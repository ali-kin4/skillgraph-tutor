# Contributing

Thanks for helping improve SkillGraph. This guide covers setup, the change workflow and the standards every pull request is reviewed against.

## Development setup

Requirements: Python 3.11+, Git, and optionally Node.js 20+ for the browser smoke test.

```bash
git clone https://github.com/ali-kin4/skillgraph-tutor.git
cd skillgraph-tutor
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
python -m pip install -e ".[dev]"
pre-commit install                                   # optional: ruff on every commit
```

`make` targets wrap the common commands (`make help` lists them). On systems without `make`, run the underlying commands shown in the `Makefile`.

| Task | Command |
| --- | --- |
| Format and autofix | `make fmt` |
| Lint | `make lint` |
| Tests | `make test` (or `make cov` for coverage) |
| End-to-end CLI demo | `make demo` |
| Run the dashboard on demo data | `make dashboard` |
| Regenerate README screenshots | `make screenshots` |

### Browser smoke test

```bash
skillgraph dashboard --demo --workspace workspace/insights-demo --port 8765 &
npm install --no-save --no-package-lock playwright@1.56.1
npx playwright install chromium
node tests/browser-smoke.mjs
```

Screenshots of every view at desktop and mobile widths land in `screenshots/`.

## Workflow

1. Open or reference an issue describing the problem.
2. Branch from `main` (`feat/…`, `fix/…`, `docs/…`).
3. Make the change with tests. Keep commits focused and use [Conventional Commits](https://www.conventionalcommits.org/) prefixes (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `chore:`).
4. Run `make check` locally.
5. Open a pull request and complete the template. CI runs lint, the test matrix (Linux, Windows, macOS; Python 3.11–3.13), a wheel build check and the Chromium smoke test.
6. PRs are squash-merged once CI is green and review is complete. Add a line to `CHANGELOG.md` under *Unreleased*.

## Engineering standards

- **Offline by default.** No required network calls, accounts or API keys.
- **Deterministic.** Seed any randomness; demo data must be reproducible.
- **Explainable metrics.** Every number in the UI traces to a documented rule. Missing observations stay missing, never zero. Document new metrics in the Methodology view and `docs/`.
- **Pure analytics.** Planners, schedulers and analytics are pure functions where possible. Persist learner state only through `student.py` helpers. The CLI and HTTP server orchestrate; they do not hold business logic.
- **Small, focused modules** and no new runtime dependencies without a clear operational reason.
- **Frontend:** dependency-free HTML/CSS/ES modules, no CDN assets, all dynamic text escaped, keyboard accessible, no horizontal overflow at 390px.
- **Privacy:** never commit real learner data, exports or screenshots of real records.

## Releasing

1. Move *Unreleased* entries in `CHANGELOG.md` under a new version heading.
2. Bump `__version__` in `src/skillgraph_tutor/__init__.py`.
3. Tag `vX.Y.Z` on `main` and publish a GitHub release with the changelog section.
