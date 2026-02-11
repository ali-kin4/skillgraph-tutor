from skillgraph_tutor.graph import parse_syllabus_markdown
from skillgraph_tutor.planner import next_action, seven_day_plan
from skillgraph_tutor.student import StudentState


def test_planner_respects_prerequisites():
    g = parse_syllabus_markdown("## A\n## B\nrequires: A")
    s = StudentState(student_id="s1", name="Ada")
    action = next_action(g, s)
    assert action.concept == "A"


def test_seven_day_plan_no_mutation_side_effect():
    g = parse_syllabus_markdown("## A\n## B\nrequires: A")
    s = StudentState(student_id="s1", name="Ada")
    before = s.to_dict()
    plan = seven_day_plan(g, s)
    assert len(plan) == 7
    assert s.to_dict() == before
