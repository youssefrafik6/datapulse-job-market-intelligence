from pathlib import Path

import pytest

from datapulse.analytics import Analytics, Filters
from datapulse.pipeline import build
from datapulse.sources import records
from datapulse.store import query

QUERIES = Path(__file__).resolve().parents[1] / "sql" / "analysis_queries.sql"


def test_ingestion_accounting_and_repeatability(snapshot):
    src, path, report = snapshot
    assert report["total_records"] == 6
    assert report["valid_records"] == 3
    assert report["duplicate_records"] == 1
    assert report["rejected_records"] == 2
    assert report["quality_flags"] == {"invalid_posting_date": 1, "invalid_salary": 1}
    previous = query("select job_id from jobs order by 1", path=path)
    assert build(src, "zalize", path) == report
    assert previous.equals(query("select job_id from jobs order by 1", path=path))
    assert len(list(Path("data/raw").rglob("fixture.parquet"))) == 1


def test_csv_schema_and_failed_run_preserve_snapshot(snapshot):
    _, path, _ = snapshot
    invalid = Path("invalid.csv")
    invalid.write_text("job_title\nExample\n")
    with pytest.raises(ValueError, match="Missing columns"):
        list(records(invalid, "luke"))
    with pytest.raises(ValueError, match="Missing columns"):
        build(invalid, "luke", path)
    assert query("select count(*) as n from jobs", path=path).n.item() == 3


def test_sql_analytics(snapshot):
    _, path, _ = snapshot
    cohort = Analytics(Filters(source="zalize", state="CT"), path)
    assert cohort.summary().postings.item() == 2
    assert cohort.salary("role")["median"].item() == 125000
    assert cohort.pairs(min_support=2).together.tolist() == [2, 2, 2]
    assert cohort.trends().empty
    assert len(cohort.jobs(limit=1)) == 1
    queries = [sql for sql in QUERIES.read_text().split(";") if sql.strip()]
    assert len(queries) >= 15
    for sql in queries:
        query(sql, path=path)


def test_filter_bindings_and_grain(snapshot):
    _, path, _ = snapshot
    assert Analytics(Filters(title="%"), path).jobs().empty
    assert Analytics(Filters(title="x' OR '1'='1"), path).jobs().empty
    assert Analytics(Filters(region="New York City"), path).jobs().title.item() == "Data Analyst"
    exact = Analytics(Filters(skill="PostgreSQL"), path)
    assert exact.summary().postings.item() == 3
    assert exact.skills().share.tolist() == [1, 1, 1]
    assert query("select count(*) n from job_skills", path=path).n.item() == 9
