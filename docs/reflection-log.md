# Reflection Log

**Author:** Varalakshmi

One consolidated record of the self-improving loop: each entry names what triggered a
change, what changed (agent, skill, or memory), the **before** and **after** scores, and
whether the change **held on a rerun**. A memory-curation section at the end records a
pruned stale entry with its reason.

---

## Entry 1 — Over-broad tool grant (2026-09-29)

- **Trigger (eval evidence):** the `forbidden_operations` deterministic check failed —
  the Implementer performed `delete_entry`, which contradicts its write-only charter.
- **Change (tool grant):** removed `delete_entry` from the Implementer in
  `docs/routing-and-tool-grant-map.json` and `.claude/agents/appt-implementer.md`
  (induce commit `b564f82`, fix commit `c26bdaf`).
- **Before:** 13/14 deterministic (`forbidden_operations` FAIL; `tool_grants` passed, so the
  grant map alone could not catch it).
- **After:** 14/14 deterministic (`forbidden_operations`, `tool_grants`, `audit_matches_writes`
  all pass).
- **Held on rerun?** Yes — re-verified on the dev task (no regression) and generalized to the
  unseen holdout HO-06 (`forbidden_operations` passed on an unseen task).
- **Evidence:** `eval/evidence/before/DEV-grant.*`, `eval/evidence/after/DEV-grant.*`,
  `eval/evidence/holdout/HO-06.*`.

## Entry 2 — Agentic tester → deterministic code (2026-10-29, ADR-001)

- **Trigger (observed failure):** the `appt-tester` agent had no working test tool in the
  environment (`coursetools` missing), so the pipeline halted at the test gate.
- **Change (agent → deterministic):** replaced the agent with
  `scripts/run_tests_deterministic.py`, which runs the suite and classifies pass / fail /
  error (three-state).
- **Before:** non-functional — step never completed; latency / cost / score N/A.
- **After:** ~2.3s wall-clock, **$0** token cost, verdict identical across runs; the
  classifier's three states covered by `eval/test_deterministic_step.py` (6/6).
- **Held on rerun?** Yes — the deterministic governance checks do not depend on the tester,
  so no regression; the tester gate now completes instead of halting. ADR-001 moved
  Proposed → Accepted after an end-to-end regression.
- **Evidence:** ADR-001; implementation commit `33e40ba`; unit tests 6/6.

## Entry 3 — Extracted reusable skills from recurring procedures (2026-11-02)

- **Trigger:** the security-review method lived only inside the agent prompt, and the
  right-tool conversion process lived only in the ADRs — neither was reusable by a new team
  member or a future run.
- **Change (skill update):** extracted two versioned skills, `skills/security-review`
  (v1.0.0) and `skills/right-tool-conversion` (v1.0.0), capturing the review checklist and
  the four-signal conversion procedure.
- **Before:** 0 reusable skills for these procedures (ad-hoc, embedded).
- **After:** 2 committed, versioned skills alongside the code.
- **Held on rerun?** The security-review skill matches the findings pattern the reviewer
  produced on the status-route run (race condition, auth gaps), so it reflects real behavior.

## Entry 4 — Retrieval near-miss on a paraphrased query (2026-09-24) — in progress

- **Trigger (eval evidence):** Q2 ("how should we handle failures returned by the appointment
  API routes?") fell below the 0.65 vector threshold, so the FTS5 keyword fallback ranked the
  SMS doc above the intended error-handling doc.
- **Change (planned, retrieval layer):** lower the vector threshold for short paraphrased
  queries, or add a query-shaped sentence to the error-handling lesson; then re-index.
- **Before:** 6/7 ground-truth (85.7%); Q2 FAIL.
- **After:** to be measured on re-run (target: Q2 passes without regressing Q1/Q6).
- **Held on rerun?** Pending — tracked as an open item, honestly not yet closed.
- **Evidence:** `docs/retrieval-quality-report.md`.

---

## Memory curation — pruned stale entry

- **Pruned:** the outdated appointment status-transition lesson from the project knowledge
  layer (`proj-lessons`).
- **Date:** 2026-09-29.
- **Reason (written):** superseded. During the status-transition work the old entry's
  transition table no longer matched the authoritative rule in `decision-007`; it was
  deleted and replaced with the corrected `appointment-status-state-machine` lesson. Keeping
  both would let retrieval surface a contradicted rule. This is why the Implementer's write
  path is supersession (delete-old + write-corrected), and why that very task is what exposed
  the over-broad `delete_entry` grant in Entry 1.
- **Policy:** stale entries are pruned when a lesson is contradicted by a newer decision; the
  removal and reason are recorded here so curation is auditable.

---

## How this maps to the self-improving loop

Each entry is a full **run → review → fix → rerun** cycle driven by a specific eval result or
observed failure, across multiple sessions (2026-09-24 → 2026-11-02) — visible in the commit
history and `docs/calibration-log.md`. Before/after scores show the change held (or, for the
open item, honestly mark it pending).