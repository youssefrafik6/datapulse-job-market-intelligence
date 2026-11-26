"""Versioned, deterministic title and skill rules."""
import ast
import math
import re

ROLES = {
    "Data Analyst": r"\b(data analyst|analytics specialist)\b",
    "Business Intelligence Analyst": r"\b(business intelligence|bi (analyst|developer))\b",
    "Data Scientist": r"\bdata scien(tist|ce)\b",
    "Data Engineer": r"\bdata (engineer|engineering)\b",
    "Analytics Engineer": r"\banalytics (engineer|engineering)\b",
    "Machine Learning Engineer": r"\b(machine learning|ml) (engineer|scientist)\b",
    "AI Engineer": r"\b(ai|artificial intelligence|llm)( systems?)? engineer\b",
    "Software Engineer": r"\b(software (engineer|developer)|full[ -]stack (engineer|developer))\b",
    "Cloud Engineer": r"\b(cloud|devops|platform|site reliability) engineer\b",
}
EXPERIENCES = ("Entry", "Mid", "Senior", "Executive", "Unknown")
REMOTE = ("Remote", "Hybrid", "On-site", "Unspecified")
SKILL_ALIASES = {
    "Python": ["python"], "SQL": ["sql"], "R": ["r"], "Excel": ["excel", "microsoft excel"],
    "Tableau": ["tableau"], "Power BI": ["power bi", "powerbi"], "Snowflake": ["snowflake"],
    "dbt": ["dbt"], "AWS": ["aws", "amazon web services"], "Azure": ["azure", "microsoft azure"],
    "Google Cloud": ["google cloud", "gcp", "google cloud platform"], "Docker": ["docker"],
    "Kubernetes": ["kubernetes", "k8s"], "Spark": ["spark", "apache spark"], "PySpark": ["pyspark"],
    "Databricks": ["databricks"], "Airflow": ["airflow", "apache airflow"], "Git": ["git"],
    "PostgreSQL": ["postgresql", "postgres"], "SQL Server": ["sql server", "ms sql server", "mssql"],
    "Machine Learning": ["machine learning", "machine-learning"], "Deep Learning": ["deep learning", "deep-learning"],
    "NLP": ["nlp", "natural language processing"], "TensorFlow": ["tensorflow"], "PyTorch": ["pytorch"],
    "FastAPI": ["fastapi"], "Java": ["java"], "Scala": ["scala"], "Go": ["go", "golang"],
    "JavaScript": ["javascript"], "TypeScript": ["typescript"], "SAS": ["sas"],
    "Looker": ["looker"], "BigQuery": ["bigquery"], "Kafka": ["kafka"], "Pandas": ["pandas"],
    "NumPy": ["numpy"], "React": ["react"], "Linux": ["linux"], "LLM": ["llm", "large language models"],
    "C++": ["c++"], "C#": ["c#"], "MySQL": ["mysql"], "NoSQL": ["nosql"],
    "PowerPoint": ["powerpoint"], "Hadoop": ["hadoop"], "Redis": ["redis"],
    "MongoDB": ["mongodb"], "Terraform": ["terraform"], "GitHub": ["github"],
    "ETL": ["etl"], "CI/CD": ["ci/cd"], "Jenkins": ["jenkins"], "DAX": ["dax"],
}
ALIASES = {alias: skill for skill, values in SKILL_ALIASES.items() for alias in values}
TEXT_ALIASES = {alias: skill for alias, skill in ALIASES.items() if alias not in {
    "r", "go", "spark", "excel", "git", "react",
}}
TEXT_PATTERN = re.compile(
    r"(?<![\w+#])(" + "|".join(map(re.escape, sorted(TEXT_ALIASES, key=len, reverse=True))) +
    r")(?![\w+#])", re.I,
)
STATE_PAIRS = """AL Alabama|AK Alaska|AZ Arizona|AR Arkansas|CA California|CO Colorado|
CT Connecticut|DE Delaware|DC District of Columbia|FL Florida|GA Georgia|HI Hawaii|
ID Idaho|IL Illinois|IN Indiana|IA Iowa|KS Kansas|KY Kentucky|LA Louisiana|
ME Maine|MD Maryland|MA Massachusetts|MI Michigan|MN Minnesota|MS Mississippi|
MO Missouri|MT Montana|NE Nebraska|NV Nevada|NH New Hampshire|NJ New Jersey|
NM New Mexico|NY New York|NC North Carolina|ND North Dakota|OH Ohio|OK Oklahoma|
OR Oregon|PA Pennsylvania|RI Rhode Island|SC South Carolina|SD South Dakota|
TN Tennessee|TX Texas|UT Utah|VT Vermont|VA Virginia|WA Washington|
WV West Virginia|WI Wisconsin|WY Wyoming"""
STATES = {part.strip()[:2]: part.strip()[3:] for part in STATE_PAIRS.split("|")}
STATE_NAMES = {name.casefold(): code for code, name in STATES.items()}


