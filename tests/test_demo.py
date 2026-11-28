from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_aggregate_demo_keeps_cohorts_separate(monkeypatch, tmp_path):
    from datapulse import store

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "missing.duckdb")
    path = Path(__file__).resolve().parents[1] / "dashboard" / "app.py"
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


def test_full_hosted_dashboard_builds_and_reuses_snapshot(monkeypatch, tmp_path, snapshot):
    from datapulse import hosted, store

    source_file, _, _ = snapshot
    source_file = source_file.resolve()
    monkeypatch.setattr(store, "DB_FILE", tmp_path / "missing.duckdb")
    downloads = []

    def fixture_download(source, *, raw):
        downloads.append(source)
        return source_file

    monkeypatch.setattr(hosted, "download", fixture_download)
    hosted.snapshot.clear()
    try:
        path = Path(__file__).resolve().parents[1] / "dashboard" / "full.py"
        app = AppTest.from_file(str(path), default_timeout=30).run()
        assert not app.exception
        assert not app.error
        assert app.metric[0].value == "3"
        assert len(app.sidebar.radio[0].options) == 11

        app.sidebar.radio[0].set_value("Data Explorer").run()
        assert not app.exception
        assert len(app.dataframe[0].value) == 3
        assert downloads == ["zalize"]
    finally:
        hosted.snapshot.clear()
