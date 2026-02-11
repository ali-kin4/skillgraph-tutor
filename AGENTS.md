# AGENTS.md

Guidance for coding agents and contributors.

## Core commands

- `make setup` - install local package + dev tools
- `make fmt` - format with ruff
- `make lint` - lint with ruff
- `make test` - run pytest
- `make demo` - execute end-to-end CLI demo

## Style rules

- Keep default operation fully offline.
- Prefer deterministic behavior (seeded where relevant).
- Add or update tests for new behavior.
- Keep modules focused and small.
- Avoid unnecessary dependencies.

## Safe module extension

- New planners/schedulers should be pure functions where possible.
- Persist student state only through `student.py` helpers.
- CLI should orchestrate services, not hold business logic.
