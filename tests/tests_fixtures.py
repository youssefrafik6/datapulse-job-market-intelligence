"""Build a seeded synthetic training corpus for pytest only."""
import pyarrow as pa
import pyarrow.parquet as pq


def make_salary_file(root, seed_row):
    rows = [dict(seed_row, job_id=str(i), company_name=f"Fixture employer {i % 40}",
                 title="Data Analyst" if i % 2 else "Data Scientist",
                 salary_min=100_000 + (i % 13) * 2000, salary_max=175_000 + (i % 11) * 1000)
            for i in range(500)]
    file = root / "synthetic.parquet"
    pq.write_table(pa.Table.from_pylist(rows), file)
    return file
