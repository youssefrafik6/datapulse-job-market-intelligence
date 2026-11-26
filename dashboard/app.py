"""Interactive DataPulse dashboard backed by parameterized analytics queries."""
from dataclasses import replace

import networkx as nx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from datapulse.analytics import Analytics, Filters
from datapulse.modeling import ARTIFACT, load, predict
from datapulse.rules import EXPERIENCES, REMOTE, ROLES, SKILL_ALIASES, STATES
from datapulse.store import DB_FILE, database_url, query

st.set_page_config(page_title="DataPulse | U.S. Job Market Intelligence", page_icon="📊", layout="wide")
st.markdown("""<style>
[data-testid="stSidebar"] {border-right:1px solid #dbe4ef;}
[data-testid="stMetric"] {padding: .85rem 1rem; background:white; border:1px solid #dbe4ef; border-radius: 12px;}
.block-container {padding-top:2.1rem; max-width:1440px;}
[data-testid="stCaptionContainer"] {color:#465a72;}
</style>""", unsafe_allow_html=True)

PAGES = [
    "Executive Overview", "Salary Intelligence", "Skills Demand", "Geographic Job Market",
    "Entry-Level Career Intelligence", "Hiring Trends", "Salary Prediction", "Skill Network",
    "Data Explorer", "Data Engineering", "Methodology",
]
PALETTE = ["#007c78", "#355c9d", "#cc7041", "#8461a4", "#47804c", "#a04d6c", "#447b9e"]


def choice(container, label, options):
    return container.selectbox(label, [None, *options], format_func=lambda value: value or "All")


def chart(figure):
    figure.update_layout(
        colorway=PALETTE, paper_bgcolor="#ffffff", plot_bgcolor="#ffffff",
        font={"color": "#223a56", "size": 13}, margin={"t": 32, "b": 28, "l": 25, "r": 25},
    )
    figure.update_xaxes(gridcolor="#e5edf5", zerolinecolor="#e5edf5")
    figure.update_yaxes(gridcolor="#e5edf5", zerolinecolor="#e5edf5")
    st.plotly_chart(figure, use_container_width=True)


def table(frame):
    st.dataframe(frame, use_container_width=True, hide_index=True)


def bars(frame, x, y, labels=None):
    if frame.empty:
        st.info("No matching observations in this selection.")
    else:
        chart(px.bar(frame.iloc[::-1], x=x, y=y, orientation="h", labels=labels,
                     color_discrete_sequence=PALETTE, hover_data=[c for c in frame if c not in {x, y}]))


def show_skill_bars(cohort):
    bars(cohort.skills(12), "mentions", "skill", {"mentions": "Postings mentioning skill", "skill": "Skill"})


def show_roles(cohort):
    bars(cohort.breakdown("role"), "postings", "segment", {"postings": "Postings", "segment": "Role"})


def map_states(cohort):
    states = cohort.breakdown("state", 51)
    if states.empty:
        st.info("No state-level records in this selection.")
        return
    figure = px.choropleth(states, locations="segment", locationmode="USA-states", scope="usa",
                           color="postings", color_continuous_scale=["#e6f3f2", "#006a68"],
                           labels={"postings": "Postings", "segment": "State"})
    chart(figure)


def salary_detail(cohort, dimension):
    frame = cohort.salary(dimension)
    if frame.empty:
        st.info("No comparable advertised USD salaries for this selection.")
        return
    bars(frame, "median", "segment", {"median": "Median annual USD", "segment": dimension.replace("_", " ").title()})
    table(frame.round(0))


def date_label(value):
    return value.date().isoformat() if pd.notna(value) and hasattr(value, "date") else str(value) if pd.notna(value) else "Unavailable"


st.sidebar.title("DataPulse")
st.sidebar.caption("U.S. JOB MARKET INTELLIGENCE")
page = st.sidebar.radio("Pages", PAGES, label_visibility="collapsed")
st.title("DataPulse" if page == PAGES[0] else page)
if not database_url() and not DB_FILE.exists():
    st.info("Build a local snapshot with `make demo`, or configure the PostgreSQL connection.")
    st.stop()

sources = query("select source, revision, url, license from data_sources order by source")
if sources.empty:
    st.info("Ingest a source to start exploring.")
    st.stop()
