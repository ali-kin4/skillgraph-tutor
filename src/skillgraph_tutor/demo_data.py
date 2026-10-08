"""Reproducible fictional cohort for offline product demonstrations only."""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .graph import parse_syllabus_markdown
from .student import StudentState, save_student

WEEK = timedelta(days=7)

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
    source = Path(__file__).with_name("demo_syllabus.md")
    graph = parse_syllabus_markdown(source.read_text(encoding="utf-8"))
    graph_path = root / "graph.json"
    student_dir = root / "students"
    existing_metadata = root / "cohort_metadata.json"
    if graph_path.exists() and existing_metadata.is_file():
        existing = json.loads(existing_metadata.read_text(encoding="utf-8"))
        if existing.get("synthetic") is True:
            return root
    if graph_path.exists() or (student_dir.exists() and any(student_dir.iterdir())):
        raise FileExistsError(
            "Demo target already contains data. Choose a new --workspace to avoid overwriting."
        )
    student_dir.mkdir(parents=True, exist_ok=True)
    graph.save_json(graph_path)
    rng = random.Random(4206)
    # Separate stream so adding history never changes the seeded mastery values.
    history_rng = random.Random(9013)
    concepts = list(graph.nodes)
    group_map = {}
    for i, (student_id, name, group) in enumerate(NAMES):
        student = StudentState(student_id=student_id, name=name)
        group_map[student_id] = group
        completed = len(concepts) - ((i * 3 + 1) % 5)
        for j, topic in enumerate(concepts[:completed]):
            # Distinct simulated learner bands illustrate action prioritization.
            if i < 5:
                base, decline, jitter = 0.88, 0.018, 0.035
                due_offset = 3 + (i + j) % 7
            elif i < 10:
                base, decline, jitter = 0.74, 0.022, 0.045
                due_offset = -1 if j == 0 or (i % 2 == 0 and j == 1) else 2 + (i + j) % 9
            else:
                base, decline, jitter = 0.60, 0.032, 0.04
                due_offset = -(1 + j % 5) if j < 4 else 3 + (i + j) % 7
            value = min(0.97, max(0.18, base - j * decline + rng.uniform(-jitter, jitter)))
            state = student.concept(topic)
            state.mastery = round(value, 4)
            state.updated_at = (now - timedelta(days=(i + j) % 13)).isoformat()
            state.reviews.repetitions = 1 + (i + j) % 4
            state.reviews.interval_days = 3 + (i + j) % 7
            state.reviews.due_at = (now + timedelta(days=due_offset)).isoformat()
            state.history = _simulated_history(history_rng, state.updated_at, state.mastery, j)
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


def _simulated_history(
    rng: random.Random, updated_at: str, final: float, order: int
) -> list[tuple[str, float]]:
    """Weekly estimates rising to ``final``; later curriculum concepts start later."""
    end = datetime.fromisoformat(updated_at)
    weeks = max(2, 12 - order)
    start = max(0.12, final - rng.uniform(0.2, 0.42))
    points = []
    for week in range(weeks, 0, -1):
        progress = (weeks - week) / weeks
        value = start + (final - start) * progress + rng.uniform(-0.02, 0.02)
        points.append(((end - week * WEEK).isoformat(), round(min(0.97, max(0.1, value)), 4)))
    points.append((updated_at, final))
    return points
