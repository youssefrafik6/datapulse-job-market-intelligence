"""Prepare public Streamlit data on demand using the pinned source files."""

from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from datapulse.modeling import load, train
from datapulse.pipeline import build
from datapulse.sources import download


@st.cache_resource(show_spinner=False)
def snapshot(source):
    """Keep one completed snapshot per source for the life of the app process."""
    with TemporaryDirectory(prefix=f"datapulse-{source}-") as staging:
        # Retain the temporary directory alongside the database in the resource cache.
        storage = TemporaryDirectory(prefix=f"datapulse-{source}-")
        try:
            root = Path(storage.name)
            raw = Path(staging)
            database = root / "jobs.duckdb"
            build(download(source, raw=raw), source, database, root / "quality.json",
                  raw=raw, memory_limit="384MB", threads=2)
        except BaseException:
            storage.cleanup()
            raise
    return database, storage


@st.cache_resource(show_spinner=False)
def salary_model():
    database, _ = snapshot("zalize")
    artifact = database.with_name("salary.joblib")
    train(database, artifact=artifact, results=database.with_name("salary-metrics.json"))
    return load(artifact)
