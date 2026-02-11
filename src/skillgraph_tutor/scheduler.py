from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .student import ConceptState


def _now() -> datetime:
    return datetime.now(timezone.utc)


def sm2_update(concept: ConceptState, quality: int, now: datetime | None = None) -> ConceptState:
    now = now or _now()
    quality = max(0, min(5, quality))
    review = concept.reviews

    if quality < 3:
        review.repetitions = 0
        review.interval_days = 1
    else:
        if review.repetitions == 0:
            review.interval_days = 1
        elif review.repetitions == 1:
            review.interval_days = 6
        else:
            review.interval_days = max(1, round(review.interval_days * review.ease_factor))
        review.repetitions += 1

    review.ease_factor = max(
        1.3, review.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
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
