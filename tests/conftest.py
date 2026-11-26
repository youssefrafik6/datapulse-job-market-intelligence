"""Synthetic fixtures for tests only."""
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from datapulse import pipeline


@pytest.fixture
def raw_rows():
    base = {
        "title": "Senior Data Engineer", "country": "United States", "location_raw": "New Haven, CT",
        "company_name": "Synthetic employer", "job_id": "101", "is_remote": False,
        "posted_at": "2025-01-05", "scraped_at": "2025-01-06T13:12:30Z",
        "salary_min": 100_000, "salary_max": 150_000, "salary_currency": "USD", "salary_period": "year",
        "skills": ["python", "sql", "postgres"], "employment_type": "full_time",
    }
    return [
        base, base, dict(base, job_id="102", title="Data Analyst", location_raw="Brooklyn, NY", is_remote=True),
        dict(base, job_id="103", title=None), dict(base, job_id="104", country="Canada"),
        dict(base, job_id="105", salary_min=-1, salary_max=None, posted_at="today"),
    ]


@pytest.fixture
def snapshot(tmp_path, monkeypatch, raw_rows):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    output = Path("data/processed/datapulse.duckdb")
    source = Path("fixture.parquet")
    pq.write_table(pa.Table.from_pylist(raw_rows), source)
    report = pipeline.build(source, "zalize", output)
    return source, output, report
