"""Stable Streamlit entry point for DataPulse."""

from pathlib import Path
from runpy import run_path

from datapulse.store import DB_FILE, database_url

root = Path(__file__).resolve().parents[1]
entrypoint = "dashboard/full.py" if database_url() or DB_FILE.is_file() else "demo/app.py"
run_path(str(root / entrypoint), run_name="__main__")
