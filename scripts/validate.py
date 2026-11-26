from datapulse.store import query

CHECKS = {
    "no_duplicate_jobs": "select job_id from job_postings group by 1 having count(*) > 1",
    "no_missing_titles": "select job_id from jobs where title is null or trim(title) = ''",
    "salary_positive": "select job_id from jobs where annual_usd <= 0",
    "salary_origin_separated": "select job_id from jobs where annual_usd is not null and salary_origin <> 'advertised'",
    "no_future_dates": "select job_id from jobs where posted_date > current_date",
    "no_orphaned_skills": """select k.job_id from job_skills k left join job_postings j on j.job_id=k.job_id
                            left join skills s on s.skill=k.skill where j.job_id is null or s.skill is null""",
}

if __name__ == "__main__":
    failures = [name for name, sql in CHECKS.items() if not query(sql).empty]
    if failures:
        raise SystemExit("Failed checks: " + ", ".join(failures))
    print(f"{len(CHECKS)} data quality checks passed")
