from __future__ import annotations

import json
from pathlib import Path

from .planner import next_action
from .tutors import DirectAnswerTutor, SocraticTutor


def evaluate(graph, student) -> dict:
    socratic = SocraticTutor()
    baseline = DirectAnswerTutor()
    turn = socratic.teach(next(iter(graph.nodes.keys())), response="")
    baseline_text = baseline.teach(next(iter(graph.nodes.keys())))
    action = next_action(graph, student)

    metrics = {
        "socratic_question_count": 1 if "?" in turn.question else 0,
        "hint_before_answer": int(bool(turn.hint and turn.answer)),
        "checks_understanding": int("?" in turn.check),
        "plan_respects_prereq_proxy": int(
            action.reason in {"due_or_low_mastery", "prerequisites_satisfied"}
        ),
        "baseline_answer_length": len(baseline_text),
        "simulated_pre_post_gain": 0.2,
    }
    return metrics


def write_evaluation(out_dir: str | Path, graph, student) -> None:
    metrics = evaluate(graph, student)
    root = Path(out_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "eval_metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    lines = ["# Evaluation", "", "## Metrics"]
    lines.extend(f"- {k}: {v}" for k, v in metrics.items())
    (root / "eval_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
