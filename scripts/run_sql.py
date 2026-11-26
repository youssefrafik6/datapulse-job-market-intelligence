from pathlib import Path

from datapulse.store import query

if __name__ == "__main__":
    scripts = Path("sql/analysis_queries.sql").read_text().split(";")
    for i, sql in enumerate((statement for statement in scripts if statement.strip()), 1):
        result = query(sql)
        print(f"Query {i:02d} · {len(result):,} result rows")
