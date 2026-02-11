from skillgraph_tutor.config import SpacedRepetitionConfig
from skillgraph_tutor.scheduler import sm2_update
from skillgraph_tutor.student import ConceptState


def test_sm2_progression():
    c = ConceptState()
    sm2_update(c, quality=4)
    assert c.reviews.interval_days == 1
    sm2_update(c, quality=4)
    assert c.reviews.interval_days == 6


def test_sm2_uses_configurable_initial_interval():
    c = ConceptState()
    cfg = SpacedRepetitionConfig(initial_interval_days=2, easy_bonus=1.5)
    sm2_update(c, quality=5, config=cfg)
    assert c.reviews.interval_days >= 2