source_names = {"luke": "Luke Barousse · 2023", "zalize": "Zalize · Aug 2026 sample"}
ordered_sources = sorted(sources.source.tolist(), reverse=True)
source = st.sidebar.selectbox("Dataset", ordered_sources, format_func=source_names.get)
with st.sidebar.expander("Cohort filters", expanded=False):
    role = choice(st, "Role", [*ROLES, "Ambiguous", "Other Technology"])
    experience = choice(st, "Experience", EXPERIENCES)
    state = choice(st, "State", STATES)
    remote = choice(st, "Remote status", REMOTE)
    use_dates = st.checkbox("Filter by posting date")
    dates = st.date_input("Posting date range", (pd.Timestamp("2023-01-01").date(),
                                                 pd.Timestamp("2026-08-31").date())) if use_dates else ()
    if len(dates) == 2 and dates[0] > dates[1]:
        st.error("The end date must follow the start date.")
        st.stop()
filters = Filters(source=source, role=role, experience=experience, state=state, remote=remote,
                  start=dates[0] if dates else None, end=dates[1] if len(dates) == 2 else None)
cohort = Analytics(filters)
st.caption(f"{source_names[source]}  ·  Historical observations  ·  U.S. subset")
if source == "zalize":
    st.caption("Source: DataForge (data.zalize.com) · [Zalize dataset and attribution](https://data.zalize.com/datasets/tech-job-postings-salary-dataset) · CC BY-NC 4.0")
else:
    st.caption("Source: [Luke Barousse’s Data Jobs dataset](https://huggingface.co/datasets/lukebarousse/data_jobs) · Apache-2.0")

if page == PAGES[0]:
    st.subheader("Explore the U.S. Tech & Data Job Market.")
    if source == "zalize":
        st.caption("Every retained posting in this snapshot carries a Python tag. Use Luke Barousse’s cohort for broader skill comparisons.")
    totals = cohort.summary().iloc[0]
    count = int(totals.postings)
    denominator = max(count, 1)
    columns = st.columns(5)
    for column, label, number in zip(columns, ["Job postings", "Companies", "Location labels", "Remote", "Advertised USD salary"], [
        f"{count:,}", f"{int(totals.companies):,}", f"{int(totals.locations):,}",
        f"{totals.remote_jobs / denominator:.1%}", f"{totals.salary_jobs / denominator:.1%}",
    ], strict=True):
        column.metric(label, number if count else "—")
    st.caption(f"Posting dates {date_label(totals.first_posted)} to {date_label(totals.last_posted)}  ·  "
               f"Latest source observation {date_label(totals.last_observed)}  ·  "
               f"Loaded {date_label(totals.last_ingested)}")
    left, right = st.columns(2)
    with left:
        st.subheader("Posting mix by role")
        show_roles(cohort)
    with right:
        st.subheader("Top technical mentions")
        show_skill_bars(cohort)
    left, right = st.columns(2)
    with left:
        st.subheader("Coverage by state")
        map_states(cohort)
    with right:
        st.subheader("Work arrangement")
        bars(cohort.breakdown("remote"), "postings", "segment")
    sample = cohort.salary_sample()
    if not sample.empty:
        st.subheader("Advertised salary distribution")
        chart(px.histogram(sample, x="annual_usd", nbins=38, labels={"annual_usd": "Annual USD"},
                           color_discrete_sequence=PALETTE))
elif page == PAGES[1]:
    st.write("Advertised USD figures describe postings with comparable disclosed pay. This salary-rich source and "
             "selective employer disclosure limit comparisons to the observed sample.")
    dimension = st.selectbox("Compare by", ["role", "title", "experience", "state", "company_size", "remote"],
                             format_func=lambda item: item.replace("_", " ").title())
    if dimension == "company_size":
        st.info("Neither posting source includes a verified employer size field.")
    else:
        salary_detail(cohort, dimension)
    sample = cohort.salary_sample()
    if not sample.empty:
        left, right = st.columns(2)
        with left:
            chart(px.box(sample, x="annual_usd", y="experience", color_discrete_sequence=PALETTE,
                         labels={"annual_usd": "Annual USD", "experience": "Experience signal"}))
        with right:
            chart(px.histogram(sample, x="annual_usd", nbins=35, color_discrete_sequence=PALETTE,
                               labels={"annual_usd": "Annual USD"}))
        st.caption(f"Distribution charts show {len(sample):,} observations, with a reproducible sample capped at 10,000.")
