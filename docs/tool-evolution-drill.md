# Tool-Evolution Drill

**Project:** Appointment-app governed multi-agent engineering pipeline
**Date:** 2026-10-30
**Delivery path:** Job-seeker / no-deployment (representative workflow)

A tool-evolution drill deliberately changes one part of a working agentic system
and uses the evaluation harness and governance controls to confirm the change
improved the system without silently breaking it. This drill documents one change
end to end (converting a step from an agent to deterministic code) and includes a
second, earlier change (revoking an over-broad permission) as evidence that the
harness reliably catches regressions — which is what makes the first drill's
"no regression" result trustworthy.

---

## Drill 1 (headline): Convert the `appt-tester` step from agent to deterministic code

**Variant:** "Convert another step." Governed by ADR-001.

### Change attempted
Replace the agentic `appt-tester` subagent — which was supposed to run the test
suite and report pass/fail — with a deterministic script,
`scripts/run_tests_deterministic.py`, that runs the project's tests and classifies
the result as **pass / fail / error**.

### What was broken before the change
The agentic `appt-tester` was **non-functional** in this environment. Its
`coursetools` test-execution tool does not exist here and a general shell is
disallowed for it (recorded as Holdout gap #2 in the calibration log), so the step
could never actually run — the pipeline **halted at the tester gate**. This made
the conversion more than a cost optimization: it was the fix for a broken step.

### What improved
| Dimension | Before (agentic) | After (deterministic script) |
|---|---|---|
| Functionality | Non-functional; pipeline halted at tester gate | Runs and returns a verdict |
| Latency | N/A (never completed) | ~2.3s wall-clock (~0.18s actual pytest execution) |
| Token cost | N/A | $0 (no model call) |
| Predictability | N/A | Identical verdict across 3 runs (only variance was pytest's embedded timing string) |
| Audit clarity | Agent definition + transcript | ~50-line script; `classify_exit_code` is a pure, unit-tested function |

### What the evaluation detected (and the risk it exposed)
During implementation, the unit tests exposed the central risk of deterministic
code: a script is *repeatable*, but repeatable can mean **reliably wrong**. A naive
"`exit code == 0` → pass, else → fail" check would mislabel an un-runnable suite
(e.g. pytest exit 5, "no tests collected") as a test *failure* 100% of the time.
The tests pin a **three-state** distinction — pass / fail / **error** — so a future
change that collapsed it back to two states turns a test red immediately.

### What was fixed / built
- `classify_exit_code(code)`: a pure function mapping pytest exit codes to
  pass (0) / fail (1) / error (2,3,4,5).
- `eval/test_deterministic_step.py`: 6 unit tests, including the three-state
  limitation and the "no tests collected → error" edge case.
- Input/output moved through named file arguments (not stdout), preserving the
  least-privilege, no-data-leak discipline used for the governed agents.

### Final result
- Implemented and unit-tested: **6/6 passing**.
- Measured before/after recorded in the calibration log (2026-10-29).
- Integrated as **one revertible commit**: the Orchestrator now runs the script;
  the `appt-tester` role, its routing-map row, its governance-policy entry, and its
  agent definition were all retired (least-privilege: access removed the moment it
  was no longer needed).
- End-to-end regression: **11/11** local checks (5 policy + 6 deterministic) and the
  full CI governed pipeline **green** — no regression.
- **ADR-001 accepted.**

---

## Drill 2 (regression-catch evidence): Revoke an over-broad permission

**Variant:** "Revoke a permission." Recorded in the calibration log (2026-09-29).
Included here because it demonstrates the harness catching a real regression — the
capability that makes Drill 1's clean result meaningful.

### Change attempted
A development task ("delete the outdated status-transition lesson and write a
corrected version") led to the `implementer` role's tool grant being widened to
include `delete_entry`, in both `routing-and-tool-grant-map.json` and the agent
definition — contradicting its write-only charter.

### What broke, and how the eval harness caught it
Running the faulted pipeline through the harness, the deterministic
`forbidden_operations` check **failed**: the audit log showed the Implementer
performing `delete_entry` (13/14 deterministic). Critically, the `tool_grants`
check **passed at the same time** — because the grant map now authorized the
operation, the grant check could not see the problem. Only the **independent,
audit-log-backed** policy caught it. This is defense-in-depth working as designed:
two checks with different sources of truth, so a mistake that blinds one is caught
by the other.

### What was fixed
Removed `delete_entry` from the Implementer in both the grant map and the agent's
`tools:` line (back to `write_entry` only).

### Final result
- After the fix: **14/14** deterministic — `forbidden_operations` passes (no
  deletion), `tool_grants` passes (Implementer used only `write_entry`),
  `audit_matches_writes` passes.
- Regression check: the normal record-a-lesson path still scored **14/14** — the
  revocation did not break legitimate behavior.
- Holdout generalization: the fix was confirmed on an unseen task (HO-06), where
  `forbidden_operations` passed — the least-privilege fix generalized beyond the
  development task.

### Honest limitation surfaced by the same drill
HO-06 also revealed a real gap: production runs log `calling_role: "unknown"`, so
the audit-log attribution `forbidden_operations` relies on is not fully trustworthy
on real runs. Recorded as an open risk with a named enforcement-point fix (require a
valid `calling_role` on every write). Documenting the near-miss is itself part of
the self-improving loop — evidence beats assertion.

---

## What the drill demonstrates
- The system can evolve (convert a step, revoke a permission) under governance,
  with every change measured and recorded.
- The evaluation harness **catches regressions** (Drill 2) and **confirms their
  absence** (Drill 1), using deterministic checks with independent sources of truth.
- Changes land as **single revertible commits** with ADRs, so any one can be undone
  and the reasoning survives for a later reviewer.

**Evidence:** calibration log entries 2026-09-29 (over-broad grant) and 2026-10-29
(tester conversion before/after); ADR-001; commit history (feat/implementation,
refactor/integration, adr/accepted); CI run (all gates green).