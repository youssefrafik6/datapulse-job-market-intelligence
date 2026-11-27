"""Serve the full dashboard when a datastore is configured, otherwise use aggregates."""

from pathlib import Path
from runpy import run_path

from datapulse.store import DB_FILE, database_url

dashboard = Path(__file__).resolve().parent
entrypoint = (
    dashboard / "full.py"
    if database_url() or DB_FILE.is_file()
    else dashboard.parent / "demo" / "app.py"
)
run_path(str(entrypoint), run_name="__main__")