elif page == PAGES[2]:
    st.write("Skill mentions come from source-provided tags and supported text matching. The denominator includes all "
             "postings in each displayed group.")
    if source == "zalize":
        st.caption("Python appears on every retained posting from this source.")
    left, right = st.columns(2)
    with left:
        show_skill_bars(cohort)
    with right:
        dimension = st.selectbox("Segment", ["role", "experience", "state", "salary_band"])
        chosen = choice(st, "Compare a skill", sorted(SKILL_ALIASES))
        frame = cohort.skill_demand(dimension, 180, chosen)
        if frame.empty:
            st.info("No recorded mentions in this selection.")
        elif chosen:
            chart(px.bar(frame, x="share", y="segment", orientation="h", hover_data=["mentions", "sample"],
                         labels={"share": "Share of postings", "segment": "Segment"},
                         color_discrete_sequence=PALETTE).update_xaxes(tickformat=".0%"))
        else:
            top = frame.pivot(index="skill", columns="segment", values="share")
            chart(px.imshow(top, aspect="auto", color_continuous_scale="Teal", labels={"color": "Share"}))
            st.caption("Blank cells have no reported value among the top displayed combinations.")
    st.subheader("Skills mentioned together")
    table(cohort.pairs(20).round(3))
elif page == PAGES[3]:
    map_states(cohort)
    region = st.selectbox("Regional comparison", ["Connecticut", "New York City", "New York State",
                                                   "Massachusetts", "Remote U.S.", "Nationwide"])
    region_state = {"Connecticut": "CT", "New York State": "NY", "Massachusetts": "MA"}
    national_filters = replace(filters, state=None)
    national = Analytics(national_filters)
    regional = Analytics(replace(national_filters, state=region_state.get(region), region=region))
    comparison = pd.concat([national.summary().assign(region="Nationwide"), regional.summary().assign(region=region)])
    table(comparison[["region", "postings", "companies", "remote_jobs", "salary_jobs"]].drop_duplicates())
    st.caption("Regional comparisons use the selected source and other cohort filters. Regional definitions may overlap.")
    left, right = st.columns(2)
    with left:
        st.subheader("Roles")
        show_roles(regional)
        salary_detail(regional, "role")
    with right:
        st.subheader("Skills and experience")
        show_skill_bars(regional)
        table(regional.breakdown("experience"))
elif page == PAGES[4]:
    st.write("This cohort includes postings with description evidence of up to two years of experience and a "
             "separate group flagged by junior, associate, internship or entry-level title cues. "
             "Both built-in sources lack full descriptions, so their results are title signals.")
    selected = choice(st, "Career path", ROLES)
    early = Analytics(replace(filters, role=selected or filters.role, early=True))
    left, right = st.columns(2)
    with left:
        show_skill_bars(early)
        table(early.pairs(12, 2).round(3))
    with right:
        table(early.breakdown("state", 10))
        table(early.breakdown("remote"))
        salary_detail(early, "role")
elif page == PAGES[5]:
    dimension = st.selectbox("View by", ["role", "state", "remote"])
    skill = choice(st, "Skill mention", sorted(SKILL_ALIASES))
    frame = cohort.trends(dimension, skill)
    if frame.month.nunique() < 3:
        st.info("A trend requires at least three months of dated observations from an eligible source. "
                "The Zalize sample is a single snapshot of jobs present at collection.")
    else:
        st.write("Counts group 2023 source records by reported posting month. Search coverage and capture timing "
                 "can change, so month-to-month differences describe this dataset.")
        top_segments = frame.groupby("segment").postings.sum().nlargest(8).index
        chart(px.line(frame[frame.segment.isin(top_segments)], x="month", y="postings", color="segment",
                      markers=True, color_discrete_sequence=PALETTE))
        if frame.median_usd.notna().any():
            chart(px.line(frame[frame.median_usd.notna()], x="month", y="median_usd", color="segment"))
        else:
            st.caption("Comparable advertised USD salaries are unavailable for this trend source.")
        table(frame)
elif page == PAGES[6]:
    st.write("Estimate an advertised annual USD midpoint from the role, experience signal, state and work arrangement. "
             "Company size and skill inputs are excluded from this baseline.")
    if not ARTIFACT.exists():
        st.info("Run `python scripts/train.py` after ingesting Zalize to enable predictions.")
    else:
        bundle = load()
        with st.form("salary"):
            columns = st.columns(4)
            features = {field: column.selectbox(field.title(), values)
                        for column, (field, values) in zip(columns, bundle["options"].items(), strict=True)}
            submitted = st.form_submit_button("Estimate salary", type="primary")
        report = bundle["report"]
        if submitted:
            prediction = predict(bundle, features)
            st.metric("Predicted advertised midpoint", f"${prediction['prediction_usd']:,}")
            st.write(f"Estimated interval ${prediction['lower_usd']:,}–${prediction['upper_usd']:,}")
        st.caption(f"{report['selected']}  ·  {report['test']['sample']:,} held-out postings  ·  "
                   f"Empirical interval coverage {report['test_interval_coverage']:.1%}. "
                   "The salary-rich snapshot has limited generalizability.")
        table(pd.DataFrame([report["test"], report["test_median_baseline"]],
                           index=[report["selected"], "Median baseline"]).reset_index(names="Model").round(3))
        st.subheader("Predictive features")
        table(pd.Series(report["validation_permutation_mae_increase"], name="Validation MAE increase").round(2))
