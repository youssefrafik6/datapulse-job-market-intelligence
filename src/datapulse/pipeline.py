"""Load a reproducible, transactional snapshot, with row-level audit counts."""
import hashlib
import json
import logging
import os
import re
import shutil
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

import duckdb
import pyarrow as pa

from datapulse.rules import (
    classify_title,
    experience,
    location_parts,
    normalize_salary,
    remote_status,
    skills_from_text,
    supplied_skills,
)
from datapulse.sources import RAW, SOURCES, records
from datapulse.store import DB_FILE, JOB_VIEW, SCHEMA

LOG = logging.getLogger(__name__)
VERSION = "1.0"
CONTACT = re.compile(r"[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|(?<!\w)(?:\+1[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\w)")
TABLES = ("companies", "locations", "job_titles", "skills", "job_postings", "salary_records", "job_skills")
REPORT = Path("results/data_quality_report.json")


def clean(value):
    return " ".join(value.split()) if isinstance(value, str) and value.strip() else None


def sanitized(value):
    return CONTACT.sub("[redacted]", value) if value else None


def parse_date(value, now):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        utc = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return utc if 1990 <= utc.year and utc <= now else None
    except (ValueError, TypeError):
        return None


def identity(*parts):
    return hashlib.sha256(json.dumps(parts, ensure_ascii=False).encode()).hexdigest()


def archive_input(path, key, raw=RAW):
    """Keep an immutable local copy of an externally supplied input."""
    if path.resolve().is_relative_to(raw.resolve()):
        return path
    from datapulse.sources import checksum

    dest = raw / key / checksum(path) / path.name
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        with TemporaryDirectory(dir=dest.parent) as directory:
            staged = Path(directory) / dest.name
            shutil.copyfile(path, staged)
            staged.replace(dest)
    return dest


def interpret(row, key, now):
    luke = key == "luke"
    country = clean(row.get("job_country" if luke else "country"))
    raw_location = clean(row.get("job_location" if luke else "location_raw"))
    if (country or "").casefold() not in {"united states", "us", "usa"}:
        return None, "outside_us_or_unknown"
    raw_title = clean(row.get("job_title" if luke else "title"))
    if not raw_title:
        return None, "missing_title"
    company = sanitized(clean(row.get("company_name")))
    title = sanitized(raw_title)
    location = sanitized(raw_location)
    city, state, nyc = location_parts(location or "")
    role, candidates = classify_title(title)
    date_value = row.get("job_posted_date" if luke else "posted_at")
    posted = parse_date(date_value, now)
    observed = parse_date(row.get("scraped_at"), now)
    remote_value = row.get("job_work_from_home" if luke else "is_remote")
    remote, conflict = remote_status(raw_location or "", str(remote_value).lower() == "true")
    description = row.get("description") or ""
    level, years, evidence = experience(title, description)
    skill_value = row.get("job_skills" if luke else "skills")
    skills, unknown_skills, malformed = supplied_skills(skill_value or None)
    extracted = skills_from_text(description) if description else set()
    if luke:
        period = {"year": "year", "hour": "hour"}.get(row.get("salary_rate"), row.get("salary_rate"))
        point = clean(row.get("salary_year_avg") if period == "year" else row.get("salary_hour_avg"))
        salary, salary_flag = normalize_salary(None, None, point, period, None, "source_reported")
    else:
        period = row.get("salary_period")
        salary, salary_flag = normalize_salary(
            row.get("salary_min"), row.get("salary_max"), None, period, row.get("salary_currency"),
            "advertised", full_time=row.get("employment_type") == "full_time",
        )
    source_key = (clean(row.get("url")) or
                  (":".join(str(row.get(field) or "") for field in ("ats", "ats_token", "job_id"))
                   if row.get("job_id") else None))
    job_id = identity(key, source_key) if source_key else identity(
        key, title.casefold(), (company or "").casefold(), (location or "").casefold(),
        posted.date().isoformat() if posted else date_value, row.get("job_schedule_type"),
    )
    platform = sanitized(clean(row.get("job_via" if luke else "ats")))
    flags = [flag for flag, condition in {
        "missing_company": not company, "missing_location": not location, "unknown_state": not state,
        "invalid_posting_date": bool(date_value and not posted), "missing_posting_date": not date_value,
        "invalid_observation_date": bool(row.get("scraped_at") and not observed),
        "remote_conflict": conflict, "invalid_remote_flag": str(remote_value).lower() not in {"true","false","none",""},
        "unrecognized_skills": unknown_skills, "malformed_skill_list": malformed,
        "ambiguous_role": role == "Ambiguous", salary_flag: salary_flag is not None,
    }.items() if condition]
    return {
        "job_id": job_id, "title_id": identity(title), "title": title, "role": role,
        "candidates": " | ".join(candidates), "company_id": identity(company.casefold()) if company else None,
        "company": company, "location_id": identity(location.casefold()) if location else None,
        "location": location, "city": city, "state": state, "nyc": nyc, "source": key,
        "source_key": identity(source_key) if source_key else None,
        "posted_date": posted.date() if posted else None, "last_observed_at": observed,
        "ingested_at": now, "processing_version": VERSION, "quality_status": "flagged" if flags else "valid",
        "remote": remote, "experience": level, "experience_years": years, "experience_evidence": evidence,
        "skill_evidence": ("supplied + text" if skills and extracted else "supplied" if skills else
                           "text" if extracted else "none"), "platform": platform,
        "skills_list": sorted(skills | extracted), "flags": flags, **(salary or {}),
    }, None


