from pathlib import Path

from skillgraph_tutor.cli import app
from skillgraph_tutor.compat import CliRunner
from skillgraph_tutor.student import load_student


def test_cli_doctor_smoke():
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "python: ok" in result.stdout
    assert "workspace_writable: ok" in result.stdout


def test_study_unknown_student_is_user_friendly_error():
    runner = CliRunner()
    result = runner.invoke(app, ["study", "missing-student", "Variables"])
    assert result.exit_code == 1
    assert "Student with ID 'missing-student' not found" in result.stdout


def test_quiz_records_correct_and_incorrect_outcomes(tmp_path, monkeypatch):
    syllabus = Path(__file__).resolve().parents[1] / "data" / "sample_syllabus.md"
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()
    assert runner.invoke(app, ["init", str(syllabus)]).exit_code == 0
    assert runner.invoke(app, ["add-student", "s1", "--name", "Ada"]).exit_code == 0
    up = runner.invoke(app, ["quiz", "s1", "Variables", "--correct", "--confidence", "1.0"])
    assert up.exit_code == 0, up.stdout
    down = runner.invoke(app, ["quiz", "s1", "Variables", "--no-correct", "--confidence", "1.0"])
    assert down.exit_code == 0, down.stdout
    history = load_student(tmp_path / "workspace" / "students" / "s1.json").concepts["Variables"]
    assert len(history.history) == 2
    assert history.history[1][1] < history.history[0][1]
