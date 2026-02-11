from __future__ import annotations

import inspect


class OptionInfo:
    def __init__(self, default=None, *param_decls):
        self.default = default
        self.param_decls = param_decls


def Option(default=None, *param_decls):
    return OptionInfo(default, *param_decls)


def echo(message: str) -> None:
    print(message)


class Typer:
    def __init__(self, help: str | None = None):
        self.help = help
        self._commands = {}

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

    def _run(self, argv: list[str]):
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
            elif isinstance(p.default, OptionInfo):
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
