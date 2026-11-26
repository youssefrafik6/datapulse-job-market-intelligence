# Resume material for Youssef Rafik

DataPulse is a local-first U.S. tech and data job market intelligence platform built on historical posting datasets.

It combines reproducible Python ingestion, PostgreSQL and dbt analytics, a Streamlit dashboard, and an evaluated salary baseline.

## Three resume bullets

- Built a batch CSV/Parquet pipeline that retained 217,644 validated U.S. postings across two independently analyzed cohorts, using deterministic deduplication, data-quality reports and transaction-scoped PostgreSQL loads.
- Authored 16 dbt models, 14 dbt data tests and 15 analytical SQL queries for skill demand, geographic coverage, remote work, and advertised pay, and exposed cohort analytics in an 11-page Streamlit dashboard and a FastAPI service.
- Benchmarked median, Ridge and random forest regression on employer-disjoint splits. Selected Ridge by validation MAE and measured $44,738 test MAE on 2,432 held-out postings versus $48,723 for the median baseline.

## Tailor by role

| Role | Emphasis |
| --- | --- |
| Data Analyst | Analyzed 204,273 U.S. 2023 observations by geography, posting month and skill. Used coverage-aware filters to compare Connecticut and NYC with the nationwide cohort. |
| Business Intelligence Analyst | Designed an 11-page interactive dashboard with sample sizes, work-arrangement coverage, geographic views and analyst-facing limitations. |
| Analytics Engineer | Modeled fact and bridge grains with 16 dbt models and 14 data tests. Used window functions, filtered aggregates, percentile statistics and Jaccard overlap. |
| Data Engineer | Streamed CSV/Parquet, applied immutable source handling and deterministic identity rules, then loaded PostgreSQL transactionally via COPY. |
| Data Scientist | Compared three model families using independent employer groups, evaluated subgroup errors, and measured empirical interval coverage at 86.3% on held-out salaries. |

**Stack** · Python, SQL, PostgreSQL, DuckDB, PyArrow, dbt, pandas, scikit-learn, NetworkX, Streamlit, Plotly, FastAPI, pytest, Ruff and Docker Compose.

Interview topics include a source selection decision based on provenance, the limits of a posting fingerprint without a job ID, why a surviving snapshot cannot establish hiring growth, and how salary disclosure bias, broad title buckets and employer shift affect model performance.
