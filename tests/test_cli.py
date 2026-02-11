from skillgraph_tutor.cli import app
from skillgraph_tutor.compat import CliRunner


def test_cli_doctor_smoke():
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "python: ok" in result.stdout
    assert "workspace_writable: ok" in result.stdout
