from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest


@pytest.mark.parametrize("entrypoint", ["app.py", "full.py"])
def test_aggregate_demo_keeps_cohorts_separate(monkeypatch, tmp_path, entrypoint):
    from datapulse import store

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "missing.duckdb")
    path = Path(__file__).resolve().parents[1] / "dashboard" / entrypoint
    app = AppTest.from_file(str(path), default_timeout=30).run()
    assert not app.exception
    assert app.metric[0].value == "204,273"
    assert app.metric[2].value == "0.0%"
    assert "does not establish currency" in app.info[0].value
    assert any(h.value == "Monthly remote share" for h in app.subheader)
    app.radio[0].set_value("zalize").run()
    assert not app.exception
    assert app.metric[0].value == "13,371"
    assert app.metric[2].value == "74.7%"
    assert not app.info
    assert all(h.value != "Monthly remote share" for h in app.subheader)