def classify_title(title):
    candidates = tuple(role for role, pattern in ROLES.items() if re.search(pattern, title, re.I))
    if len(candidates) > 1:
        return "Ambiguous", candidates
    return (candidates[0] if candidates else "Other Technology"), candidates


def experience(title, description=""):
    pattern = r"\b(\d{1,2})\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:relevant\s+|professional\s+)?experience\b"
    years = [int(match) for match in re.findall(pattern, description, re.I)]
    minimum = min(years, default=None)
    if re.search(r"\b(chief|vice president|vp)\b", title, re.I):
        return "Executive", minimum, "title signal"
    if re.search(r"\b(senior|sr|staff|principal|lead|director)\b", title, re.I):
        return "Senior", minimum, "title signal"
    if minimum is not None:
        return ("Entry" if minimum <= 2 else "Mid"), minimum, "description heuristic"
    if re.search(r"\b(entry.level|jr|junior|associate|intern)\b", title, re.I):
        return "Unknown", None, "early-career title signal"
    if re.search(r"\b(mid.level|intermediate)\b", title, re.I):
        return "Mid", None, "title signal"
    return "Unknown", None, "unspecified"


def skills_from_text(description):
    skills = {TEXT_ALIASES[match.group().lower()] for match in TEXT_PATTERN.finditer(description)}
    for skill, pattern in {
        "R": r"\bR (?:programming|language)\b",
        "Go": r"\bGo (?:programming|language)\b",
        "Excel": r"\b(?:advanced Excel|Excel (?:skills|formulas|macros))\b",
        "Git": r"\bGit\b",
        "Spark": r"\b(?:Apache Spark|Spark SQL)\b",
        "React": r"\bReact(?:\.js| framework)\b",
    }.items():
        if re.search(pattern, description):
            skills.add(skill)
    return skills


def supplied_skills(value):
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value) if len(value) <= 8192 else []
        except (ValueError, SyntaxError, RecursionError):
            return set(), 0, True
    if not isinstance(value, (list, tuple)):
        return set(), 0, value is not None
    strings = {item.strip().lower() for item in value if isinstance(item, str) and item.strip()}
    return {ALIASES[alias] for alias in strings & ALIASES.keys()}, len(strings - ALIASES.keys()), False


def location_parts(raw):
    parts = [part.strip() for part in raw.split(",")]
    if len(parts) > 1 and parts[-1].casefold() in {"us", "usa", "united states"}:
        parts.pop()
    tail = parts[-1]
    code = tail if tail in STATES else STATE_NAMES.get(tail.casefold())
    city = parts[-2] if code and len(parts) > 1 else None
    if raw.casefold() in {"nyc", "new york city"}:
        return "New York", "NY", True
    nyc = code == "NY" and (city or "").casefold() in {
        "new york", "new york city", "manhattan", "brooklyn", "bronx", "queens", "staten island",
    }
    return city, code, nyc


def remote_status(raw, source_flag):
    hybrid = bool(re.search(r"\bhybrid\b", raw, re.I))
    onsite = bool(re.search(r"\bon[ -]?site\b", raw, re.I))
    remote = source_flag is True or bool(re.search(r"\b(remote|anywhere)\b", raw, re.I))
    if onsite and remote and not hybrid:
        return "Unspecified", True
    if hybrid:
        return "Hybrid", False
    if remote:
        return "Remote", False
    return ("On-site" if onsite else "Unspecified"), False


def normalize_salary(lower, upper, point, period, currency, origin, fx=None, full_time=False):
    """Annualize only when the schedule supports it. Never manufacture an endpoint."""
    inputs = (lower, upper, point)
    if all(value is None for value in inputs):
        return None, None
    try:
        low, high, midpoint = [float(value) if value is not None else None for value in inputs]
    except (ValueError, TypeError, OverflowError):
        return None, "invalid_salary"
    if any(value is not None and (value <= 0 or not math.isfinite(value)) for value in (low, high, midpoint)):
        return None, "invalid_salary"
    if low is not None and high is not None and high < low:
        return None, "invalid_salary"
    if origin not in {"advertised", "source_reported", "estimated"}:
        raise ValueError("Unknown salary origin")
    multiplier = {"year": 1, "month": 12, "hour": 2080 if full_time else None}.get(period)
    rate = 1.0 if currency == "USD" else fx
    valid_rate = rate is not None and math.isfinite(rate) and rate > 0
    scale = multiplier * rate if multiplier and valid_rate else None
    if origin == "estimated":
        scale = None
    if midpoint is None and low is not None and high is not None:
        midpoint = low + (high - low) / 2
    result = {
        "original_low": low, "original_high": high, "original_point": point and float(point),
        "period": period, "currency": currency, "salary_origin": origin,
        "annual_low": low * scale if low is not None and scale else None,
        "annual_high": high * scale if high is not None and scale else None,
        "annual_usd": midpoint * scale if midpoint is not None and scale else None,
    }
    flag = "unsupported_currency" if not valid_rate else "unsupported_period" if not multiplier else None
    return result, flag
