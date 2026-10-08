# Evaluation, measurement and honest claims

SkillGraph is a teaching/analytics *demonstration*. Its built-in synthetic cohort has 16 fictional names, three fictional learning groups, a nine-concept syllabus, and seeded numerical observations. These are **not records of delivered corporate training or proven educational outcomes**.

## Observed vs unobserved

| Signal | Meaning | Avoid claiming |
| --- | --- | --- |
| Mastery estimate | Persisted 0–1 state updated by a handcrafted learning-rate heuristic | Calibrated competence probability |
| Mastery mean | Arithmetic mean of recorded learner-concept entries | Standardized exam score |
| Coverage | Fraction of concept entries with a state | Attendance or completion percentage |
| Reviews due | Saved due timestamps at/before UTC snapshot | All concepts needing urgent teaching |
| Support label | Explicitly documented screening rules | Likelihood of dropout or course failure |
| Socratic prompt | Deterministic scaffold generated from a concept | Personalized LLM feedback or independent grading |
| 7-day plan | Heuristic plan produced by current planner | Optimized or validated intervention sequence |

## Calculation audit

For every learner, calculate the mean only across non-missing concept masteries. The **cohort mean** pools all observed learner-concept entries and therefore weights learners with more observed concepts more heavily. This choice is disclosed; compare with equal-learner weighting before drawing policy conclusions.

A low mastery value signals a candidate review target, but it is not a causal explanation of why a learner struggled. Do not treat lack of observations as failure. A due review requires an explicitly stored deadline; never turn an unattempted concept into overdue work simply because the core scheduler treats an unscheduled state as due when invoked by the CLI.

Use dates as UTC instants and make no assumptions about the user's time zone beyond display formatting.

## Risk/support rules

- **Needs support:** at least 3 scheduled due items, or any observed mastery below 0.40.
- **Monitor:** any due review, or at least 2 observed masteries below 0.60.
- **On track:** no flag, with at least one observed concept.
- **Unassessed:** no concept states.

This is deliberately described as a transparent *support prioritization rubric*. It has no fitting, calibration, sensitivity analysis, validation cohort, uncertainty interval, subgroup fairness evaluation, or evidence supporting individual outcome predictions.

## Evaluation roadmap

To establish educational usefulness with real consented participants:

1. Pre-register questions and operational definitions (e.g., improvement in knowledge checks, retention after 14 days).
2. Use real item-level graded outcomes and review event history.
3. Establish pre/post and delayed post-tests with comparable difficulty.
4. Compare to baseline instructional strategies; account for prior knowledge and selection.
5. Estimate effect sizes and uncertainty; handle repeated measures and missing data.
6. Evaluate explainability, instructor workload, usability and learner experience.
7. Perform subgroup fairness and privacy impact assessments before high-stakes use.
8. Publish reproducible evaluation scripts and limitations.

Until those steps are complete, use language such as **"prototype of learning analytics and spaced-practice support"**, not **"clinically validated"**, **"predicts failure"**, **"increases learning by X%"**, or **"guaranteed performance"**.

## Privacy checklist

- The dashboard is served on loopback, with no remote authentication.
- Use only fictional or properly authorized real learning records.
- Do not publish real learner CSV exports or screenshot identifiable information.
- Restrict local workspace file permissions and back up before trying demonstrations on real data.
- Avoid using this workbench for minors or sensitive educational records without a separate privacy/legal review.

## What has been technically verified

CI validates code style, existing CLI behavior, analytics/API tests, and a Chromium smoke run. These checks verify software contracts and selected functional paths. They do not verify correctness of every possible API input, browser, accessibility requirement, pedagogical result, or deployed security boundary.
