from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone

import pytest

from skillgraph_tutor.analytics import (
    _cell_for_spreadsheet,
    cohort_csv,
    dashboard_snapshot,
    load_cohort,
)
from skillgraph_tutor.demo_data import NAMES, create_demo_workspace
from skillgraph_tutor.graph import parse_syllabus_markdown
from skillgraph_tutor.student import StudentState

NOW = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


def test_seeded_demo_is_reproducible_and_non_destructive(tmp_path):
    root = tmp_path / "demo"
    create_demo_workspace(root, now=NOW)
    graph, students, meta = load_cohort(root)
    assert len(graph.nodes) == 9
    assert len(students) == len(NAMES) == 16
    assert meta["synthetic"] is True
    assert len(meta["groups"]) == 16
    assert {student.student_id for student in students} == {item[0] for item in NAMES}
    original = (root / "students" / "learner-01.json").read_bytes()
    create_demo_workspace(root, now=NOW + timedelta(days=12))
    assert (root / "students" / "learner-01.json").read_bytes() == original
    other = tmp_path / "other"
    create_demo_workspace(other, now=NOW)
    assert (other / "students" / "learner-01.json").read_bytes() == original


def test_demo_never_overwrites_an_existing_real_workspace(tmp_path):
    root = tmp_path / "live"
    root.mkdir()
    (root / "graph.json").write_text('{"nodes":[]}', encoding="utf-8")
    with pytest.raises(FileExistsError):
        create_demo_workspace(root, now=NOW)


def test_snapshot_coverage_due_and_missingness(tmp_path):
    root = tmp_path / "demo"
    create_demo_workspace(root, now=NOW)
    graph, students, meta = load_cohort(root)
    result = dashboard_snapshot(graph, students, meta, now=NOW)
    metrics = result["metrics"]
    assert result["sample"] is True
    assert metrics["learners"] == 16
    assert metrics["concepts"] == 9
    assert metrics["observations"] < metrics["possibleObservations"]
    assert metrics["dueReviews"] > 0
    assert len(result["groups"]) == 3
    assert sum(v for v in metrics["supportBands"].values()) == 16
    assert any(c["mastery"] is None for row in result["students"] for c in row["concepts"])
    assert sum(row["dueCount"] for row in result["students"]) == metrics["dueReviews"]


def test_unattempted_is_not_implicitly_a_due_review():
    graph = parse_syllabus_markdown("## Basics\n## Functions\nrequires: Basics")
    student = StudentState(student_id="s", name="Synthetic")
    student.concept("Basics").mastery = 0.5
    result = dashboard_snapshot(graph, [student], now=NOW)
    learner = result["students"][0]
    assert learner["dueCount"] == 0
    assert learner["concepts"][0]["dueAt"] is None
    assert learner["concepts"][1]["status"] == "not_started"
    assert result["concepts"][1]["mean"] is None
    assert learner["meanMastery"] == 0.5


@pytest.mark.parametrize("input_value", ["=SUM(1,1)", "+42", "-4", "@cmd", "\t=test", " =1"])
def test_spreadsheet_formula_injection_is_escaped(input_value):
    assert _cell_for_spreadsheet(input_value).startswith("'")


def test_csv_has_all_concept_cells_and_labeled_source(tmp_path):
    root = tmp_path / "demo"
    create_demo_workspace(root, now=NOW)
    payload = dashboard_snapshot(*load_cohort(root), now=NOW)
    reader = list(csv.DictReader(io.StringIO(cohort_csv(payload))))
    assert len(reader) == 16 * 9
    assert all(row["Data source"] == "Synthetic demonstration" for row in reader)
    assert any(row["Status"] == "not_started" and not row["Mastery estimate"] for row in reader)
    assert not any("predicted" in row["Support band"].lower() for row in reader)
