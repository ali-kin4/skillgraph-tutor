from datetime import datetime, timedelta, timezone

from skillgraph_tutor.student import StudentState


def test_forgetting_and_update():
    s = StudentState(student_id="s1", name="Ada", forgetting_lambda=0.1)
    now = datetime.now(timezone.utc)
    s.concept("A").mastery = 0.8
    s.concept("A").updated_at = (now - timedelta(days=5)).isoformat()
    decayed = s.apply_forgetting("A", now=now)
    assert decayed < 0.8
    updated = s.update_mastery("A", correct=True, confidence=1.0, now=now)
    assert updated >= decayed


def test_from_dict_uses_dataclass_defaults_when_fields_missing():
    student = StudentState.from_dict({"student_id": "s1", "name": "Ada", "concepts": {"A": {}}})
    assert student.forgetting_lambda == StudentState.forgetting_lambda
    assert student.mastery_learning_rate == StudentState.mastery_learning_rate
    assert student.concepts["A"].mastery == 0.2