# Explicit Arrow types keep all-null batches compatible with later batches.
FIELDS = {
    "job_id": pa.string(), "source": pa.string(), "source_key": pa.string(), "company_id": pa.string(),
    "location_id": pa.string(), "title_id": pa.string(), "title": pa.string(), "role": pa.string(),
    "candidates": pa.string(), "company": pa.string(), "location": pa.string(), "city": pa.string(),
    "state": pa.string(), "nyc": pa.bool_(), "posted_date": pa.date32(),
    "last_observed_at": pa.timestamp("us", tz="UTC"), "ingested_at": pa.timestamp("us", tz="UTC"),
    "processing_version": pa.string(), "quality_status": pa.string(), "remote": pa.string(),
    "experience": pa.string(), "experience_years": pa.int32(), "experience_evidence": pa.string(),
    "skill_evidence": pa.string(), "platform": pa.string(), "skills_list": pa.list_(pa.string()),
    "flags": pa.list_(pa.string()), "original_low": pa.float64(), "original_high": pa.float64(),
    "original_point": pa.float64(), "period": pa.string(), "currency": pa.string(), "salary_origin": pa.string(),
    "annual_low": pa.float64(), "annual_high": pa.float64(), "annual_usd": pa.float64(),
}
ARROW_SCHEMA = pa.schema(FIELDS)
SELECTS = {
    "companies": "select company_id, min(company), cast(null as varchar) from unique_rows where company_id is not null group by company_id",
    "locations": """select distinct on(location_id) location_id, location, city, state, nyc
        from unique_rows where location_id is not null order by location_id, state nulls last, location""",
    "job_titles": "select distinct title_id, title, role, candidates from unique_rows",
    "skills": "select distinct unnest(skills_list) from unique_rows",
    "job_postings": """select job_id, source, source_key, company_id, location_id, title_id, posted_date,
        last_observed_at, ingested_at, processing_version, quality_status, remote, experience,
        experience_years, experience_evidence, skill_evidence, platform from unique_rows""",
    "salary_records": """select job_id, original_low, original_high, original_point, period, currency,
        salary_origin, annual_low, annual_high, annual_usd from unique_rows where salary_origin is not null""",
    "job_skills": "select job_id, unnest(skills_list) from unique_rows",
}


def batches(path, key, now, counts):
    batch = []
    for raw in records(path, key):
        counts["total_records"] += 1
        record, rejection = interpret(raw, key, now)
        if rejection:
            counts[rejection] += 1
        else:
            batch.append(record)
        if len(batch) == 8192:
            yield pa.Table.from_pylist(batch, schema=ARROW_SCHEMA)
            batch.clear()
    if batch:
        yield pa.Table.from_pylist(batch, schema=ARROW_SCHEMA)


