"""Export aggregate-only data for the DataPulse Streamlit demo."""

import argparse
import json
from pathlib import Path

from datapulse.analytics import Analytics, Filters
from datapulse.store import query


def rows(frame):
    return json.loads(frame.to_json(orient="records", date_format="iso"))


def export(source, database):
    cohort = Analytics(Filters(source=source), database)
    provenance = query(
        "select source, revision, url, license from data_sources where source=:source",
        {"source": source},
        path=database,
    )
    totals = rows(cohort.summary())[0]
    if not totals["postings"] or provenance.empty:
        raise ValueError(f"The supplied database does not contain the {source} cohort.")
    remote = cohort.trends("remote")
    if not remote.empty:
        remote["month"] = remote["month"].dt.strftime("%Y-%m")
    return {
        "provenance": rows(provenance)[0],
        "totals": {key: totals[key] for key in ("postings", "remote_jobs", "salary_jobs")},
        "skills": rows(cohort.skills(12)),
        "states": rows(cohort.breakdown("state", 51)),
        "work_arrangement": rows(cohort.breakdown("remote")),
        "remote_months": rows(remote[["month", "segment", "postings"]]),
        "salary_by_role": rows(cohort.salary("role", 12)),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--luke", type=Path, required=True)
    parser.add_argument("--zalize", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("demo/snapshots.json"))
    args = parser.parse_args()
    snapshots = {
        source: export(source, path)
        for source, path in (("luke", args.luke), ("zalize", args.zalize))
    }
    args.output.write_text(json.dumps(snapshots, indent=2, allow_nan=False) + "\n")
