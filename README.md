# SkillGraph Insights

**An offline-first intelligent learning and assessment platform.**

SkillGraph combines a Python mastery/review engine with a local visual dashboard for instructors, technical trainers, and learners. It helps answer practical teaching questions: *Which concepts have been observed? Who has practice due? Where are the knowledge gaps? What should we do next?*

The core engine remains available through its original CLI. The Insights dashboard adds a **cohort overview, learner profiles, interactive prerequisite graph, review center, cohort reporting, and guided practice**.

Created by [Ali Jabbary](https://alijabbary.com) · [GitHub](https://github.com/ali-kin4/skillgraph-tutor)

> **Accuracy and privacy:** This is an offline-first **local demonstration**, not a remotely authenticated learning management system or a validated learning-risk prediction product. Example learners are fictional. Mastery values are heuristic state estimates, not probabilities of passing an exam. Socratic prompts are deterministic templates, not an autonomous LLM.

## Start in under two minutes

Install Python 3.11+ and run from the repository root:

~~~bash
python -m pip install -e ".[dev]"
skillgraph dashboard --demo
~~~

Open **http://127.0.0.1:8765**.

The first run initializes a reusable, isolated **synthetic** workspace in `workspace/insights-demo`. Subsequent runs keep the learner changes you made in that local demonstration.

A different local workspace can be opened without synthetic seeding:

~~~bash
skillgraph dashboard --workspace workspace
~~~

The workspace must already have `graph.json` and any learner state files under `students/`. Initialize with the existing CLI first.

Choose a port or alternate workspace if needed:

~~~bash
skillgraph dashboard --demo --workspace workspace/my-demo --port 8766
~~~

**The server binds to 127.0.0.1 only** and intentionally provides no authentication. Do not proxy or expose it to the internet without implementing a proper authentication, authorization, and security architecture.

### Dashboard experiences

| Experience | What it actually does |
| --- | --- |
| Instructor overview | Cohort size, observed mastery, explicit scheduled reviews, support categories, concept bottlenecks |
| Learner explorer | Search/filter by group or support; inspect learner mastery and honest missingness |
| Interactive knowledge graph | SVG prerequisite network colored by cohort or selected learner's observed mastery |
| Review center | Due practice queue based on actual scheduled due dates |
| Cohort reporting | Per-group summaries and safe CSV/JSON exports |
| Socratic practice | Offline deterministic hints, questions, and micro-actions |
| Record a practice result | An instructor-selected correct/incorrect observation updates the original mastery model and SM-2 schedule |
| Methodology | Every important calculation and limitation documented in the interface |

The dashboard uses a dependency-free, responsive web interface. It works locally without accounts, a cloud API key, external fonts, or telemetry.

## Architecture

~~~text
                           local browser
            ┌─────────────────────────────────┐
            │ SkillGraph Insights UI           │
            │ Overview • Roster • Knowledge    │
            │ Graph • Review • Coaching        │
            └────────────────┬────────────────┘
                             │ same-origin /api
                 ┌───────────▼───────────────┐
                 │ Local Python HTTP server  │
                 │ Bound to 127.0.0.1 only   │
                 └───────────┬───────────────┘
                             │
                 ┌───────────▼────────────────┐
                 │ SkillGraph existing engine │
                 │ graph · student · scheduler│
                 │ tutors · planner · reports │
                 └───────────┬────────────────┘
                             │
                  local graph.json +
                  students/*.json
~~~

Core additions:

- `src/skillgraph_tutor/analytics.py`: deterministic cohort analytics, gaps, support categories, CSV export
- `src/skillgraph_tutor/dashboard_server.py`: loopback server, static assets, explicit API routes
- `src/skillgraph_tutor/demo_data.py`: deterministic fictional cohort generator
- `src/skillgraph_tutor/web/`: real dashboard HTML, CSS, JavaScript, and vector graph
- `tests/test_analytics.py` and `tests/test_dashboard_server.py`: numerical, API, privacy and export checks
- `tests/browser-smoke.mjs`: real-browser learner, mastery and responsive flows

See [architecture](docs/ARCHITECTURE.md) and [evaluation and limitations](docs/EVALUATION_AND_LIMITATIONS.md).

## How the measurements work

- **Mastery:** An original SkillGraph student state contains a value between 0 and 1 for each observed concept. Correct/incorrect observations move that value with a configurable learning-rate heuristic. Forgetting is applied when a new assessment updates the model; displaying the snapshot does not silently recalculate or persist decay.
- **Unattempted:** A concept without a saved state is **not observed**, not zero mastery. It is excluded from means and visualized separately.
- **Due:** Only previously scheduled reviews with a timestamp on or before the current UTC snapshot count as due. An untouched concept is not implicitly overdue.
- **Support label:** A transparent action-priority heuristic, not a predicted dropout or exam-failure probability:
  - *Needs support:* three or more due reviews, or an observed mastery below 0.40.
  - *Monitor:* a due review or at least two observed concepts below 0.60.
  - *On track:* neither rule applies.
  - *Unassessed:* no observed concepts.
- **Cohort mean:** Mean of **all observed learner × concept entries**, not a mean of unobserved concepts set to zero.
- **Socratic tutoring:** Offline fixed prompts with scaffolding, not automated grading. A human reports practice correctness and confidence.

Use generated synthetic data only to demonstrate product capability—not to assert measured real-world training gains, clients, or commercial deployments.

## CLI — original engine preserved

~~~bash
skillgraph init data/sample_syllabus.md
skillgraph add-student s1 --name "Ada"
skillgraph study s1 --concept Variables
skillgraph quiz s1 --concept Variables --correct --confidence 0.8
skillgraph review s1
skillgraph plan s1 --horizon 7d
skillgraph report s1 --out reports/s1
skillgraph doctor
~~~

The CLI still supports offline concept graph construction, mastery states, SM-2 spaced repetition, Socratic prompt templates, planning and reports.

## Quality gates and screenshots

~~~bash
ruff check .
ruff format --check .
pytest -q
make demo
~~~

Pull requests also run a **Chromium browser smoke test** covering the dashboard, learner filtering, interactive graph, due reviews, Socratic prompts, recorded practice, CSV export, and narrow mobile layouts.

Browser-generated screenshots are uploaded to the [GitHub Actions workflow](https://github.com/ali-kin4/skillgraph-tutor/actions) as the `skillgraph-insights-screenshots` artifact. These are **real rendered captures**, not generated mockups.

## Limitations and responsible usage

This project has no multi-user permissions, audit database, proctoring, identity verification, bias evaluation, calibrated mastery model, or learner-risk validation. Running a local server on a workstation does not confer security to a public network deployment. Learner names and observations are personally sensitive in real use: use consent, access controls, and retention policies before working with real customer data. See the dedicated [evaluation and limitations guide](docs/EVALUATION_AND_LIMITATIONS.md).

## License

Apache-2.0 · See [LICENSE](LICENSE). Original project contributors and code history preserved.
