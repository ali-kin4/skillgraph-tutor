from skillgraph_tutor.scheduler import sm2_update
from skillgraph_tutor.student import ConceptState


def test_sm2_progression():
    c = ConceptState()
    sm2_update(c, quality=4)
    assert c.reviews.interval_days == 1
    sm2_update(c, quality=4)
    assert c.reviews.interval_days == 6
