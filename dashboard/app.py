"""Stable Streamlit entry point for DataPulse."""

from pathlib import Path
from runpy import run_path

run_path(str(Path(__file__).resolve().with_name("full.py")), run_name="__main__")
