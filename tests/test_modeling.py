import pandas as pd
import pytest
from tests_fixtures import make_salary_file

from datapulse.modeling import FEATURES, load, partition, predict, train
from datapulse.pipeline import build


def test_disjoint_partitions():
    data = pd.DataFrame({"company_id": [f"company-{i % 30}" for i in range(600)],
                         "job_id": list(range(600))})
    parts = partition(data)
    groups = [set(frame.company_id) for frame in parts]
    assert not groups[0] & groups[1] and not groups[0] & groups[2] and not groups[1] & groups[2]
    assert sum(map(len, parts)) == 600


def test_small_input_refuses_to_train(snapshot):
    _, path, _ = snapshot
    with pytest.raises(ValueError, match="200"):
        train(path)


def test_training_and_inference(tmp_path, monkeypatch, raw_rows):
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "jobs.duckdb"
    raw = make_salary_file(tmp_path, raw_rows[0])
    build(raw, "zalize", path)
    report = train(path)
    bundle = load()
    sample = {field: bundle["options"][field][0] for field in FEATURES}
    response = predict(bundle, sample)
    assert report["test"]["sample"] > 20
    assert response["lower_usd"] <= response["prediction_usd"] <= response["upper_usd"]
    with pytest.raises(ValueError):
        predict(bundle, {**sample, "role": "Unsupported title"})
