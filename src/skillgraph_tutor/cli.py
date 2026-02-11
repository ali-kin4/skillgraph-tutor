from __future__ import annotations

import shutil
from pathlib import Path

from .compat import typer
from .config import SkillGraphConfig
from .eval_harness import write_evaluation
from .graph import load_graph, parse_syllabus_markdown
from .logging_utils import log_trace
from .planner import build_review_queue, next_action, seven_day_plan
from .reporting import write_report
from .scheduler import sm2_update
from .student import StudentState, load_student, save_student
from .tutors import SocraticTutor

app = typer.Typer(help="SkillGraph Tutor CLI")


def _workspace(config: SkillGraphConfig) -> Path:
    root = Path(config.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    (root / "students").mkdir(parents=True, exist_ok=True)
    return root


def _student_path(config: SkillGraphConfig, student_id: str) -> Path:
    return _workspace(config) / "students" / f"{student_id}.json"


def _graph_path(config: SkillGraphConfig) -> Path:
    return _workspace(config) / "graph.json"


def _fail(message: str) -> None:
    typer.echo(f"Error: {message}")
    raise SystemExit(1)


def _require_student(config: SkillGraphConfig, student_id: str) -> StudentState:
    path = _student_path(config, student_id)
    try:
        return load_student(path)
    except FileNotFoundError:
        _fail(
            f"Student with ID '{student_id}' not found. Run 'skillgraph add-student {student_id}'."
        )


def _require_graph(config: SkillGraphConfig):
    path = _graph_path(config)
    try:
        return load_graph(path)
    except FileNotFoundError:
        _fail("Concept graph not initialized. Run 'skillgraph init <syllabus.md>' first.")


@app.command("init")
def init_cmd(syllabus: str, config_path: str | None = typer.Option(None, "--config")) -> None:
    cfg = SkillGraphConfig.load(config_path)
    text = Path(syllabus).read_text(encoding="utf-8")
    graph = parse_syllabus_markdown(text)
    graph.save_json(_graph_path(cfg))
    typer.echo(f"Initialized graph with {len(graph.nodes)} concepts.")


@app.command("add-student")
def add_student(
    student_id: str, name: str = typer.Option(..., "--name"), config_path: str | None = None
) -> None:
    cfg = SkillGraphConfig.load(config_path)
    student = StudentState(
        student_id=student_id,
        name=name,
        forgetting_lambda=cfg.forgetting.lambda_default,
        mastery_learning_rate=cfg.policy.mastery_learning_rate,
    )
    save_student(_student_path(cfg, student_id), student)
    typer.echo(f"Added student {student_id}.")


@app.command("study")
def study(student_id: str, concept: str, config_path: str | None = None) -> None:
    cfg = SkillGraphConfig.load(config_path)
    student = _require_student(cfg, student_id)
    tutor = SocraticTutor()
    turn = tutor.teach(concept, response="")
    student.concept(concept)
    save_student(_student_path(cfg, student_id), student)
    typer.echo(turn.question)
    typer.echo(f"Hint: {turn.hint}")


@app.command("quiz")
def quiz(
    student_id: str,
    concept: str,
    correct: bool = typer.Option(..., "--correct"),
    confidence: float = typer.Option(0.7, "--confidence"),
    config_path: str | None = None,
) -> None:
    cfg = SkillGraphConfig.load(config_path)
    student = _require_student(cfg, student_id)
    before = student.concept(concept).mastery
    after = student.update_mastery(concept, correct=correct, confidence=confidence)
    quality = 4 if correct else 2
    sm2_update(student.concept(concept), quality=quality, config=cfg.spaced_repetition)
    save_student(_student_path(cfg, student_id), student)
    log_trace(
        cfg.logging.trace_path,
        {
            "student_id": student_id,
            "concept": concept,
            "chosen_action": "quiz",
            "tutor_type": "socratic",
            "mastery_before": before,
            "mastery_after": after,
            "due_count": len(build_review_queue(student)),
            "quiz_score": int(correct),
        },
    )
    typer.echo(f"Updated mastery {before:.2f} -> {after:.2f}")


@app.command("review")
def review(student_id: str, config_path: str | None = None) -> None:
    cfg = SkillGraphConfig.load(config_path)
    student = _require_student(cfg, student_id)
    queue = build_review_queue(student, low_mastery_threshold=cfg.policy.review_mastery_threshold)
    if not queue:
        typer.echo("No due reviews.")
        return
    for concept in queue:
        sm2_update(student.concept(concept), quality=4, config=cfg.spaced_repetition)
        typer.echo(f"Reviewed {concept}")
    save_student(_student_path(cfg, student_id), student)


@app.command("plan")
def plan(
    student_id: str, horizon: str = typer.Option("7d", "--horizon"), config_path: str | None = None
) -> None:
    cfg = SkillGraphConfig.load(config_path)
    graph = _require_graph(cfg)
    student = _require_student(cfg, student_id)
    actions = seven_day_plan(graph, student) if horizon == "7d" else [next_action(graph, student)]
    for item in actions:
        typer.echo(f"{item.action}: {item.concept} ({item.reason})")


@app.command("report")
def report(
    student_id: str, out: str = typer.Option(..., "--out"), config_path: str | None = None
) -> None:
    cfg = SkillGraphConfig.load(config_path)
    graph = _require_graph(cfg)
    student = _require_student(cfg, student_id)
    write_report(out, student, graph)
    write_evaluation(out, graph, student)
    typer.echo(f"Report written to {out}")


@app.command("doctor")
def doctor(config_path: str | None = typer.Option(None, "--config")) -> None:
    cfg = SkillGraphConfig.load(config_path)
    ws_path = Path(cfg.data_dir)
    workspace_writable = False
    try:
        ws_path.mkdir(exist_ok=True, parents=True)
        check_file = ws_path / ".writable_check"
        check_file.write_text("ok", encoding="utf-8")
        check_file.unlink()
        workspace_writable = True
    except OSError:
        workspace_writable = False

    checks = {
        "python": True,
        "workspace_writable": workspace_writable,
        "sample_data": Path("data/sample_syllabus.md").exists(),
    }
    for name, ok in checks.items():
        typer.echo(f"{name}: {'ok' if ok else 'missing'}")


@app.command("demo")
def demo() -> None:
    cfg = SkillGraphConfig.load(None)
    ws = _workspace(cfg)
    syllabus = Path("data/sample_syllabus.md")
    init_cmd(str(syllabus), None)
    sid = "demo-student"
    add_student(sid, name="Demo Student", config_path=None)
    study(sid, "Variables", config_path=None)
    quiz(sid, "Variables", correct=True, confidence=0.9, config_path=None)
    review(sid, config_path=None)
    report_dir = Path("reports") / sid
    if report_dir.exists():
        shutil.rmtree(report_dir)
    report(sid, out=str(report_dir), config_path=None)
    typer.echo(f"Demo complete. Workspace: {ws}")


if __name__ == "__main__":
    app()
