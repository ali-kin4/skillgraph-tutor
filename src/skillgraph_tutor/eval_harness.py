from __future__ import annotations

import copy
import json
from pathlib import Path

from .planner import next_action
from .student import StudentState
from .tutors import DirectAnswerTutor, SocraticTutor


def _simulate_pre_post_gain(student: StudentState, concept: str) -> float:
    sim = copy.deepcopy(student)
    pre = sim.concept(concept).mastery
    post = sim.update_mastery(concept, correct=True, confidence=0.9)
    return round(post - pre, 4)


def evaluate(graph, student) -> dict:
    primary_concept = sorted(graph.nodes.keys())[0]
    socratic = SocraticTutor()
    baseline = DirectAnswerTutor()
    turn = socratic.teach(primary_concept, response="")
    baseline_text = baseline.teach(primary_concept)
    action = next_action(graph, student)

    metrics = {
        "socratic_question_count": 1 if "?" in turn.question else 0,
        "hint_before_answer": int(bool(turn.hint and turn.answer)),
        "checks_understanding": int("?" in turn.check),
        "plan_respects_prereq_proxy": int(
            action.reason in {"due_or_low_mastery", "prerequisites_satisfied"}
        ),
        "baseline_answer_length": len(baseline_text),
        "simulated_pre_post_gain": _simulate_pre_post_gain(student, primary_concept),
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
