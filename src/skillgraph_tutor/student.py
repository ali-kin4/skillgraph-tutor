from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class ReviewState:
    repetitions: int = 0
    interval_days: int = 0
    ease_factor: float = 2.5
    due_at: str | None = None


@dataclass
class ConceptState:
    mastery: float = 0.2
    updated_at: str = field(default_factory=lambda: utc_now().isoformat())
    reviews: ReviewState = field(default_factory=ReviewState)


@dataclass
class StudentState:
    student_id: str
    name: str
    forgetting_lambda: float = 0.02
    concepts: dict[str, ConceptState] = field(default_factory=dict)

    def concept(self, name: str) -> ConceptState:
        if name not in self.concepts:
            self.concepts[name] = ConceptState()
        return self.concepts[name]

    def apply_forgetting(self, concept: str, now: datetime | None = None) -> float:
        now = now or utc_now()
        c = self.concept(concept)
        past = datetime.fromisoformat(c.updated_at)
        delta_days = max((now - past).total_seconds() / 86400, 0)
        decayed = c.mastery * math.exp(-self.forgetting_lambda * delta_days)
        c.mastery = float(max(0.0, min(1.0, decayed)))
        c.updated_at = now.isoformat()
        return c.mastery

    def update_mastery(
        self, concept: str, correct: bool, confidence: float, now: datetime | None = None
    ) -> float:
        now = now or utc_now()
        self.apply_forgetting(concept, now=now)
        c = self.concept(concept)
        signal = (1.0 if correct else -1.0) * max(0.0, min(1.0, confidence))
        c.mastery = float(max(0.0, min(1.0, c.mastery + 0.18 * signal)))
        c.updated_at = now.isoformat()
        return c.mastery

    def to_dict(self) -> dict:
        return {
            "student_id": self.student_id,
            "name": self.name,
            "forgetting_lambda": self.forgetting_lambda,
            "concepts": {
                name: {
                    "mastery": state.mastery,
                    "updated_at": state.updated_at,
                    "reviews": asdict(state.reviews),
                }
                for name, state in self.concepts.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> StudentState:
        concepts: dict[str, ConceptState] = {}
        for name, raw in data.get("concepts", {}).items():
            reviews = ReviewState(**raw.get("reviews", {}))
            concepts[name] = ConceptState(
                mastery=raw.get("mastery", 0.2),
                updated_at=raw.get("updated_at", utc_now().isoformat()),
                reviews=reviews,
            )
        return cls(
            student_id=data["student_id"],
            name=data["name"],
            forgetting_lambda=data.get("forgetting_lambda", 0.02),
            concepts=concepts,
        )


def save_student(path: str | Path, student: StudentState) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(student.to_dict(), indent=2), encoding="utf-8")


def load_student(path: str | Path) -> StudentState:
    return StudentState.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))
