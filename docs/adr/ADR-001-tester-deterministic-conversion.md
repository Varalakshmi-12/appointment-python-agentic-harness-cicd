# ADR-001: Convert the appt-tester step from agent to deterministic code

## Status
Proposed

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
- Convert to deterministic code. Preferred, pending integration. A script that
  invokes the test runner directly runs in well under a second, costs zero tokens,
  returns identical output for the same code, and resolves the instrumentation gap.
  Measured numbers recorded later this lesson.
- Give the agent a working test tool (e.g., a shell). Rejected. Granting a tester a
  general shell widens privilege far beyond "run tests" — the exact over-broad-grant
  anti-pattern the calibration log already documents (Implementer + delete_entry) —
  and keeps inference latency, variance, and governance overhead a structural check
  does not need.

## Consequences
Expected benefits: the tester gate actually completes; near-zero latency; zero token
cost; perfectly repeatable output; a reviewer can understand it by reading a few
lines. Known trade-off: the script returns a terse structured result instead of a
model's prose explanation of failures — mitigated by including failing-test names
and error output in the result. To watch before integration: confirm latency, cost,
and that every deterministic harness check still passes. Acceptance: stays Proposed
until the script is wired into the running workflow, the governance artifacts are
updated, and the end-to-end regression passes.

## Evidence
Calibration log, Holdout gap #2 (appt-tester instrumentation gap), commit <fill in>.
Before/after measurement commits to be cited in the measurement section.