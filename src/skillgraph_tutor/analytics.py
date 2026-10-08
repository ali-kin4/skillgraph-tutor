"""Explainable cohort analytics derived from SkillGraph's existing student states.

No predictive model is fitted here: risk labels are transparent instructional rules.
Missing mastery observations remain missing, never silently imputed.
"""

from __future__ import annotations

import csv
import io
import json
import math
from datetime import datetime, timezone
from pathlib import Path

from .graph import ConceptGraph, load_graph
from .student import StudentState, load_student


def _as_utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 4) if values else None


def load_cohort(workspace: str | Path) -> tuple[ConceptGraph, list[StudentState], dict]:
    """Read only the intended graph, student directory, and optional demo metadata."""
    root = Path(workspace)
    graph = load_graph(root / "graph.json")
    students = []
    folder = root / "students"
    if folder.is_dir():
        for path in sorted(folder.glob("*.json")):
            if path.is_symlink() or not path.is_file():
                continue
            students.append(load_student(path))
    metadata = {}
    meta_path = root / "cohort_metadata.json"
    if meta_path.is_file() and not meta_path.is_symlink():
        raw = json.loads(meta_path.read_text(encoding="utf-8"))
        if isinstance(raw, dict):
            metadata = raw
    return graph, students, metadata


def _student_details(graph: ConceptGraph, student: StudentState, now: datetime, group: str) -> dict:
    names = list(graph.nodes)
    values = [
        student.concepts[name].mastery
        for name in names
        if name in student.concepts and math.isfinite(student.concepts[name].mastery)
    ]
    reviewed = []
    weak = []
    due = []
    observations = []
    for name in names:
        concept = student.concepts.get(name)
        if concept is None:
            observations.append(
                {"concept": name, "mastery": None, "dueAt": None, "status": "not_started"}
            )
            continue
        value = float(max(0.0, min(1.0, concept.mastery)))
        deadline = _as_utc(concept.reviews.due_at)
        is_due = deadline is not None and deadline <= now
        if is_due:
            due.append(name)
        if value < 0.6:
            weak.append(name)
        if deadline:
            reviewed.append(name)
        observations.append(
            {
                "concept": name,
                "mastery": round(value, 4),
                "dueAt": deadline.isoformat() if deadline else None,
                "status": "due" if is_due else "needs_practice" if value < 0.6 else "on_track",
            }
        )

    # Descriptive screening heuristics, not dropout/attainment predictions.
    if len(due) >= 3 or (values and min(values) < 0.4):
        support = "Needs support"
    elif due or len(weak) >= 2:
        support = "Monitor"
    else:
        support = "On track"
    if not values:
        support = "Unassessed"

    focus = sorted(
        (obs for obs in observations if obs["mastery"] is not None),
        key=lambda x: (x["mastery"], x["concept"]),
    )
    if due:
        recommendation = "Schedule review: " + due[0]
    elif focus and focus[0]["mastery"] < 0.6:
        recommendation = "Practice: " + focus[0]["concept"]
    else:
        unseen = [obs["concept"] for obs in observations if obs["mastery"] is None]
        recommendation = "Introduce: " + unseen[0] if unseen else "Continue spaced reviews"

    return {
        "id": student.student_id,
        "name": student.name,
        "group": group,
        "meanMastery": _mean(values),
        "observed": len(values),
        "totalConcepts": len(names),
        "coverage": round(len(values) / len(names), 4) if names else 0,
        "dueCount": len(due),
        "weakCount": len(weak),
        "support": support,
        "recommendation": recommendation,
        "concepts": observations,
        "dueReviews": sorted(due),
        "scheduledReviews": len(reviewed),
    }


