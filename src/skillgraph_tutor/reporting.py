from __future__ import annotations

import json
from pathlib import Path

from .graph import ConceptGraph
from .planner import seven_day_plan
from .student import StudentState


def render_report(student: StudentState, graph: ConceptGraph) -> tuple[str, dict]:
    due = [name for name, concept in student.concepts.items() if concept.reviews.due_at is None]
    plan = seven_day_plan(graph, student)
    plan_rows = [
        {"day": i + 1, "action": item.action, "concept": item.concept}
        for i, item in enumerate(plan)
    ]

    mastery_rows = [
        {"concept": name, "mastery": round(concept.mastery, 3), "due_at": concept.reviews.due_at}
        for name, concept in sorted(student.concepts.items())
    ]

    md = [
        f"# Progress Report: {student.name} ({student.student_id})",
        "",
        "## Mastery",
        "| Concept | Mastery | Due |",
        "|---|---:|---|",
    ]
    md.extend(
        f"| {row['concept']} | {row['mastery']} | {row['due_at'] or 'due-now'} |"
        for row in mastery_rows
    )
    due_lines = [f"- {item}" for item in due] if due else ["- None"]
    md.extend(["", "## Due Reviews", *due_lines])
    md.extend(["", "## Next 7-Day Plan"])
    md.extend(f"- Day {r['day']}: {r['action']} {r['concept']}" for r in plan_rows)
    md.extend(["", "## Skill Graph (Mermaid)", "```mermaid", graph.to_mermaid(), "```", ""])

    payload = {"student": student.to_dict(), "due_reviews": due, "plan": plan_rows}
    return "\n".join(md), payload


def write_report(out_dir: str | Path, student: StudentState, graph: ConceptGraph) -> None:
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    md, payload = render_report(student, graph)
    (root / "report.md").write_text(md, encoding="utf-8")
    (root / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
