from __future__ import annotations

import json
import threading
from datetime import datetime, timedelta, timezone
from http.server import HTTPServer
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from skillgraph_tutor.analytics import dashboard_snapshot, load_cohort
from skillgraph_tutor.dashboard_server import make_handler
from skillgraph_tutor.demo_data import create_demo_workspace
from skillgraph_tutor.graph import parse_syllabus_markdown
from skillgraph_tutor.insights import (
    HISTORY_WINDOW_WEEKS,
    build_insights,
    concept_growth,
    select_learners,
    trajectory,
)
from skillgraph_tutor.student import HISTORY_LIMIT, StudentState

NOW = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


@pytest.fixture()
def cohort(tmp_path):
    create_demo_workspace(tmp_path / "demo", now=NOW)
    return load_cohort(tmp_path / "demo")


def test_update_mastery_records_bounded_history_that_round_trips():
    student = StudentState(student_id="s1", name="Test Learner")
    for step in range(HISTORY_LIMIT + 5):
        student.update_mastery("Loops", True, 0.5, now=NOW + timedelta(hours=step))
    history = student.concepts["Loops"].history
    assert len(history) == HISTORY_LIMIT
    assert history[-1] == (
        student.concepts["Loops"].updated_at,
        round(student.concepts["Loops"].mastery, 4),
    )
    restored = StudentState.from_dict(json.loads(json.dumps(student.to_dict())))
    assert restored.concepts["Loops"].history == history


def test_legacy_records_without_history_still_load():
    restored = StudentState.from_dict(
        {"student_id": "s1", "name": "Legacy", "concepts": {"Loops": {"mastery": 0.5}}}
    )
    assert restored.concepts["Loops"].history == []


def test_scope_selection(cohort):
    _, students, meta = cohort
    assert len(select_learners(students, meta, "cohort")) == 16
    assert len(select_learners(students, meta, "group:Engineering")) == 5
    assert [s.student_id for s in select_learners(students, meta, "learner:learner-03")] == [
        "learner-03"
    ]
    with pytest.raises(LookupError):
        select_learners(students, meta, "group:Nobody")
    with pytest.raises(ValueError):
        select_learners(students, meta, "everyone")


def test_trajectory_history_ends_at_snapshot_mean_and_scenarios_diverge(cohort):
    graph, students, meta = cohort
    result = trajectory(graph, students, NOW, weeks_ahead=8)
    history = result["history"]
    assert len(history) == HISTORY_WINDOW_WEEKS + 1
    assert (
        history[-1]["mean"]
        == dashboard_snapshot(graph, students, meta, NOW)["metrics"]["meanMastery"]
    )
    assert history[0]["observed"] < history[-1]["observed"]
    practice = [p["mean"] for p in result["practice"]]
    idle = [p["mean"] for p in result["noPractice"]]
    assert len(practice) == len(idle) == 9
    assert practice[0] == idle[0] == history[-1]["mean"]
    assert practice == sorted(practice)
    assert idle == sorted(idle, reverse=True)
    assert all(0 <= value <= 1 for value in practice + idle)
    assert "not predictions" in result["assumptions"]["disclaimer"]


def test_trajectory_marks_unobserved_weeks_as_missing():
    graph = parse_syllabus_markdown("# Course\n## Loops\n")
    student = StudentState(student_id="s1", name="New Learner")
    student.update_mastery("Loops", True, 1.0, now=NOW - timedelta(days=1))
    result = trajectory(graph, [student], NOW, weeks_ahead=2)
    assert result["history"][0] == {
        "date": (NOW - timedelta(weeks=HISTORY_WINDOW_WEEKS)).isoformat(),
        "mean": None,
        "observed": 0,
    }
    assert result["history"][-1]["observed"] == 1


def test_growth_and_insights_are_deterministic(cohort):
    graph, students, meta = cohort
    growth = concept_growth(graph, students, NOW)
    assert [g["name"] for g in growth] == list(graph.nodes)
    assert all(g["delta"] > 0 for g in growth if g["delta"] is not None)
    snapshot = dashboard_snapshot(graph, students, meta, NOW)
    projection = trajectory(graph, students, NOW)
    first = build_insights(snapshot, growth, projection)
    assert first == build_insights(snapshot, growth, projection)
    kinds = [item["kind"] for item in first]
    assert kinds == ["growth", "bottleneck", "projection", "reviews"]
    for item in first:
        assert all(name in item["text"] for name in item["concepts"])


def test_insights_handle_empty_cohort():
    graph = parse_syllabus_markdown("# Course\n## Loops\n")
    snapshot = dashboard_snapshot(graph, [], {}, NOW)
    projection = trajectory(graph, [], NOW)
    assert build_insights(snapshot, concept_growth(graph, [], NOW), projection) == []


@pytest.fixture()
def server(tmp_path):
    root = create_demo_workspace(tmp_path / "demo")
    httpd = HTTPServer(("127.0.0.1", 0), make_handler(root))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    httpd.server_close()


def test_insights_endpoint(server):
    with urlopen(server + "/api/insights?scope=group%3AOperations&weeks=4", timeout=5) as response:
        payload = json.loads(response.read())
    assert payload["learners"] == 6
    assert len(payload["trajectory"]["practice"]) == 5
    assert payload["insights"]
    with urlopen(server + "/insights.js", timeout=5) as response:
        assert response.headers["Content-Type"].startswith("text/javascript")


@pytest.mark.parametrize(
    ("query", "status"),
    [("scope=everyone", 400), ("weeks=0", 400), ("weeks=abc", 400), ("scope=learner%3Anope", 404)],
)
def test_insights_endpoint_rejects_bad_input(server, query, status):
    with pytest.raises(HTTPError) as error:
        urlopen(server + "/api/insights?" + query, timeout=5)
    assert error.value.code == status