elif page == PAGES[7]:
    support = st.slider("Minimum joint mentions", 2, 100, 15)
    frame = cohort.pairs(70, support)
    frame = frame[frame.lift > 1]
    if frame.empty:
        st.info("No positive associations meet the selected support.")
    else:
        graph = nx.from_pandas_edgelist(frame, "skill_a", "skill_b", edge_attr="jaccard")
        communities = nx.community.greedy_modularity_communities(graph, weight="jaccard")
        position = nx.spring_layout(graph, seed=42, weight="jaccard")
        ex, ey = [], []
        for a, b in graph.edges():
            ex.extend([position[a][0], position[b][0], None])
            ey.extend([position[a][1], position[b][1], None])
        figure = go.Figure(go.Scatter(x=ex, y=ey, mode="lines", line={"color": "#acbaca", "width": 1},
                                     hoverinfo="skip", showlegend=False))
        for i, nodes in enumerate(communities, 1):
            nodes = sorted(nodes)
            figure.add_scatter(x=[position[n][0] for n in nodes], y=[position[n][1] for n in nodes],
                               text=nodes, mode="markers+text", textposition="top center",
                               marker={"size": [8+graph.degree[n] for n in nodes]}, name=f"Community {i}")
        figure.update_xaxes(visible=False)
        figure.update_yaxes(visible=False)
        chart(figure)
        st.caption("Edges require lift above 1. Ranking uses Jaccard overlap. Communities summarize this filtered sample.")
        table(frame.round(3))
elif page == PAGES[8]:
    left, middle, right = st.columns(3)
    title = left.text_input("Title contains", max_chars=100)
    company = middle.text_input("Company contains", max_chars=100)
    location = right.text_input("Location contains", max_chars=100)
    left, middle, right = st.columns(3)
    skill = choice(left, "Skill", sorted(SKILL_ALIASES))
    floor = middle.number_input("Minimum normalized salary (USD)", min_value=0, value=0, step=5000)
    page_number = right.number_input("Page", min_value=1, max_value=5000, value=1)
    explorer = Analytics(replace(filters, title=title, company=company, location=location, skill=skill,
                                 salary_floor=floor or None))
    table(explorer.jobs(100, (page_number - 1) * 100).drop(columns="job_id"))
    st.caption("Up to 100 historical postings per page.")
elif page == PAGES[9]:
    st.code("Pinned CSV / Parquet → immutable raw file → batch validation and rules\n"
            "→ deterministic deduplication → PostgreSQL / DuckDB → dbt and SQL → dashboard + API", language=None)
    st.subheader("Data sources")
    table(sources)
    st.subheader("Ingestion runs and data quality")
    runs = query("""select source, started_at, finished_at, status, report
                    from ingestion_runs order by started_at desc limit 20""")
    table(runs.drop(columns="report"))
    selected = runs[runs.source == source]
    if not selected.empty:
        st.json(selected.iloc[0].report)
    st.subheader("Database and transformations")
    st.write("Job postings reference title, employer, location and source tables. Salary facts attach to a "
             "single posting. A bridge joins jobs and skills. dbt builds staging views, joined facts and "
             "marts for salaries, skill demand, geography, work arrangement, seniority, trends and skill pairs.")
elif page == PAGES[10]:
    st.subheader("Historical DSC 101 results")
    st.write("The original study used 607 global salary observations. It reported test R² of 0.220, RMSE of "
             "$60,469, KNN test accuracy of approximately 52%, and three K-Means clusters.")
    st.subheader("DataPulse methods")
    st.write("Each dataset is analyzed separately. Title rules preserve multiple matches as ambiguous. "
             "Skill lists use a versioned alias dictionary and exact normalized matching. "
             "Posted dates and ingestion timestamps have separate meanings. No raw descriptions are served.")
    st.write("Annualization uses 2,080 hours for full-time hourly wages and 12 months for monthly wages. "
             "USD aggregates use eligible advertised values. Records without verified currency keep their original values.")
    st.write("The salary model uses employer-disjoint train, validation and test sets. Validation MAE selects the model "
             "and validation residuals set a heuristic interval. Coverage is measured on held-out records.")
    st.write("Signals from these samples describe the postings observed by the source. Use the data engineering page "
             "to check coverage and provenance before comparing segments.")
