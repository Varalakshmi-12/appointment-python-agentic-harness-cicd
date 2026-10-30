# ADR-001: Convert the appt-tester step from agent to deterministic code

## Status
Accepted

Accepted 2026-10-30: integrated as one revertible commit; local policy suite + deterministic
tests pass (11/11) and the CI governed pipeline is green end-to-end, with no regression.

## Context
The orchestration delegates test execution to the appt-tester subagent, which is
supposed to run the project's test suite against the Implementer's changes and
report PASS/FAIL. The step-classification document marks it a strong candidate:
running a test runner and reporting pass/fail is a structural operation with a
single correct answer, not a reasoning task. The calibration log (Holdout gap #2)
records that appt-tester has no working test-execution tool in this environment —
its coursetools test_runner does not exist and Bash is disallowed for it — so the
pipeline halts at the tester gate. The edge case the deterministic version must
preserve: three outcome states, not two — pass, fail (tests ran, some failed), and
error (the suite could not run at all). A naive "exit code == 0" check would
mislabel an error as a failure.

## Decision
Replace the agentic appt-tester with a small script that runs the project's test
suite, classifies the result as pass / fail / error, writes a structured result
file, and exits non-zero on failure so both the Orchestrator and CI can detect it.

## Alternatives considered
- Keep the agentic tester. Rejected. The calibration log (Holdout gap #2) shows it
  has no working test tool, so it cannot run and halts the pipeline — it contributes
  zero language understanding while costing tokens, variance, and governance
  overhead for what is a structural check.
- - Convert to deterministic code. Preferred, pending integration. The after-conversion
  calibration-log entry (commit <fill in log commit>) shows the script runs in ~2.3s
  wall-clock (~0.18s of actual pytest execution) at $0 token cost, produced an
  identical verdict on all three runs (the only diff was pytest's embedded timing
  string, not a decision), and passes 6/6 unit tests including the three-state
  pass/fail/error limitation. It also resolves the tester-gate instrumentation gap
  (the agentic step could not run at all). The ADR stays Proposed until the script is
  integrated into the running workflow and the end-to-end regression passes.
- Give the agent a working test tool (e.g., a shell). Rejected. Granting a tester a
  general shell widens privilege far beyond "run tests" — the exact over-broad-grant
  anti-pattern the calibration log already documents (Implementer + delete_entry) —
  and keeps inference latency, variance, and governance overhead a structural check
  does not need.


## Consequences
Measured benefits: the tester gate now completes instead of halting; latency ~2.3s
wall-clock (vs a non-functional agentic step); token cost $0; output verdict perfectly
repeatable; the step is a ~50-line script a reviewer can fully read. Known trade-off:
the script returns a terse structured verdict plus the pytest log tail, rather than a
model's prose explanation of failures — mitigated by including failing-test output in
the result file. To watch before integration: confirm every deterministic harness
check still passes end-to-end. Acceptance: stays Proposed until integrated into the
running workflow, governance artifacts updated, and the end-to-end regression passes.
Rollback: the integration lands as a single commit so it can be undone with one
git revert if the script misbehaves in the running workflow.


## Evidence
Calibration log, before/after entry dated 2026-10-29 (commit <fill in after you commit the log>).
Implementation commit 33e40ba. Unit tests: eval/test_deterministic_step.py, 6/6 passing in container.