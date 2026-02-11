from skillgraph_tutor.graph import parse_syllabus_markdown
from skillgraph_tutor.planner import next_action
from skillgraph_tutor.student import StudentState


def test_planner_respects_prerequisites():
    g = parse_syllabus_markdown("## A\n## B\nrequires: A")
    s = StudentState(student_id="s1", name="Ada")
    action = next_action(g, s)
    assert action.concept == "A"
