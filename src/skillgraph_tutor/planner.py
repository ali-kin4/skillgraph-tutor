from __future__ import annotations

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from .graph import ConceptGraph
from .scheduler import is_due
from .student import StudentState


@dataclass
class PlannedAction:
    action: str
    concept: str
    reason: str


def _eligible_new_concepts(
    graph: ConceptGraph, student: StudentState, threshold: float
) -> list[str]:
    eligible: list[str] = []
    for name, node in graph.nodes.items():
        if name in student.concepts:
            continue
        prereq_ok = all(
            student.concepts.get(req, None) and student.concepts[req].mastery >= threshold
            for req in node.requires
        )
        if prereq_ok:
            eligible.append(name)
    return eligible


def build_review_queue(student: StudentState, low_mastery_threshold: float = 0.6) -> list[str]:
    queue: list[str] = []
    for name, concept in student.concepts.items():
        if is_due(concept) or concept.mastery < low_mastery_threshold:
            queue.append(name)
    queue.sort(key=lambda n: student.concepts[n].mastery)
    return queue


def next_action(
    graph: ConceptGraph, student: StudentState, mastery_threshold: float = 0.7
) -> PlannedAction:
    queue = build_review_queue(student)
    if queue:
        concept = queue[0]
        return PlannedAction(action="review", concept=concept, reason="due_or_low_mastery")

    eligible = _eligible_new_concepts(graph, student, mastery_threshold)
    if eligible:
        return PlannedAction(action="learn", concept=eligible[0], reason="prerequisites_satisfied")

    fallback = sorted(graph.nodes.keys())[0]
    return PlannedAction(action="review", concept=fallback, reason="no_eligible_new_concepts")


def seven_day_plan(graph: ConceptGraph, student: StudentState) -> list[PlannedAction]:
    actions: list[PlannedAction] = []
    simulated_student = copy.deepcopy(student)
    simulated_now = datetime.now(timezone.utc)
    for day in range(7):
        action = next_action(graph, simulated_student)
        actions.append(action)
        if action.concept not in simulated_student.concepts:
            simulated_student.concept(action.concept).mastery = 0.3
        simulated_student.apply_forgetting(
            action.concept, now=simulated_now + timedelta(days=day + 1)
        )
    return actions
