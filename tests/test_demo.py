from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_aggregate_demo_keeps_cohorts_separate():
    path = Path(__file__).resolve().parents[1] / "demo" / "app.py"
    app = AppTest.from_file(str(path)).run()
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
