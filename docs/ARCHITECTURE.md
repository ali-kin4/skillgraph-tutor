# SkillGraph Insights architecture

## Design principles

**Local-first, real state, explainable logic.** The browser calls a local Python API backed by existing SkillGraph state files. It never fabricates mastery values to make a chart look populated. A separate reproducible fictional cohort is available by opt-in.

**No paid dependencies or remote model calls.** Static HTML/CSS/JavaScript and the Python standard-library HTTP server support the UI. Existing Typer/Pydantic CLI and engine stay functional.

**Read vs write separation.** Dashboard data and exports are GET resources. Practice submissions are explicit, bounded POST requests which use StudentState.update_mastery and sm2_update, then persist through save_student. A template-based tutor endpoint does not modify state.

## Data flow

1. **Input**: a local graph.json (nodes/requires), students/*.json (mastery and spaced-repetition states), and optional cohort_metadata.json (synthetic flag and group labels).
2. **Analytics**: load_cohort reads the workspace and dashboard_snapshot computes at a given timezone-aware instant.
3. **Presentation**: the browser receives concept, student and group summaries. SVG nodes and CSS charts are derived from these values and reflect real missingness.
4. **Practice**: the instructor chooses a learner, concept, correctness, and confidence. The server validates inputs, loads the student, invokes original model/scheduler, and writes that learner's state.
5. **Reports**: CSV/JSON exports come from the same snapshot contract.

## API contract

| Verb | Path | Purpose |
| --- | --- | --- |
| GET | /api/dashboard | Full cohort snapshot and methodology |
| GET | /api/student?id=... | One learner's dashboard state |
| GET | /api/insights?scope=...&weeks=... | Weekly mastery history, two scenario projections, 4-week concept growth and rule-based insights. `scope` is `cohort`, `group:<name>` or `learner:<id>`; `weeks` is 1–26 |
| GET | /api/export.csv | Per-learner, per-concept CSV with safe spreadsheet cells |
| GET | /api/export.json | Full JSON snapshot |
| POST | /api/tutor | Offline deterministic Socratic question/hint/next step |
| POST | /api/attempt | Record human-reported practice result and update existing engine |

### Assessment request

~~~json
{
  "studentId": "learner-01",
  "concept": "Python Essentials",
  "correct": true,
  "confidence": 0.85
}
~~~

The API does not accept free-form masteries: only observations are recorded. The original engine computes the new state and SM-2 interval.

## Growth history and scenario projections

`StudentState.update_mastery` appends a `(timestamp, mastery)` point to the concept's `history` (bounded to the latest 120 points). Older learner files without `history` load unchanged; for them the last recorded `updated_at`/`mastery` pair is the only point.

`insights.py` holds pure functions over these states:

- **History:** for each of the last 12 weeks, the mean of every learner-concept pair's most recent recorded estimate at that instant. Pairs not yet observed are excluded and the per-week observation count is returned, so new concepts entering the curriculum are visible rather than silently imputed. The final point equals the dashboard snapshot mean.
- **Scenario projections:** starting from each current estimate, *with practice* applies one successful review per week at confidence 0.7 through the learner's own learning rate and forgetting rate; *without practice* applies only exponential forgetting. Both are what the heuristic model implies under a stated assumption, not forecasts.
- **Concept growth:** mean change over 28 days among learners observed at both ends.
- **Insights:** fixed rules (fastest-growing skills, lowest-mastery concept and its weakest prerequisite, scenario gap, due reviews). Each insight lists the concepts it names so the UI can link them to the charts.

The Insights view renders these with dependency-free SVG/HTML: a learner × concept heat map on a single-hue sequential scale with five labelled bands and hatched "not observed" cells, skill averages with 4-week change, and the trajectory chart with a keyboard-accessible crosshair and a data-table fallback.

## Graph visualization

Topological depth is computed from explicit prerequisites, with cycle detection to avoid browser hangs. The graph uses an accessible, interactive SVG with selectable nodes. Nodes can be shaded using the cohort's observed mean or one selected learner's concept state.

**Graph caveat:** the source syllabus parser can accept invalid prerequisites and cycles; the display avoids infinite loops but does not claim to validate curriculum correctness. A future release may add strict DAG diagnostics and upstream graph validation.

## Practical security boundary

- HTTP binds only to 127.0.0.1 and is not suitable for direct internet access.
- Static assets are served by strict path allowlisting; no arbitrary file browsing.
- Learner IDs are constrained, and the server checks symlinks on write.
- Cross-origin JSON writes with a mismatched Origin are rejected.
- POST body must be application/json and not exceed 8192 bytes.
- No authentication, session isolation, concurrent editing support, or fine-grained authorization is provided.
- No personal data is transmitted to third-party SaaS by the application; it does not use telemetry or external frontend packages.
- The local filesystem and workstation permissions remain the actual access-control boundary.

Do not expose this server to other users until authentication, persistent audit logging, role-based authorization, CSRF protections, concurrency handling, privacy agreements and security review have been implemented.

## Testing

Unit tests validate synthetic cohort repeatability and non-destructive initialization, support math, missingness, review dates, CSV escaping, API behavior, and original mastery/scheduler integration.

A real Chromium smoke test covers dashboard loading, roster filtering, learner inspection, graph interaction, due reviews, deterministic coaching, practice submission, CSV download, and mobile drawer/overflow. The screenshot artifact demonstrates actual UI rendering.

All tests use synthetic local data. They are not evidence of predictive accuracy, psychometric validity, pedagogical effectiveness, or production security.

## Roadmap after this upgrade

- Pilot study of instructor usability and actual measured learning outcomes with consent and a declared design
- Per-item/question evidence models with validated parameters; do not call it BKT/IRT until actually implemented
- Audit history, immutable snapshots, concurrency-safe persistence and role-based access
- Privacy/data retention features for hosted operations
- Independent accessibility audits and additional browser coverage
- Optional LLM adapter only with clearly separated model results, privacy agreements and evaluation harness
