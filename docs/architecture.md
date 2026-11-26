# Architecture and database schema

```mermaid
flowchart LR
    Sources[Pinned CSV and Parquet] --> Raw[Immutable local raw files]
    Raw --> Batch[Python batch validation and enrichment]
    Batch --> Stage[DuckDB staging and deduplication]
    Stage --> PG[PostgreSQL normalized store]
    Stage --> Demo[DuckDB demo]
    PG --> DBT[dbt staging views, facts and marts]
    PG --> SQL[Shared SQL query layer]
    Demo --> SQL
    SQL --> UI[Streamlit and Plotly]
    SQL --> API[FastAPI]
    SQL --> Model[Advertised salary training and evaluation]
    Model --> UI
    Model --> API
```

PostgreSQL is the primary deployment. DuckDB provides bounded-memory staging and a portable, single-source demo. Python reads CSV row streams or Arrow Parquet batches. SQL selects one record per source-scoped ID, preferring the latest observation and richer comparable information. Luke’s file lacks stable IDs, so its key hashes normalized title, employer, locality, posting day and schedule. This may collapse jobs with indistinguishable visible attributes. PostgreSQL COPY loads temporary tables, and the source replacement runs under a transaction-scoped advisory lock. Repeated PostgreSQL ingestion replaces the selected source while keeping the other cohort and prior successful ingestion runs. The DuckDB demo replaces its snapshot atomically and carries the latest run for that snapshot. Failed runs are logged to process output.

```mermaid
erDiagram
    DATA_SOURCES ||--o{ INGESTION_RUNS : produces
    DATA_SOURCES ||--o{ JOB_POSTINGS : supplies
    COMPANIES o|--o{ JOB_POSTINGS : employs
    LOCATIONS o|--o{ JOB_POSTINGS : locates
    JOB_TITLES ||--o{ JOB_POSTINGS : describes
    JOB_POSTINGS ||--o| SALARY_RECORDS : discloses
    JOB_POSTINGS ||--o{ JOB_SKILLS : mentions
    SKILLS ||--o{ JOB_SKILLS : identifies
    JOB_POSTINGS {
      varchar job_id PK
      varchar source FK
      varchar title_id FK
      date posted_date
      timestamptz last_observed_at
      timestamptz ingested_at
      varchar processing_version
      varchar quality_status
    }
    SALARY_RECORDS {
      varchar job_id PK,FK
      float original_low
      float original_high
      varchar currency
      varchar period
      varchar salary_origin
      float annual_usd
    }
    JOB_SKILLS {
      varchar job_id PK,FK
      varchar skill PK,FK
    }
```

The dashboard and API use parameterized SQL over a one-row-per-posting view and the skill bridge, enabling identical interactive filters on either backend. dbt provides shared PostgreSQL marts for analysts and external BI consumers. A full rebuild is appropriate because each load replaces a pinned snapshot and the dataset fits on a local workstation. `make docs` generates a lineage catalog from PostgreSQL and `dbt docs serve --project-dir dbt --profiles-dir dbt` opens it locally.

The salary fact keeps original values, normalized bounds and the range midpoint separately. The pipeline annualizes monthly wages by 12 and full-time hourly wages by 2,080. Unsupported units, currencies and missing endpoints are visible in the quality rules. Historical FX conversion requires a verified dated table supplied by an operator. No FX table is bundled, so non-USD compensation remains in its original units. Prediction outputs are separate from salary facts.
