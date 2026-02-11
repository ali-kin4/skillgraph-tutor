from datetime import datetime, timedelta, timezone

from skillgraph_tutor.graph import parse_syllabus_markdown
from skillgraph_tutor.reporting import render_report
from skillgraph_tutor.student import StudentState


def test_due_reviews_include_past_due_items():
    graph = parse_syllabus_markdown("## A")
    student = StudentState(student_id="s1", name="Ada")
    concept = student.concept("A")
    concept.reviews.due_at = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()

    md, payload = render_report(student, graph)

    assert "- A" in md
    assert payload["due_reviews"] == ["A"]
