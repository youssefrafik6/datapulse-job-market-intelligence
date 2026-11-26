"""Pinned inputs and bounded CSV/Parquet readers."""
import csv
import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.request import urlopen


@dataclass(frozen=True)
class Source:
    repo: str
    revision: str
    file: str
    license: str
    trend_eligible: bool
    sha256: str = ""

    @property
    def url(self):
        return f"https://huggingface.co/datasets/{self.repo}"

    @property
    def download_url(self):
        return f"{self.url}/resolve/{self.revision}/{self.file}"


SOURCES = {
    "luke": Source("lukebarousse/data_jobs", "ed776e5a0a8c40ea9d5efbd800772ae52e140f3e",
                   "data_jobs.csv", "Apache-2.0", True,
                   "635241ed09ccee18bdae1f83b45f26d6759e0aa2513c529f6190e9054062436c"),
    "zalize": Source("zalizedata/tech-job-postings-salary-dataset", "2314a3ac6897d6a454d53a1120ec3a540e82907d",
                     "data/S/jobs-00000-of-00001.parquet", "CC BY-NC 4.0", False, "425ddd62f254e317183002823c711e153f00fae8507f7e2d93d0a7e291ca7ed8"),
}
RAW = Path("data/raw")
REQUIRED = {
    "luke": {"job_title", "job_country", "job_location", "job_posted_date", "company_name",
             "job_work_from_home", "salary_rate", "salary_year_avg", "salary_hour_avg", "job_skills"},
    "zalize": {"title", "country", "location_raw", "company_name", "job_id", "is_remote",
               "posted_at", "scraped_at", "salary_min", "salary_max", "salary_currency",
               "salary_period", "skills"},
}


def checksum(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def download(key):
    source = SOURCES[key]
    destination = RAW / key / Path(source.file).name
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if source.sha256 and checksum(destination) != source.sha256:
            raise ValueError(f"Unexpected checksum for {destination}")
        return destination
    pending = destination.with_suffix(".download")
    try:
        digest = hashlib.sha256()
        with urlopen(source.download_url, timeout=120) as response, pending.open("wb") as output:
            while block := response.read(1024 * 1024):
                digest.update(block)
                output.write(block)
        if source.sha256 and digest.hexdigest() != source.sha256:
            raise ValueError(f"Unexpected checksum for {destination}")
        pending.replace(destination)
    finally:
        pending.unlink(missing_ok=True)
    return destination


def records(path, key):
    def validate(columns):
        missing = REQUIRED[key] - set(columns or [])
        if missing:
            raise ValueError(f"Missing columns for {key}: {', '.join(sorted(missing))}")

    if path.suffix == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            validate(reader.fieldnames)
            yield from reader
    elif path.suffix == ".parquet":
        from pyarrow.parquet import ParquetFile

        with ParquetFile(path) as file:
            validate(file.schema_arrow.names)
            columns = REQUIRED[key] | {"description", "ats", "ats_token", "url", "employment_type"}
            for batch in file.iter_batches(columns=list(columns & set(file.schema_arrow.names)), batch_size=8192):
                yield from batch.to_pylist()
    else:
        raise ValueError("Expected CSV or Parquet")
