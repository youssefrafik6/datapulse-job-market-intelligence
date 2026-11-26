"""Acquire a pinned data file and load a local or PostgreSQL snapshot."""
import argparse
import logging
from pathlib import Path

from datapulse.pipeline import build
from datapulse.sources import SOURCES, download
from datapulse.store import DB_FILE, database_url


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=SOURCES, default="zalize")
    parser.add_argument("--input", type=Path, help="A local CSV or Parquet file in the selected source format")
    parser.add_argument("--output", type=Path, default=DB_FILE)
    parser.add_argument("--report", type=Path, default=Path("results/data_quality_report.json"))
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    try:
        build(args.input or download(args.source), args.source, args.output, args.report, database_url())
    except Exception:
        logging.exception("Ingestion failed")
        raise


if __name__ == "__main__":
    main()
