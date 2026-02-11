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
