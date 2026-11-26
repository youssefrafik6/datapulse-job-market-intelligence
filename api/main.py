"""Read-only DataPulse API. Interactive specification is served at /docs."""
import json
from typing import Annotated

from duckdb import Error as DuckDBError
from fastapi import Depends, FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import OperationalError

from datapulse.analytics import Analytics, Filters
from datapulse.modeling import load, predict
from datapulse.store import query

app = FastAPI(title="DataPulse", version="1.0.0", description="Historical U.S. technology job postings.")


def json_records(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def select_filters(source: str | None = Query(None, pattern="^(luke|zalize)$"),
                   role: str | None = Query(None, max_length=100),
                   state: str | None = Query(None, pattern="^[A-Z]{2}$")):
    return Analytics(Filters(source=source, role=role, state=state))


Cohort = Annotated[Analytics, Depends(select_filters)]


@app.get("/health")
def health():
    try:
        query("select count(*) from data_sources")
    except (DuckDBError, RuntimeError, OSError, OperationalError) as error:
        raise HTTPException(503, "Datastore is unavailable") from error
    return {"status": "ok"}


@app.get("/summary")
def summary(cohort: Cohort):
    return json_records(cohort.summary())[0]


@app.get("/jobs")
def jobs(cohort: Cohort, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0, le=1_000_000),
         skill: str | None = Query(None, max_length=100), title: str | None = Query(None, max_length=100)):
    cohort.filters.skill = skill
    cohort.filters.title = title
    return {"limit": limit, "offset": offset, "records": json_records(cohort.jobs(limit, offset))}


@app.get("/skills")
def skills(cohort: Cohort):
    return json_records(cohort.skills(60))


@app.get("/salary-statistics")
def salaries(cohort: Cohort):
    return json_records(cohort.salary("role"))


@app.get("/locations")
def locations(cohort: Cohort):
    return json_records(cohort.breakdown("state", 51))


@app.get("/trends")
def trends(cohort: Cohort):
    frame = cohort.trends()
    available = frame["month"].nunique() >= 3
    return {"available": available, "scope": "Dated observations from the 2023 source",
            "reason": None if available else "Fewer than three distinct months in an eligible source",
            "records": json_records(frame) if available else []}


@app.get("/data-quality")
def data_quality():
    return json_records(query("""select source, started_at, finished_at, status, report
                                from ingestion_runs order by started_at desc limit 20"""))


class SalaryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: str = Field(min_length=1, max_length=100)
    experience: str = Field(min_length=1, max_length=30)
    state: str = Field(min_length=2, max_length=20)
    remote: str = Field(min_length=1, max_length=25)


@app.post("/salary-predict")
def salary_predict(payload: SalaryInput):
    try:
        bundle = load()
    except FileNotFoundError as error:
        raise HTTPException(503, "Train the salary model before requesting predictions") from error
    try:
        return predict(bundle, payload.model_dump())
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
