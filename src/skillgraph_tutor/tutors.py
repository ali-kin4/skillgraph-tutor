from __future__ import annotations

from dataclasses import dataclass


class BaseLLM:
    def generate(self, prompt: str) -> str:
        raise NotImplementedError


class MockLLM(BaseLLM):
    def generate(self, prompt: str) -> str:
        return f"[mock-llm] {prompt[:180]}"


@dataclass
class TutorTurn:
    question: str
    hint: str
    check: str
    answer: str
    summary: str
    micro_actions: list[str]


class SocraticTutor:
    def __init__(self, llm: BaseLLM | None = None):
        self.llm = llm or MockLLM()

    def teach(self, concept: str, response: str, difficulty: int = 1) -> TutorTurn:
        q = f"What is one key idea behind '{concept}'? (difficulty {difficulty})"
        hint = f"Hint: connect {concept} to one concrete example and one prerequisite."
        check = "Can you restate your answer in your own words with a quick test case?"
        answer = f"A strong answer links definition, mechanism, and example for {concept}."
        summary = f"You practiced {concept} using explanation + example framing."
        micro_actions = [
            f"Write a 2-sentence definition of {concept}.",
            f"Solve one mini problem about {concept}.",
            f"Teach {concept} aloud for 60 seconds.",
        ]
        if response.strip():
            q = f"Nice attempt. What part of '{concept}' still feels uncertain?"
        return TutorTurn(q, hint, check, answer, summary, micro_actions)


class DirectAnswerTutor:
    def teach(self, concept: str) -> str:
        return f"Direct answer: {concept} is explained with definition, formula, and example."
