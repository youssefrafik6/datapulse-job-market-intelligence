import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


@pytest.mark.parametrize("endpoint", [
    "/health", "/summary", "/jobs?limit=1", "/skills", "/salary-statistics",
    "/locations", "/trends", "/data-quality", "/openapi.json",
])
def test_api_reads(snapshot, endpoint):
    response = client.get(endpoint)
    assert response.status_code == 200
    assert response.json()


def test_pagination_and_prediction_validation(snapshot):
    jobs = client.get("/jobs?limit=1").json()
    assert len(jobs["records"]) == 1
    assert client.get("/jobs?limit=201").status_code == 422
    assert client.get("/trends").json()["available"] is False
    assert client.post("/salary-predict", json={"role": "Analyst"}).status_code == 422
    assert client.post("/salary-predict", json={
        "role": "Data Analyst", "state": "CT", "experience": "Unknown", "remote": "Remote",
    }).status_code == 503
