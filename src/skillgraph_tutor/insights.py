"""Growth trajectories, scenario projections and rule-based insights.

Projections replay each learner's own forgetting and learning-rate parameters under two
stated assumptions. They illustrate what the mastery model implies; they are not
predictions of attainment. Insights are deterministic rules over observed data.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .analytics import mean_or_none, parse_utc
from .graph import ConceptGraph
from .student import ConceptState, StudentState

WEEK = timedelta(days=7)
PRACTICE_CONFIDENCE = 0.7
GROWTH_WINDOW_DAYS = 28
HISTORY_WINDOW_WEEKS = 12
MIN_GROWTH_SAMPLE = 3


def select_learners(
    students: list[StudentState], metadata: dict | None, scope: str
) -> list[StudentState]:
    """Resolve ``cohort``, ``group:<name>`` or ``learner:<id>`` to a list of learners."""
    groups = (metadata or {}).get("groups", {})
    if not isinstance(groups, dict):
        groups = {}
    if scope == "cohort":
        return list(students)
    kind, _, value = scope.partition(":")
    if kind == "group" and value:
        chosen = [s for s in students if str(groups.get(s.student_id, "Unassigned")) == value]
    elif kind == "learner" and value:
        chosen = [s for s in students if s.student_id == value]
    else:
        raise ValueError("Scope must be 'cohort', 'group:<name>' or 'learner:<id>'.")
    if not chosen:
        raise LookupError("No learners match this scope.")
    return chosen


def _value_at(state: ConceptState, when: datetime) -> float | None:
    """Most recent recorded estimate at or before ``when``; None if not yet observed."""
    points = [*state.history, (state.updated_at, state.mastery)]
    best: tuple[datetime, float] | None = None
    for raw_at, value in points:
        at = parse_utc(raw_at)
        if at is None or at > when or not math.isfinite(value):
            continue
        if best is None or at >= best[0]:
            best = (at, value)
    return None if best is None else max(0.0, min(1.0, best[1]))


def _observed_pairs(graph: ConceptGraph, students: list[StudentState]):
    for student in students:
        for name in graph.nodes:
            state = student.concepts.get(name)
            if state is not None:
                yield student, name, state


def trajectory(
    graph: ConceptGraph,
    students: list[StudentState],
    now: datetime,
    weeks_back: int = HISTORY_WINDOW_WEEKS,
    weeks_ahead: int = 8,
) -> dict:
    """Weekly mean mastery history plus two scenario projections from ``now``."""
    pairs = list(_observed_pairs(graph, students))
    history = []
    for k in range(weeks_back, -1, -1):
        when = now - k * WEEK
        values = [v for _, _, s in pairs if (v := _value_at(s, when)) is not None]
        history.append(
            {"date": when.isoformat(), "mean": mean_or_none(values), "observed": len(values)}
        )

    practice: list[list[float]] = [[] for _ in range(weeks_ahead)]
    idle: list[list[float]] = [[] for _ in range(weeks_ahead)]
    for student, _, state in pairs:
        start = _value_at(state, now)
        if start is None:
            continue
        weekly_decay = math.exp(-student.forgetting_lambda * 7)
        gain = student.mastery_learning_rate * PRACTICE_CONFIDENCE
        practiced = start
        for week in range(weeks_ahead):
            practiced = min(1.0, practiced * weekly_decay + gain)
            practice[week].append(practiced)
            idle[week].append(start * weekly_decay ** (week + 1))

    def series(buckets: list[list[float]]) -> list[dict]:
        anchor = history[-1]
        points = [{"date": anchor["date"], "mean": anchor["mean"]}]
        for week, values in enumerate(buckets, start=1):
            points.append({"date": (now + week * WEEK).isoformat(), "mean": mean_or_none(values)})
        return points

    return {
        "history": history,
        "practice": series(practice),
        "noPractice": series(idle),
        "assumptions": {
            "practice": "One successful review per observed concept each week at confidence "
            f"{PRACTICE_CONFIDENCE}, applied with each learner's learning rate and forgetting.",
            "noPractice": "No further practice; estimates decay at each learner's forgetting rate.",
            "history": "Weekly mean of the most recent recorded estimate per learner-concept pair.",
            "disclaimer": "Scenario projections from the heuristic model, not predictions.",
        },
    }


def concept_growth(
    graph: ConceptGraph,
    students: list[StudentState],
    now: datetime,
    window_days: int = GROWTH_WINDOW_DAYS,
) -> list[dict]:
    """Mean change per concept over the window, among learners observed at both ends."""
    start = now - timedelta(days=window_days)
    rows = []
    for name in graph.nodes:
        deltas = []
        for student in students:
            state = student.concepts.get(name)
            if state is None:
                continue
            before, after = _value_at(state, start), _value_at(state, now)
            if before is not None and after is not None:
                deltas.append(after - before)
        rows.append({"name": name, "delta": mean_or_none(deltas), "learners": len(deltas)})
    return rows


def _pct(value: float) -> int:
    return round(value * 100)


def build_insights(snapshot: dict, growth: list[dict], projection: dict) -> list[dict]:
    """Deterministic, evidence-backed observations. Each insight names its concepts."""
    insights = []
    rising = sorted(
        (g for g in growth if g["delta"] is not None and g["delta"] > 0.005),
        key=lambda g: (-g["delta"], g["name"]),
    )
    rising = [
        g for g in rising if g["learners"] >= min(MIN_GROWTH_SAMPLE, len(snapshot["students"]))
    ]
    if rising:
        top = rising[:2]
        names = " and ".join(g["name"] for g in top)
        gains = " and ".join(f"+{_pct(g['delta'])} pts" for g in top)
        insights.append(
            {
                "kind": "growth",
                "title": "Fastest-growing skills",
                "text": f"Learners strengthened {names} the most over the last "
                f"{GROWTH_WINDOW_DAYS // 7} weeks ({gains} on average).",
                "concepts": [g["name"] for g in top],
            }
        )

    if snapshot["bottlenecks"]:
        weakest = snapshot["bottlenecks"][0]
        means = {c["name"]: c["mean"] for c in snapshot["concepts"]}
        text = (
            f"{weakest['name']} has the lowest observed mastery ({_pct(weakest['mean'])}%), "
            f"with {weakest['weak']} of {weakest['observed']} learners below 60%."
        )
        concepts = [weakest["name"]]
        shaky = sorted(
            (r for r in weakest["requires"] if means.get(r) is not None and means[r] < 0.7),
            key=lambda r: means[r],
        )
        if shaky:
            prereq = shaky[0]
            text += (
                f" Its prerequisite {prereq} averages {_pct(means[prereq])}%; reinforce it first."
            )
            concepts.append(shaky[0])
        insights.append(
            {
                "kind": "bottleneck",
                "title": "Biggest bottleneck",
                "text": text,
                "concepts": concepts,
            }
        )

    practiced, idle = projection["practice"][-1]["mean"], projection["noPractice"][-1]["mean"]
    if practiced is not None and idle is not None:
        weeks = len(projection["practice"]) - 1
        insights.append(
            {
                "kind": "projection",
                "title": "Practice keeps gains",
                "text": f"With weekly practice, mean mastery is projected at {_pct(practiced)}% "
                f"in {weeks} weeks, versus {_pct(idle)}% without practice (model scenario).",
                "concepts": [],
            }
        )

    due_learners = [s for s in snapshot["students"] if s["dueCount"]]
    if due_learners:
        busiest = max(snapshot["groups"], key=lambda g: (g["dueReviews"], g["name"]))
        text = (
            f"{snapshot['metrics']['dueReviews']} scheduled reviews are due across "
            f"{len(due_learners)} learners."
        )
        if len(snapshot["groups"]) > 1:
            text += f" {busiest['name']} has the most ({busiest['dueReviews']})."
        insights.append(
            {"kind": "reviews", "title": "Reviews waiting", "text": text, "concepts": []}
        )
    return insights
