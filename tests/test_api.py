"""API tests: decisions must update status AND write an audit row, and bad input must be rejected."""
import pytest
from fastapi.testclient import TestClient

from service import db
from service.api import app

client = TestClient(app)


@pytest.fixture()
def study():
    sid = "test-study-1"
    with db.conn() as c:
        c.execute("DELETE FROM audit_log")
        c.execute("DELETE FROM results")
        c.execute(
            "INSERT INTO results (study_id, probability, predicted_positive, threshold, model_version, heatmap_path) "
            "VALUES (?,?,?,?,?,?)",
            (sid, 0.91, 1, 0.34, "test-model", "none.png"),
        )
    return sid


def test_list_and_get(study):
    assert [s["study_id"] for s in client.get("/studies").json()] == [study]
    assert client.get(f"/studies/{study}").json()["status"] == "pending"


def test_unknown_study_404():
    assert client.get("/studies/nope").status_code == 404
    r = client.post("/studies/nope/decision", json={"reviewer": "Dr A", "decision": "approved"})
    assert r.status_code == 404


def test_decision_updates_status_and_writes_audit(study):
    r = client.post(f"/studies/{study}/decision", json={"reviewer": "Dr A", "decision": "approved", "comment": "ok"})
    assert r.status_code == 200
    assert client.get(f"/studies/{study}").json()["status"] == "approved"
    log = client.get(f"/studies/{study}/audit").json()
    assert len(log) == 1
    assert log[0]["reviewer"] == "Dr A" and log[0]["decision"] == "approved"
    assert log[0]["model_version"] == "test-model" and log[0]["probability"] == pytest.approx(0.91)


def test_history_is_append_only(study):
    client.post(f"/studies/{study}/decision", json={"reviewer": "Dr A", "decision": "approved"})
    client.post(f"/studies/{study}/decision", json={"reviewer": "Dr B", "decision": "rejected"})
    log = client.get("/audit").json()
    assert [a["decision"] for a in log] == ["rejected", "approved"]  # both kept, newest first
    assert client.get(f"/studies/{study}").json()["status"] == "rejected"


@pytest.mark.parametrize(
    "body",
    [
        {"reviewer": "", "decision": "approved"},        # empty reviewer
        {"reviewer": "Dr A", "decision": "maybe"},       # invalid decision
        {"decision": "approved"},                        # missing reviewer
    ],
)
def test_invalid_decision_rejected(study, body):
    assert client.post(f"/studies/{study}/decision", json=body).status_code == 422
    assert client.get(f"/studies/{study}/audit").json() == []


def test_image_endpoints_resolve_windows_style_paths(study):
    """Rows written on Windows store 'folder\\file.png'. They must still resolve on Linux/Docker."""
    import os
    from service.api import HEATMAP_DIR

    os.makedirs(HEATMAP_DIR, exist_ok=True)
    for name in ("win-study.png", "win-study_orig.png"):
        with open(os.path.join(HEATMAP_DIR, name), "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
    with db.conn() as c:
        c.execute(
            "INSERT INTO results (study_id, probability, predicted_positive, threshold, model_version, heatmap_path) "
            "VALUES (?,?,?,?,?,?)",
            ("win-study", 0.5, 1, 0.34, "m", "service/data/heatmaps\\win-study.png"),
        )
    assert client.get("/studies/win-study/image").status_code == 200
    assert client.get("/studies/win-study/heatmap").status_code == 200
    assert client.get("/studies/test-study-1/image").status_code == 404  # file missing -> clean 404, not a crash