def transfer_postgres(connection, url, metadata, run):
    """Atomically replace only the selected source snapshot using PostgreSQL COPY."""
    from sqlalchemy import create_engine

    engine = create_engine(url)
    raw = engine.raw_connection()
    try:
        with raw.cursor() as cursor:
            cursor.execute("select pg_advisory_xact_lock(421028101)")
            for ddl in SCHEMA:
                cursor.execute(ddl)
            cursor.execute("insert into data_sources values (%s,%s,%s,%s,%s) on conflict(source) do update "
                           "set revision=excluded.revision,url=excluded.url,license=excluded.license,"
                           "trend_eligible=excluded.trend_eligible", metadata)
            for table in ("job_skills", "salary_records"):
                cursor.execute(f"delete from {table} where job_id in (select job_id from job_postings where source=%s)",
                               (metadata[0],))
            cursor.execute("delete from job_postings where source=%s", (metadata[0],))
            for table in TABLES:
                cursor.execute(f"create temporary table load_{table} (like {table}) on commit drop")
                result = connection.execute(f"select * from {table}")
                with cursor.copy(f"copy load_{table} from stdin") as stream:
                    while rows := result.fetchmany(8192):
                        for row in rows:
                            stream.write_row(row)
                cursor.execute(f"insert into {table} select * from load_{table} on conflict do nothing")
            cursor.execute(f"create or replace view jobs as {JOB_VIEW}")
            cursor.execute("insert into ingestion_runs values (%s,%s,%s,%s,%s,%s)", run)
        raw.commit()
    finally:
        raw.close()
        engine.dispose()


def build(path, key, output=DB_FILE, report_path=REPORT, postgres=None, *,
          raw=RAW, memory_limit="768MB", threads=4):
    """Rebuild the demo atomically. A failed run leaves the prior snapshot available."""
    source = SOURCES[key]
    path = archive_input(path, key, raw)
    now = datetime.now(timezone.utc)
    counts = Counter()
    metadata = (key, source.revision, source.url, source.license, source.trend_eligible)
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=output.parent) as directory:
        pending = Path(directory) / "snapshot.duckdb"
        with duckdb.connect(str(pending), config={"memory_limit": memory_limit, "threads": threads}) as cx:
            for ddl in SCHEMA:
                cx.execute(ddl)
            empty = pa.Table.from_pylist([], schema=ARROW_SCHEMA)
            cx.register("input_batch", empty)
            cx.execute("create temp table staged as select * from input_batch")
            for batch in batches(path, key, now, counts):
                cx.register("input_batch", batch)
                cx.execute("insert into staged select * from input_batch")
                cx.unregister("input_batch")
            cx.execute("""create temp table unique_rows as
                select * from staged qualify row_number() over (
                  partition by job_id order by last_observed_at desc nulls last, annual_usd desc nulls last,
                  salary_origin desc nulls last, len(skills_list) desc, title, company, location,
                  skills_list, original_low, original_high, original_point, currency, period, remote, platform,
                  posted_date, experience, experience_years, experience_evidence, flags
                ) = 1""")
            valid, locations, skills, salaries, observed_salary, flagged = cx.execute("""
                select count(*), count(state), count(*) filter(where len(skills_list)>0),
                       count(annual_usd), count(salary_origin), count(*) filter(where quality_status='flagged')
                from unique_rows
            """).fetchone()
            flags = dict(cx.execute("""select flag, count(*) from (select unnest(flags) as flag from unique_rows)
                                      group by flag order by flag""").fetchall())
            rejected = counts["missing_title"] + counts["outside_us_or_unknown"]
            report = {
                "source": key, "revision": source.revision, "processing_version": VERSION,
                "total_records": counts["total_records"], "valid_records": valid, "flagged_records": flagged,
                "rejected_records": rejected, "duplicate_records": counts["total_records"] - valid - rejected,
                "rejection_reasons": {reason: counts[reason] for reason in ("missing_title", "outside_us_or_unknown")},
                "quality_flags": flags, "state_coverage": locations / max(valid, 1),
                "skill_coverage": skills / max(valid, 1), "normalized_salary_coverage": salaries / max(valid, 1),
                "salary_source_coverage": observed_salary / max(valid, 1),
            }
            if not valid:
                raise ValueError("No valid U.S. postings. Check input schema and coverage.")
            cx.execute("insert into data_sources values (?, ?, ?, ?, ?)", metadata)
            for table, select in SELECTS.items():
                cx.execute(f"insert into {table} {select}")
            cx.execute(f"create view jobs as {JOB_VIEW}")
            run = (str(uuid.uuid4()), key, now, datetime.now(timezone.utc), "succeeded", json.dumps(report))
            cx.execute("insert into ingestion_runs values (?, ?, ?, ?, ?, ?)", run)
            if postgres:
                transfer_postgres(cx, postgres, metadata, run)
        os.replace(pending, output)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=report_path.parent) as directory:
        pending_report = Path(directory) / report_path.name
        pending_report.write_text(json.dumps(report, indent=2) + "\n")
        pending_report.replace(report_path)
    LOG.info("Loaded %d U.S. records from %s", valid, key)
    return report
