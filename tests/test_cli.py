from skillgraph_tutor.cli import app
from typer.testing import CliRunner


def test_cli_doctor_smoke():
    runner = CliRunner()
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert "python: ok" in result.stdout
