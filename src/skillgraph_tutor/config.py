from __future__ import annotations

from pathlib import Path

from .compat import BaseModel, Field

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


class ModelConfig(BaseModel):
    provider: str = Field(default="mock", description="mock|openai")
    model_name: str = "mock-socratic-v1"


class ForgettingConfig(BaseModel):
    lambda_default: float = 0.02


class SpacedRepetitionConfig(BaseModel):
    initial_interval_days: int = 1
    easy_bonus: float = 1.3
    min_ease: float = 1.3
    start_ease: float = 2.5


class PolicyConfig(BaseModel):
    review_mastery_threshold: float = 0.6
    new_concept_mastery_cap: float = 0.75
    mastery_learning_rate: float = 0.18


class LoggingConfig(BaseModel):
    trace_path: str = "artifacts/traces.jsonl"


class SkillGraphConfig(BaseModel):
    seed: int = 42
    data_dir: str = "workspace"
    models: ModelConfig = ModelConfig()
    forgetting: ForgettingConfig = ForgettingConfig()
    spaced_repetition: SpacedRepetitionConfig = SpacedRepetitionConfig()
    policy: PolicyConfig = PolicyConfig()
    logging: LoggingConfig = LoggingConfig()

    @classmethod
    def load(cls, path: str | Path | None = None) -> SkillGraphConfig:
        if path is None:
            return cls()
        raw = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)
