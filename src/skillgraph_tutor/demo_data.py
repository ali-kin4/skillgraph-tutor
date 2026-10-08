"""Reproducible fictional cohort for offline product demonstrations only."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .graph import parse_syllabus_markdown
from .student import StudentState, save_student

NAMES = [
    ("learner-01", "Amelia Chen", "Data & Analytics"),
    ("learner-02", "Noah Patel", "Data & Analytics"),
    ("learner-03", "Isla Morgan", "Data & Analytics"),
    ("learner-04", "Lucas Bennett", "Data & Analytics"),
    ("learner-05", "Mia Rivera", "Data & Analytics"),
    ("learner-06", "Ethan Walsh", "Engineering"),
    ("learner-07", "Ava Thompson", "Engineering"),
    ("learner-08", "Liam Brooks", "Engineering"),
    ("learner-09", "Sofia Reed", "Engineering"),
    ("learner-10", "Oliver Hayes", "Engineering"),
    ("learner-11", "Grace Kim", "Operations"),
    ("learner-12", "Leo Martin", "Operations"),
    ("learner-13", "Ella Cooper", "Operations"),
    ("learner-14", "James Walker", "Operations"),
    ("learner-15", "Zoe Parker", "Operations"),
    ("learner-16", "Aria Scott", "Operations"),
]


def create_demo_workspace(root: str | Path, now: datetime | None = None) -> Path:
    """Populate an isolated workspace without overwriting existing learner records."""
    root = Path(root)
    now = now or datetime.now(timezone.utc)
    source = Path(__file__).parents[2] / "demo" / "corporate_python_syllabus.md"
    if not source.is_file():
        # Wheel installs include the built-in syllabus under package data.
        source = Path(__file__).with_name("demo_syllabus.md")
    graph = parse_syllabus_markdown(source.read_text(encoding="utf-8"))
    graph_path = root / "graph.json"
    student_dir = root / "students"
    if graph_path.exists() or (student_dir.exists() and any(student_dir.iterdir())):
        raise FileExistsError(
            "Demo target already contains data. Choose a new --workspace to avoid overwriting."
        )
    student_dir.mkdir(parents=True, exist_ok=True)
    graph.save_json(graph_path)
    rng = random.Random(4206)
    concepts = list(graph.nodes)
    group_map = {}
    for i, (student_id, name, group) in enumerate(NAMES):
        student = StudentState(student_id=student_id, name=name)
        group_map[student_id] = group
        completed = len(concepts) - ((i * 3 + 1) % 5)
        for j, topic in enumerate(concepts[:completed]):
            value = min(0.97, max(0.18, 0.81 - i * 0.024 - j * 0.028 + rng.uniform(-0.14, 0.14)))
            state = student.concept(topic)
            state.mastery = round(value, 4)
            state.updated_at = (now - timedelta(days=(i + j) % 13)).isoformat()
            state.reviews.repetitions = 1 + (i + j) % 4
            state.reviews.interval_days = 3 + (i + j) % 7
            state.reviews.due_at = (
                now + timedelta(days=((i + j * 2) % 12) - 7)
            ).isoformat()
        save_student(student_dir / (student_id + ".json"), student)
    (root / "cohort_metadata.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "label": "Applied Python · Demo Cohort",
                "description": "Fictional learners and simulated mastery estimates",
                "groups": group_map,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return root
