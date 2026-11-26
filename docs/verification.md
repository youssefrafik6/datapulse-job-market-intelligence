# Verification record

Verified November 26, 2026 on Apple Silicon. Native Python 3.13 and a Linux ARM64 Python 3.12 image were used.

| Check | Result |
| --- | --- |
| Source files | Read the original DSC 101 PDF, script and CSV. Downloaded and inspected both proposed datasets and the Luke Barousse source. Verified pinned download hashes in the pipeline. |
| Data load | Retained 204,273 Luke and 13,371 Zalize U.S. observations. The PostgreSQL integration held both datasets. |
| Validation | Six operational assertions passed. Report totals reconcile to retained, duplicate and rejected rows. |
| SQL | All 15 analytical queries executed against PostgreSQL and the DuckDB demo. |
| dbt | 16 models built, 14 data tests passed, and dbt generated a catalog. |
| Model | Median, Ridge and random forest fit on the Zalize training group. The selected Ridge model was evaluated on 2,432 held-out postings. See `results/model_metrics.json`. |
| API | Verified live HTTP 200 responses for all eight GET endpoints, OpenAPI JSON and salary prediction. Tested 2023 trend availability and the snapshot fallback. |
| Dashboard | Loaded all 11 pages in Chrome against PostgreSQL, switched cohorts, checked historical trends and submitted a salary estimate. Screenshots are from the running application. |
| Docker Compose | ARM64 build, both pinned downloads, PostgreSQL load, dbt and training completed. FastAPI and Streamlit health endpoints responded successfully. Rounded model metrics match the native result. |
| Automation | 26 pytest checks and Ruff passed. The GitHub Actions workflow runs tests, lint and a container build. |

Limitations include the lack of full descriptions, verified company-size and individual compensation data, and uncertain correspondence between job advertisements and hires. Historical exchange-rate integration, a live Adzuna job, source-record CSV export and public hosting are outside the delivered configuration. The model interval calibrates residuals empirically, with no claim about individual compensation. The staged detect-secrets scan flagged six public dataset revision or checksum strings. The staged file audit confirmed raw datasets, processed databases, originals, local credentials and serialized models were excluded.
