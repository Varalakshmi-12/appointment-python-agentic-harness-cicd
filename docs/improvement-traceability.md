# Improvement Traceability — the self-improving loop across the course

Author: Varalakshmi

This maps each run → review → fix → rerun cycle to its committed, dated evidence, so
the self-improving loop is auditable end to end — original failure, the eval result
that caught it, the change made, and the rerun that confirmed it held.

## A note on provenance (read first)

The incremental agentic development was done in a local working copy of the target
codebase and was assembled into this capstone repository in a single import, so this
repo's `git log` does not reproduce the per-change cadence. Two things make the loop
auditable anyway:

- The **base codebase** has a real, incremental public history (March–August 2026) at
  <https://github.com/Varalakshmi-12/Appointment-Python> — the Flask/MySQL/React
  appointment app the agents operate on, built commit by commit (initial app, the
  Twilio test file, email error-handling, removing hardcoded DB credentials, the agent
  sandbox Dockerfile).
- The **agentic cadence** below is traced through the dated `docs/calibration-log.md`
  entries and the before/after evidence files committed here. Each row's evidence can
  be opened and checked, and the dates span the course (2026-09-24 → 2026-11-12). The
  pair `HO-06-before-fix` (13/14) → `HO-06` (14/14), and the `eval/evidence/before/` →
  `eval/evidence/after/` folders, are the artifact-level equivalent of a fix commit and
  its verifying rerun.

Nothing here is back-dated or reconstructed to imply a history that was not recorded;
the dates and scores are those of the committed evidence.

## The cycles

| # | Date | Original failure | Eval result that caught it | Change (layer) | Regression / rerun that confirmed it held | Committed evidence |
|---|---|---|---|---|---|---|
| 1 | 2026-09-24 | A paraphrased query (Q2, "how should we handle failures from the appointment API routes?") missed the error-handling lesson under the lexical ranker | precision@1 = 6/7; Q2 FAIL (fell below the 0.65 vector floor, keyword fallback ranked the SMS doc on top) | **Retrieval tool:** replaced the lexical ranker with a spaCy GloVe dense-vector ranker (300-dim, cosine) + TF-IDF lexical gate | Re-measured **6/6**, Q2 now retrieves the error-handling lesson at 0.935 on the vector path; no regression on Q1/Q6 | `docs/retrieval-quality-report.md`; `mcp-servers/retrieval/retrieval_eval.py` |
| 2 | 2026-09-29 | The Implementer performed `delete_entry`, contradicting its write-only charter | `forbidden_operations` FAIL — **13/14** (while `tool_grants` passed, because the grant map authorized the delete: a defect manual grant-review could not see) | **Tool grant:** removed `delete_entry` from the storage allow-list, routing-and-tool-grant map, and `agents/appt-implementer.md` | Dev run re-run **14/14** (record-a-lesson path unaffected); generalized to holdout **HO-06** on an unseen task | `eval/evidence/before/DEV-grant.*`, `eval/evidence/after/DEV-grant.*`, `eval/evidence/DEV-appt-status.*` |
| 3 | 2026-10-29 | The agentic `appt-tester` had no working test tool in the environment, so the pipeline halted at the test gate (non-functional) | Step never completed — latency/cost/score N/A | **Agent → deterministic code:** converted the tester to `scripts/run_tests_deterministic.py` (ADR-001), three-state pass/fail/error | `eval/test_deterministic_step.py` **6/6**; the converted step runs in HO-02/04/05, each clearing the gate (14/14) | `docs/adr/ADR-001-tester-deterministic-conversion.md`; `scripts/run_tests_deterministic.py`; `eval/test_deterministic_step.py` |
| 4 | 2026-11-02 | The security-review method lived only in an agent prompt and the right-tool process only in ADRs — neither reusable by a new run or teammate | 0 reusable skills for these procedures | **Skills:** extracted two versioned skills (v1.0.0) | The security-review skill matches the findings pattern the reviewer produced on the status-route run (race condition, auth gaps) | `skills/security-review/`, `skills/right-tool-conversion/` |
| 5 | 2026-11-06 | A stale appointment status-transition lesson no longer matched the authoritative rule in decision-007 | Keeping it would let retrieval surface a contradicted rule | **Memory:** pruned the stale lesson with a written reason; wrote the corrected state-machine lesson in its place | Curation recorded and auditable; retrieval no longer returns the contradicted rule | `docs/reflection-log.md` (Memory curation); `.memory/reference/REFERENCE_INDEX.md` (Pruned entries) |
| 6 | 2026-11-12 | Storage attributed every write to `orchestrator` (shared-role identity), so per-role limits did not hold in a live session | `no_unknown_caller` FAIL on the first HO-06 run — **13/14** (`calling_role: "unknown"`) | **Tool + agent:** storage now takes `calling_role` per call; `appt-implementer` passes `calling_role=implementer` | `eval/test_per_role_enforcement.py` **5/5** (Implementer denied `delete_entry`/`read_entry`); **HO-06 re-run 14/14** (was 13/14) | `eval/test_per_role_enforcement.py`; `eval/evidence/holdout/HO-06{,-before-fix}.*` |

## Reading the table

Each row is one complete cycle: a specific failure or eval result drove a change to an
**agent**, **skill**, **memory** entry, or **tool grant**, and a rerun — a regression
check or an unseen holdout — confirmed the change held. The six cycles run from
2026-09-24 to 2026-11-12, so the loop operated across the full course, not only in the
final tool-evolution drill. The before/after scores (6/7 → 6/6, 13/14 → 14/14,
non-functional → 6/6) are the proof each change improved the system without regressing
the rest; the full regression set is the six holdouts, all passing after the three
fixes (grant, storage-audit, retrieval vector-tool).