def dashboard_snapshot(
    graph: ConceptGraph,
    students: list[StudentState],
    metadata: dict | None = None,
    now: datetime | None = None,
) -> dict:
    """Generate a deterministic, explicitly labelled cohort snapshot."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    now = now.astimezone(timezone.utc)
    metadata = metadata or {}
    cohorts = metadata.get("groups", {})
    if not isinstance(cohorts, dict):
        cohorts = {}
    rows = [
        _student_details(graph, s, now, str(cohorts.get(s.student_id, "Unassigned")))
        for s in students
    ]
    rows.sort(key=lambda row: (row["name"].casefold(), row["id"]))
    names = list(graph.nodes)
    concepts = []
    for name in names:
        seen = [
            row["concepts"][i]["mastery"]
            for row in rows
            for i, node in enumerate(names)
            if node == name and row["concepts"][i]["mastery"] is not None
        ]
        weak = sum(value < 0.6 for value in seen)
        concepts.append(
            {
                "name": name,
                "requires": sorted(graph.nodes[name].requires),
                "mean": _mean(seen),
                "observed": len(seen),
                "unobserved": len(rows) - len(seen),
                "weak": weak,
                "coverage": round(len(seen) / len(rows), 4) if rows else 0,
            }
        )

    observed = [c["mastery"] for row in rows for c in row["concepts"] if c["mastery"] is not None]
    due = sum(row["dueCount"] for row in rows)
    supports = {
        category: sum(row["support"] == category for row in rows)
        for category in ("Needs support", "Monitor", "On track", "Unassessed")
    }
    groups = []
    for group in sorted({row["group"] for row in rows}):
        subset = [row for row in rows if row["group"] == group]
        group_values = [
            c["mastery"] for row in subset for c in row["concepts"] if c["mastery"] is not None
        ]
        groups.append(
            {
                "name": group,
                "learners": len(subset),
                "meanMastery": _mean(group_values),
                "dueReviews": sum(row["dueCount"] for row in subset),
                "needsSupport": sum(row["support"] == "Needs support" for row in subset),
            }
        )
    bottlenecks = sorted(
        (c for c in concepts if c["observed"] > 0),
        key=lambda c: (c["mean"], -c["observed"], c["name"]),
    )
    return {
        "generatedAt": now.isoformat(),
        "sample": bool(metadata.get("synthetic", False)),
        "datasetLabel": str(metadata.get("label", "Local learning workspace")),
        "methodology": {
            "mastery": "Original SkillGraph 0–1 heuristic mastery estimates, not calibrated probabilities.",
            "due": "Only explicitly scheduled reviews with dueAt <= snapshot time count as due.",
            "support": "Needs support: 3+ due reviews or any observed mastery < 0.40; "
            "Monitor: any due review or 2+ observed masteries < 0.60; "
            "otherwise On track. Unassessed when there are no observations.",
            "missing": "Unattempted concepts are shown as missing and omitted from mastery averages.",
            "demo": "All sample learners and outcomes are synthetic demonstrations.",
        },
        "metrics": {
            "learners": len(rows),
            "concepts": len(names),
            "meanMastery": _mean(observed),
            "observations": len(observed),
            "possibleObservations": len(rows) * len(names),
            "dueReviews": due,
            "needsSupport": supports["Needs support"],
            "supportBands": supports,
        },
        "concepts": concepts,
        "students": rows,
        "groups": groups,
        "bottlenecks": bottlenecks,
    }


def _cell_for_spreadsheet(value: object) -> str:
    """Neutralize formula injection when exported CSV is opened in a spreadsheet."""
    raw = str(value if value is not None else "")
    if raw.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + raw
    return raw


def cohort_csv(snapshot: dict) -> str:
    output = io.StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(
        [
            "Learner ID",
            "Learner",
            "Group",
            "Concept",
            "Mastery estimate",
            "Status",
            "Review due (UTC)",
            "Support band",
            "Data source",
        ]
    )
    label = "Synthetic demonstration" if snapshot["sample"] else "Local workspace"
    for student in snapshot["students"]:
        for item in student["concepts"]:
            writer.writerow(
                [
                    _cell_for_spreadsheet(student["id"]),
                    _cell_for_spreadsheet(student["name"]),
                    _cell_for_spreadsheet(student["group"]),
                    _cell_for_spreadsheet(item["concept"]),
                    "" if item["mastery"] is None else item["mastery"],
                    item["status"],
                    item["dueAt"] or "",
                    student["support"],
                    label,
                ]
            )
    return output.getvalue()
