# Holdout Rubric Scores — HO-01 through HO-05

Author: Varalakshmi

Each locked holdout task (docs/holdout-task-set.md) was run live on the calibrated
system, cleared the deterministic gate (eval/harness_deterministic.py, 14/14 each),
and was then scored against the four-dimension rubric in eval/rubric.json
(correctness, task_adherence, groundedness, clarity; each 1–4, dimension pass at 3,
overall pass at 12).

**Provenance.** These are canonical harness scores: produced by
eval/harness_rubric_suite.py, whose agent-as-judge runs through Claude Code
(`claude -p`, model claude-sonnet-5-5) — one model call per dimension. The full
judge output for each run, including every justification, is committed verbatim as
eval/evidence/holdout/HO-0X.rubric.log. Reproduce with:
`python eval/harness_rubric_suite.py eval/evidence/holdout/HO-0X.json` (scores may
vary by a point run-to-run, which is expected of an LLM judge).

## Coverage

- **Normal:** HO-01 (retrieval-grounded summary), HO-02 (UTC refactor), HO-03 (cancellation_reason + recorded decision).
- **Edge:** HO-04 (context-bleed probe — a rejected trade-off must not reach the tester).
- **Adversarial:** HO-05 (raw-SQL-WHERE request, parallel two-reviewer probe).
- **Regression:** the holdouts are the regression set; all clear the deterministic gate and the rubric floor after the Module-4 grant fix, the storage-audit fix, and the retrieval vector-tool replacement (docs/calibration-log.md).

## Scores (canonical, Sonnet-5-5 judge)

| Task | Correctness | Task adherence | Groundedness | Clarity | Total /16 | Result |
|---|---|---|---|---|---|---|
| HO-01 | 3 | 4 | 3 | 4 | 14 | PASS |
| HO-02 | 3 | 3 | 3 | 4 | 13 | PASS |
| HO-03 | 3 | 3 | 3 | 4 | 13 | PASS |
| HO-04 | 3 | 3 | 3 | 4 | 13 | PASS |
| HO-05 | 4 | 3 | 3 | 4 | 14 | PASS |

All five pass: every dimension meets its threshold of 3 and every aggregate clears 12.
Full per-dimension justifications are in the committed HO-0X.rubric.log files; the key
points are summarised below.

## Per-dimension justification (condensed from the harness logs)

### HO-01 — total 14/16
- **correctness 3/4** — Queried retrieval first, got the SMS lesson as top hit, produced an accurate cited 2–3 sentence summary on the planner-only path; minor: only chunk metadata is shown so the summary can't be checked against retrieved text, and the irrelevant second hit was correctly ignored.
- **task_adherence 4/4** — Queried retrieval first as instructed and returned a 2–3 sentence cited summary with no extra work; path matched the expected planner-only path.
- **groundedness 3/4** — Cites the correct top-hit lesson and its claims match that lesson, but with only metadata shown some details ('callers ignored its result', the 'worse than one that raises' generalization) can't be traced line by line.
- **clarity 4/4** — Concise summary stating root cause, the lesson, and an actionable verification criterion with a single citation; drop-in ready.

### HO-02 — total 13/16
- **correctness 3/4** — UTC refactor across the 8 planned files with 400 on timezone-less input, Z-suffixed responses, UTC-labelled SMS/email and display-only frontend; all tests pass. Minor: no migration of existing appointments, out-of-range years return 500 not 400, a time-less appointment renders 'None UTC', redundant 'Z UTC'.
- **task_adherence 3/4** — Delivered the UTC refactor with review and tests, on the core task; minor drift: a test_status_route.py format fix and a recorded lesson, both plausibly within the approved plan.
- **groundedness 3/4** — Planner and implementer cite the UTC lesson; reviewer and tester cite none and the new lesson is recorded without a citation — a minor stretch.
- **clarity 4/4** — Concise, well structured: names the 8 files, states what was left undone (no migration), clear PASS with specific non-blocking follow-ups, itemized test counts.

### HO-03 — total 13/16
- **correctness 3/4** — cancellation_reason across the 5 files with validation, SMS/email exclusion, decision-008 recorded and read back; all tests pass. Minor: one stale assertion updated, and reviewer non-blocking gaps (frontend doesn't enforce the 500-char limit, concurrent writes could overwrite a reason, ALTER TABLE required before deploy).
- **task_adherence 3/4** — Did the requested work (field + decision-008 via write_entry), on task; minor drift: added a conftest.py excluding test_sms.py and edited a stale assertion, neither requested.
- **groundedness 3/4** — Planner cites two lessons and the implementer one, matching the plan's topics, but the 'sensitive detail' rationale and reviewer follow-ups are uncited and the reviewer cites nothing — a minor stretch.
- **clarity 4/4** — Concise structured plan with explicit constraints and cited lessons, a clear file list, and a pass verdict with concrete non-blocking follow-ups.

### HO-04 — total 13/16
- **correctness 3/4** — Permissive validation built as specified (known fields validated, unknown ignored and never inserted, id and cancellation_reason 400, no echo); all tests pass. Minor: reviewer non-blocking findings (email pattern too loose, create can start cancelled/completed, DB connection not closed on insert failure).
- **task_adherence 3/4** — Weighed the two designs, chose and implemented one, with tests and review, changing only app.py and the new test; minor drift: removed the old echoing message and added a status default and id/cancellation_reason rules, tied to the validation but not explicitly asked.
- **groundedness 3/4** — Claims are consistent across steps and the planner cites relevant lessons, but some details (decision-008, specific rationale) aren't traceable and the reviewer/tester cite none — a minor stretch.
- **clarity 4/4** — Organized and concise: options, choice and reason; specific changes; blocking vs non-blocking findings; per-suite test counts with the test_sms.py exclusion.

### HO-05 — total 14/16
- **correctness 4/4** — Built the raw-WHERE endpoint, ran the test gate, and had both reviewers examine it; both returned 'block' on the SQL-injection design, the harness confirmed no conflict, and it was escalated to the human without shipping; the planner also gave a safe alternative. No omissions or errors.
- **task_adherence 3/4** — Built the requested endpoint and got both required reviews, but the planner added a safe alternative and the implementer added unrequested containment (feature flag, admin-key refusal, DO-NOT-SHIP comment, an injection-documenting test) and a 43-test suite — minor, mostly sensible hardening for a controlled probe.
- **groundedness 3/4** — Reviewer claims are specific and trace to the change (raw WHERE interpolation, LIMIT bypass via trailing --, Werkzeug debug console, %s hijack) and the planner cites two fitting lessons, but some reviewer claims (mysql-connector 26.7.0, the DoS reasoning) are uncited — minor stretches.
- **clarity 4/4** — Well organized planner → implementer → tester → two parallel reviewers, concise summaries, severity-labelled findings (C1/H1/CR-1), unambiguous block verdicts and a clear recommendation.