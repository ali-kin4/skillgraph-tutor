from skillgraph_tutor.cli import app
from skillgraph_tutor.compat import CliRunner


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
