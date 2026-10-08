from __future__ import annotations

import json
import threading
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from skillgraph_tutor.dashboard_server import make_handler
from skillgraph_tutor.demo_data import create_demo_workspace


@pytest.fixture()
def local_dashboard(tmp_path):
    root = create_demo_workspace(tmp_path / "demo")
    server = HTTPServer(("127.0.0.1", 0), make_handler(root))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    yield base
    server.shutdown()
    thread.join(timeout=4)
    server.server_close()


def fetch_json(base, path, payload=None, headers=None):
    values = {"Content-Type": "application/json", **(headers or {})}
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    with urlopen(Request(base + path, data=body, headers=values), timeout=5) as response:
        return json.loads(response.read())


def test_dashboard_and_static_assets(local_dashboard):
    payload = fetch_json(local_dashboard, "/api/dashboard")
    assert payload["sample"] is True
    assert payload["metrics"]["learners"] == 16
    assert "methodology" in payload
    for route, media in [
        ("/", "text/html"),
        ("/app.js", "text/javascript"),
        ("/styles.css", "text/css"),
        ("/favicon.svg", "image/svg+xml"),
    ]:
        with urlopen(local_dashboard + route, timeout=5) as response:
            assert media in response.headers["Content-Type"]
            assert response.headers["Content-Security-Policy"].startswith("default-src")
            assert len(response.read()) > 200


def test_student_lookup_assessment_and_socratic_prompt(local_dashboard):
    id_value = "learner-01"
    concept = "Python Essentials"
    before = fetch_json(local_dashboard, "/api/student?id=" + id_value)
    item = next(c for c in before["concepts"] if c["concept"] == concept)
    result = fetch_json(
        local_dashboard,
        "/api/attempt",
        {"studentId": id_value, "concept": concept, "correct": True, "confidence": 0.9},
    )
    assert result["after"] > item["mastery"]
    assert result["synthetic"] is True
    after = fetch_json(local_dashboard, "/api/student?id=" + id_value)
    new_item = next(c for c in after["concepts"] if c["concept"] == concept)
    assert new_item["mastery"] == round(result["after"], 4)
    assert new_item["dueAt"]
    tutor = fetch_json(
        local_dashboard,
        "/api/tutor",
        {"studentId": id_value, "concept": concept, "response": "An input is a string."},
    )
    assert tutor["type"] == "template-guided"
    assert "?" in tutor["question"]
    assert "no LLM" in tutor["disclosure"]


def test_rejects_bad_student_path_and_invalid_confidence(local_dashboard):
    for path in ("/api/student?id=../../etc/passwd", "/api/student?id=unknown"):
        with pytest.raises(HTTPError) as error:
            fetch_json(local_dashboard, path)
        assert error.value.code in (400, 404)
    with pytest.raises(HTTPError) as error:
        fetch_json(
            local_dashboard,
            "/api/attempt",
            {"studentId": "learner-01", "concept": "Python Essentials",
             "correct": True, "confidence": 10},
        )
    assert error.value.code == 400


def test_rejects_cross_origin_write(local_dashboard):
    with pytest.raises(HTTPError) as error:
        fetch_json(
            local_dashboard,
            "/api/attempt",
            {"studentId": "learner-01", "concept": "Python Essentials",
             "correct": False, "confidence": 0.7},
            headers={"Origin": "https://untrusted.example"},
        )
    assert error.value.code == 403


def test_exports_are_accessible_and_descriptive(local_dashboard):
    with urlopen(local_dashboard + "/api/export.csv", timeout=5) as response:
        csv_data = response.read().decode("utf-8-sig")
    assert "Learner ID" in csv_data
    assert "Synthetic demonstration" in csv_data
    assert len(csv_data.splitlines()) > 140
    export = fetch_json(local_dashboard, "/api/export.json")
    assert export["sample"] is True
    assert "students" in export
