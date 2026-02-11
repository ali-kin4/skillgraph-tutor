from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .config import SpacedRepetitionConfig
from .student import ConceptState


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sm2_update(
    concept: ConceptState,
    quality: int,
    config: SpacedRepetitionConfig | None = None,
    now: datetime | None = None,
) -> ConceptState:
    cfg = config or SpacedRepetitionConfig()
    now = now or _now()
    quality = max(0, min(5, quality))
    review = concept.reviews

    if quality < 3:
        review.repetitions = 0
        review.interval_days = cfg.initial_interval_days
    else:
        if review.repetitions == 0:
            review.interval_days = cfg.initial_interval_days
        elif review.repetitions == 1:
            review.interval_days = max(2, round(cfg.initial_interval_days * 6))
        else:
            review.interval_days = max(1, round(review.interval_days * review.ease_factor))
        review.repetitions += 1

    review.ease_factor = max(
        cfg.min_ease,
        review.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)),
    )
    if quality == 5:
        review.interval_days = max(
            review.interval_days, round(review.interval_days * cfg.easy_bonus)
        )

    review.due_at = (now + timedelta(days=review.interval_days)).isoformat()
    concept.updated_at = now.isoformat()
    return concept


def is_due(concept: ConceptState, now: datetime | None = None) -> bool:
    now = now or _now()
    due_at = concept.reviews.due_at
    if due_at is None:
        return True
    return datetime.fromisoformat(due_at) <= now
