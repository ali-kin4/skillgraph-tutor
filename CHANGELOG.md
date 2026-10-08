# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.2.0] - 2026-10-08

### Added

- **Insights view** in the dashboard: learner × skill mastery heat map, average mastery by skill with 4-week change, growth trajectory with "with practice" and "without practice" scenario projections, and rule-based insights that link to the charts. Scope by cohort, group or learner; 4/8/12-week horizons; tooltips, keyboard navigation and a data-table fallback.
- `GET /api/insights` endpoint and the pure `skillgraph_tutor.insights` module.
- Bounded per-concept mastery history recorded by `StudentState.update_mastery`; existing learner files load unchanged.
- Deterministic simulated history for the synthetic demo cohort.
- Deep links to dashboard views (for example `/#insights`).
- `scripts/capture_screenshots.py` to regenerate README screenshots with a local headless browser.
- CI matrix across Linux, Windows and macOS on Python 3.11–3.13, coverage reporting, wheel content verification, and browser tests on `main`.
- Issue and pull request templates, Dependabot, pre-commit, `.editorconfig`, `.gitattributes`, `py.typed`.

### Changed

- Package metadata: classifiers, project URLs and single-sourced version.
- Methodology view and docs describe growth history, projections and insights.
- Sidebar call-to-action now opens the Methodology view; removed the decorative avatar.

### Fixed

- `skillgraph quiz` can now record incorrect answers (`--no-correct`); previously `--correct` was a required flag with no negative form.
- `skillgraph study` no longer prints a duplicated "Hint:" prefix.
- README and `examples/demo_run.sh` CLI examples match the actual command signatures.
- The dashboard server reads request bodies before rejecting them, so clients receive the error response instead of a connection reset (seen on Windows).

### Removed

- Duplicate demo syllabus under `demo/` (the packaged copy is the single source) and an internal agent prompt document.

## [0.1.1] - 2026-10-08

### Added

- SkillGraph Insights dashboard: cohort overview, learner explorer, interactive knowledge graph, review center, cohort reports with CSV/JSON export, Socratic practice and recorded practice outcomes, methodology page.
- Loopback-only HTTP server with origin, content-type and size checks and a strict CSP.
- Synthetic 16-learner demo cohort, architecture and evaluation documentation, Chromium smoke test.

## [0.1.0] - 2026-02-11

### Added

- Offline CLI: syllabus-to-graph builder, student mastery model with forgetting, SM-2 spaced repetition, Socratic tutor templates, planner, reports and evaluation harness.

[Unreleased]: https://github.com/ali-kin4/skillgraph-tutor/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/ali-kin4/skillgraph-tutor/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/ali-kin4/skillgraph-tutor/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/ali-kin4/skillgraph-tutor/releases/tag/v0.1.0
