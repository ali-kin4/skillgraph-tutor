from __future__ import annotations

import contextlib
import io
from types import SimpleNamespace


class CliRunner:
    def invoke(self, app, args: list[str]):
        buffer = io.StringIO()
        code = 0
        with contextlib.redirect_stdout(buffer):
            try:
                code = app._run(args)
            except SystemExit as exc:
                code = int(exc.code)
        return SimpleNamespace(exit_code=code, stdout=buffer.getvalue())
