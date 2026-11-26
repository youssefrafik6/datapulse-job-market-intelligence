"""DataPulse public-facing aggregate dashboard."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

LABELS = {
    "luke": "2023 · Luke Barousse Data Jobs",
    "zalize": "August 2026 · DataForge / Zalize",
}

st.set_page_config(page_title="DataPulse", layout="wide")
st.title("DataPulse")
st.write("Explore U.S. data and technology job postings from two historical sources.")

try:
    snapshots = json.loads(Path(__file__).with_name("snapshots.json").read_text())
except (OSError, ValueError):
    st.error("The aggregate snapshot is unavailable. See the repository for regeneration instructions.")
    st.stop()

source = st.radio("Dataset", list(LABELS), format_func=LABELS.get, horizontal=True)
snapshot = snapshots[source]
totals = snapshot["totals"]
count = totals["postings"]
postings, remote, pay = st.columns(3)
postings.metric("Postings analyzed", f"{count:,}")
remote.metric("Marked remote", f"{totals['remote_jobs'] / count:.1%}")
pay.metric("Comparable advertised pay", f"{totals['salary_jobs'] / count:.1%}")
st.caption("Each percentage uses all retained postings in the selected dataset.")

skills, geography = st.columns(2)
with skills:
    st.subheader("Most mentioned skills")
    st.bar_chart(pd.DataFrame(snapshot["skills"]).set_index("skill")["mentions"])
with geography:
    st.subheader("States with most postings")
    states = pd.DataFrame(snapshot["states"]).head(10)
    st.dataframe(
        states.rename(columns={"segment": "State", "postings": "Postings"}),
        hide_index=True,
    )
    st.caption("State totals include postings with a recognized state label.")

st.subheader("Work arrangement")
st.bar_chart(pd.DataFrame(snapshot["work_arrangement"]).set_index("segment")["postings"])
monthly = pd.DataFrame(snapshot["remote_months"])
if len(monthly):
    st.subheader("Monthly remote share")
    by_month = monthly.groupby("month").postings.sum()
    remote_counts = monthly[monthly.segment == "Remote"].set_index("month").postings
    st.line_chart(remote_counts.reindex(by_month.index, fill_value=0) / by_month)
    st.caption("Share marked remote among dated postings. Unspecified arrangements are included.")

st.subheader("Advertised pay")
salaries = pd.DataFrame(snapshot["salary_by_role"])
if salaries.empty:
    st.info("The 2023 source does not establish currency for its reported salaries.")
else:
    st.dataframe(
        salaries[["segment", "sample", "p10", "median", "p90"]].rename(
            columns={"segment": "Role", "sample": "Postings"}
        ),
        column_config={
            name: st.column_config.NumberColumn(label, format="dollar")
            for name, label in (("p10", "10th percentile"), ("median", "Median"),
                                ("p90", "90th percentile"))
        },
        hide_index=True,
    )
    st.caption("Annual USD midpoints among postings with comparable advertised pay.")

st.subheader("Coverage and limitations")
if source == "zalize":
    st.write("Every retained posting in this snapshot carries a Python tag. This single "
             "snapshot describes listings available at collection time.")
else:
    st.write("These observations come from search results collected in 2023. "
             "Changes in source coverage can affect monthly patterns.")
st.write("The datasets have different collection methods. Their counts describe sampled "
         "postings and should not be interpreted as hiring totals or year-over-year change.")
provenance = snapshot["provenance"]
st.caption(f"[Dataset source]({provenance['url']}) · {provenance['license']}")
