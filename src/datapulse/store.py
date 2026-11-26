"""Shared database contract for PostgreSQL and the local DuckDB demo."""
import os
from pathlib import Path

import duckdb
from sqlalchemy import create_engine, text

DB_FILE = Path(os.environ.get("DATAPULSE_DB_FILE", "data/processed/datapulse.duckdb"))

SCHEMA = (
    """create table if not exists data_sources (
        source varchar primary key, revision varchar not null, url varchar not null,
        license varchar not null, trend_eligible boolean not null)""",
    """create table if not exists ingestion_runs (
        run_id varchar primary key, source varchar not null references data_sources(source),
        started_at timestamptz not null, finished_at timestamptz, status varchar not null
        check (status in ('running','succeeded','failed')), report json)""",
    """create table if not exists companies (company_id varchar primary key, company varchar not null,
        company_size varchar)""",
    """create table if not exists locations (location_id varchar primary key, location varchar not null,
        city varchar, state varchar, nyc boolean not null)""",
    """create table if not exists job_titles (title_id varchar primary key, title varchar not null,
        role varchar not null, candidates varchar not null)""",
    """create table if not exists skills (skill varchar primary key)""",
    """create table if not exists job_postings (
        job_id varchar primary key, source varchar not null references data_sources(source),
        source_key varchar, company_id varchar references companies(company_id),
        location_id varchar references locations(location_id), title_id varchar not null references job_titles(title_id),
        posted_date date, last_observed_at timestamptz, ingested_at timestamptz not null,
        processing_version varchar not null, quality_status varchar not null
        check (quality_status in ('valid','flagged')),
        remote varchar not null check (remote in ('Remote','Hybrid','On-site','Unspecified')),
        experience varchar not null check (experience in ('Entry','Mid','Senior','Executive','Unknown')),
        experience_years integer check (experience_years >= 0), experience_evidence varchar not null,
        skill_evidence varchar not null, platform varchar)""",
    """create table if not exists salary_records (
        job_id varchar primary key references job_postings(job_id), original_low double precision,
        original_high double precision, original_point double precision, period varchar, currency varchar,
        salary_origin varchar not null check (salary_origin in ('advertised','source_reported','estimated')),
        annual_low double precision, annual_high double precision, annual_usd double precision,
        check (original_low is null or original_low > 0), check (original_high is null or original_high > 0),
        check (original_point is null or original_point > 0), check (annual_usd is null or annual_usd > 0),
        check (annual_low is null or annual_high is null or annual_low <= annual_high))""",
    """create table if not exists job_skills (job_id varchar references job_postings(job_id),
        skill varchar references skills(skill), primary key(job_id, skill))""",
    "create index if not exists jobs_date_idx on job_postings(posted_date)",
    "create index if not exists jobs_location_idx on job_postings(location_id)",
    "create index if not exists skills_name_idx on job_skills(skill)",
)

JOB_VIEW = """select j.*, t.title, t.role, t.candidates, c.company, c.company_size,
    l.location, l.city, l.state, coalesce(l.nyc, false) as nyc, s.annual_low, s.annual_high,
    s.annual_usd, s.salary_origin, d.trend_eligible, d.url as source_url
from job_postings j
join job_titles t on j.title_id = t.title_id
join data_sources d on j.source = d.source
left join companies c on j.company_id = c.company_id
left join locations l on j.location_id = l.location_id
left join salary_records s on j.job_id = s.job_id"""


def database_url():
    return os.environ.get("DATABASE_URL")


def query(sql, params=None, path=None):
    """Return a DataFrame using named bindings on either backend."""
    if database_url() and path is None:
        from pandas import read_sql

        engine = create_engine(database_url())
        try:
            with engine.connect() as connection:
                return read_sql(text(sql), connection, params=params)
        finally:
            engine.dispose()
    with duckdb.connect(str(path or DB_FILE), read_only=True) as connection:
        import re

        sql = re.sub(r"(?<!:):([a-z_]+)", r"$\1", sql)
        return connection.execute(sql, params or {}).fetchdf()
