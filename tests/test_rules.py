import pytest

from datapulse.rules import (
    classify_title,
    experience,
    location_parts,
    normalize_salary,
    remote_status,
    skills_from_text,
    supplied_skills,
)


def test_ambiguous_titles_are_retained_for_review():
    assert classify_title("Data Analyst / Data Engineer") == ("Ambiguous", ("Data Analyst", "Data Engineer"))
    assert classify_title("Senior BI Developer")[0] == "Business Intelligence Analyst"
    assert classify_title("Data Engineering Manager")[0] == "Data Engineer"


def test_early_career_requires_description_evidence():
    assert experience("Junior Data Analyst") == ("Unknown", None, "early-career title signal")
    assert experience("Analyst", "Requires 2 years of professional experience.")[:2] == ("Entry", 2)
    assert experience("Senior Data Analyst", "Requires 2 years of experience.")[:2] == ("Senior", 2)


def test_text_aliases_and_significant_boundaries():
    assert skills_from_text("We go to work and excel; R and D teams spark change.") == set()
    assert skills_from_text("Go programming, R language, GCP, Postgres, MS SQL Server, C++ and PySpark.") == {
        "Go", "R", "Google Cloud", "PostgreSQL", "SQL Server", "C++", "PySpark",
    }
    assert skills_from_text("JavaScript with Spark SQL and Git.") == {"JavaScript", "Spark", "SQL", "Git"}


def test_supplier_tags_are_exact_and_deduplicated():
    assert supplied_skills("['aws','aws','r','golang','unknown']") == ({"AWS", "R", "Go"}, 1, False)
    assert supplied_skills("not a list") == (set(), 0, True)


def test_geography_and_conflicting_work_arrangements():
    assert location_parts("Brooklyn, NY, United States") == ("Brooklyn", "NY", True)
    assert location_parts("Connecticut") == (None, "CT", False)
    assert location_parts("Springfield") == (None, None, False)
    assert remote_status("On-site or remote", True) == ("Unspecified", True)
    assert remote_status("Hybrid, Boston", True) == ("Hybrid", False)


@pytest.mark.parametrize(("low", "high"), [(-1, 100), (100, 50), (float("nan"), 15)])
def test_invalid_salary(low, high):
    assert normalize_salary(low, high, None, "year", "USD", "advertised") == (None, "invalid_salary")


def test_salary_origin_and_units():
    args = (40, 60, None, "hour", "USD", "advertised")
    assert normalize_salary(*args, full_time=True)[0]["annual_usd"] == 104_000
    assert normalize_salary(*args)[0]["annual_usd"] is None
    monthly = normalize_salary(3000, 5000, None, "month", "EUR", "advertised", fx=1.1)[0]
    assert monthly["annual_usd"] == pytest.approx(52800)
    assert normalize_salary(5000, None, None, "month", "USD", "advertised")[0]["annual_usd"] is None
    assert normalize_salary(50, 100, None, "year", "USD", "estimated")[0]["annual_usd"] is None
    assert normalize_salary(None, None, None, "year", "USD", "advertised") == (None, None)
