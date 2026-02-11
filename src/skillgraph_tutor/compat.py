from __future__ import annotations

import contextlib
import inspect
import io
from types import SimpleNamespace

try:  # pragma: no cover - exercised when deps are installed
    import typer as _typer
    from typer.testing import CliRunner as _CliRunner

    typer = _typer
    CliRunner = _CliRunner
except ModuleNotFoundError:  # pragma: no cover - offline fallback

    class _OptionInfo:
        def __init__(self, default=None, *param_decls):
            self.default = default
            self.param_decls = param_decls

    class _TyperFallback:
        class Typer:
            def __init__(self, help: str | None = None):
                self.help = help
                self._commands: dict[str, object] = {}

            def command(self, name: str):
                def decorator(func):
                    self._commands[name] = func
                    return func

                return decorator

            def _convert(self, value: str, annotation):
                if annotation is bool:
                    return value.lower() in {"1", "true", "yes", "on"}
                if annotation is int:
                    return int(value)
                if annotation is float:
                    return float(value)
                return value

            def _run(self, argv: list[str]) -> int:
                if not argv:
                    return 0
                cmd = argv[0]
                if cmd not in self._commands:
                    raise SystemExit(2)
                func = self._commands[cmd]
                sig = inspect.signature(func)
                params = list(sig.parameters.values())
                parsed = {}
                positionals = [a for a in argv[1:] if not a.startswith("--")]
                options = argv[1:]

                pos_idx = 0
                i = 0
                while i < len(options):
                    token = options[i]
                    if token.startswith("--"):
                        name = token.lstrip("-").replace("-", "_")
                        if name.startswith("no_"):
                            parsed[name[3:]] = False
                            i += 1
                            continue
                        if i + 1 < len(options) and not options[i + 1].startswith("--"):
                            parsed[name] = options[i + 1]
                            i += 2
                        else:
                            parsed[name] = True
                            i += 1
                    else:
                        i += 1

                for p in params:
                    if p.name in parsed:
                        value = parsed[p.name]
                    elif pos_idx < len(positionals):
                        value = positionals[pos_idx]
                        pos_idx += 1
                    elif isinstance(p.default, _OptionInfo):
                        value = p.default.default
                    elif p.default is inspect._empty:
                        raise SystemExit(2)
                    else:
                        value = p.default
                    if value is not None and p.annotation is not inspect._empty:
                        value = self._convert(value, p.annotation)
                    parsed[p.name] = value

                kwargs = {p.name: parsed[p.name] for p in params}
                func(**kwargs)
                return 0

            def __call__(self):
                import sys

                raise SystemExit(self._run(sys.argv[1:]))

        @staticmethod
        def Option(default=None, *param_decls):
            return _OptionInfo(default, *param_decls)

        @staticmethod
        def echo(message: str) -> None:
            print(message)

    class _CliRunnerFallback:
        def invoke(self, app, args: list[str]):
            buffer = io.StringIO()
            code = 0
            with contextlib.redirect_stdout(buffer):
                try:
                    code = app._run(args)
                except SystemExit as exc:
                    code = int(exc.code)
            return SimpleNamespace(exit_code=code, stdout=buffer.getvalue())

    typer = _TyperFallback()
    CliRunner = _CliRunnerFallback


try:  # pragma: no cover - exercised when deps are installed
    from pydantic import BaseModel, Field
except ModuleNotFoundError:  # pragma: no cover - offline fallback

    def Field(default=None, description: str | None = None):
        return default

    class BaseModel:
        def __init__(self, **kwargs):
            anns = getattr(self, "__annotations__", {})
            for name in anns:
                if name in kwargs:
                    value = kwargs[name]
                else:
                    value = getattr(self.__class__, name)
                current = getattr(self.__class__, name, None)
                if isinstance(current, BaseModel) and isinstance(value, dict):
                    value = current.__class__.model_validate(value)
                setattr(self, name, value)

        @classmethod
        def model_validate(cls, raw: dict):
            obj = cls()
            for key, value in raw.items():
                current = getattr(obj, key, None)
                if isinstance(current, BaseModel) and isinstance(value, dict):
                    setattr(obj, key, current.__class__.model_validate(value))
                else:
                    setattr(obj, key, value)
            return obj
