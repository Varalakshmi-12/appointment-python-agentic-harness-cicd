# Workflow Step Classification

Audit of every step in the Orchestrator-coordinated subagent workflow
(illustrated with the "Add CSV Export" feature run). Each agentic step is
assessed against the four signals — stability, repeatability, specifiability,
run rate — with a recommendation of: strong candidate, weak candidate,
not a candidate, or already deterministic.

---

## Step: Orchestrator (coordinate + evaluate + route)
- Stability: N/A — behavior depends on every subagent's output; not a fixed rule.
- Repeatability: No — routing/escalation decisions vary with context.
- Specifiability: No — "evaluate each result and decide what happens next" is
  open-ended judgment that cannot be fully written down.
- Run rate: Every workflow invocation.
- Known agent judgment / edge case to preserve: must weigh partial or ambiguous
  subagent results and decide continue / revise / escalate.
- Recommendation: not a candidate (requires judgment).
- Note: one sub-decision inside it IS deterministic — "if Tester reports fail
  (or Reviewer reports blocking problems) -> route back to Implementer." That
  routing condition could be extracted to code even though the Orchestrator
  overall stays agentic.

## Step: Planner (ordered plan + file list)
- Stability: N/A — output is a synthesized plan, not a fixed transformation.
- Repeatability: No — same request can yield different valid plans.
- Specifiability: No — turning a feature request into an ordered plan requires
  judgment and reasoning across the codebase.
- Run rate: Every workflow invocation.
- Known agent judgment / edge case to preserve: ambiguous or underspecified
  feature requests; choosing which files to touch.
- Recommendation: not a candidate (requires judgment).

## Step: Implementer (write code per plan)
- Stability: N/A — generative code authoring.
- Repeatability: No — many valid implementations of the same plan.
- Specifiability: No — writing code is open-ended synthesis.
- Run rate: Every workflow invocation (plus each revision loop).
- Known agent judgment / edge case to preserve: adapting the plan when the code
  doesn't match expectations.
- Recommendation: not a candidate (requires judgment).

## Step: Reviewer (flag problems, edits nothing)
- Stability: N/A — quality judgment, not a fixed check.
- Repeatability: No — review findings vary; open-ended assessment.
- Specifiability: No — "is this code good?" cannot be specified exactly; the
  criteria are contextual.
- Run rate: Every workflow invocation.
- Known agent judgment / edge case to preserve: catching subtle design issues a
  rule-based linter would miss.
- Recommendation: not a candidate (requires judgment).

## Step: Tester (run tests, report pass/fail)   <-- STRONG CANDIDATE
- Stability: a test runner is deterministic by nature. The agentic Tester
  cannot be scored by running it: calibration log Holdout gap #2 records that
  appt-tester has no working test tool in this environment (coursetools
  test_runner missing, Bash disallowed), so the pipeline halts at the tester
  gate. The behavior being converted — a test runner's pass/fail — is fully
  understood and deterministic, so no unstable behavior is being frozen.
- Repeatability: pytest on fixed code is deterministic by construction.
- Specifiability: yes. Spec: run the project's test command (pytest); exit 0
  -> pass, exit 1 -> fail, any other exit (interrupted / internal error /
  usage error / no tests collected) -> error. Return a structured result. A
  developer could implement this from the spec alone.
- Run rate: every feature run AND every revision loop — many times per day.
- Known agent judgment / edge-case input the deterministic version must preserve:
  THREE outcome states, not two — pass, fail (tests ran, some failed), and
  error (the suite could not run: import error, missing dependency, no tests
  collected). A naive "exit code == 0 else fail" check would mislabel an error
  as a failure. Also flaky tests.
- Recommendation: strong candidate. Converting the pass/fail determination to
  deterministic code removes token cost, variance, and transcript debugging
  from a step that runs on every loop, AND resolves the tester-gate
  instrumentation gap (the agentic step cannot run at all here).

## Step: Project Manager (update ticket status)
- Stability: the status mapping is fixed if the rule is agreed.
- Repeatability: yes — same result -> same status under a fixed mapping.
- Specifiability: yes IF the status logic is a simple mapping (approved +
  tests passed -> Done; tests failed -> Blocked).
- Run rate: ~once per feature — LOW. Limits the cost/latency savings.
- Known agent judgment / edge case to preserve: results that don't map cleanly
  to a status (partial completion, human requested changes).
- Recommendation: weak candidate — deterministic-friendly (a structural ticket
  write), but low run rate means small savings; not the priority.

## Step: Human checkpoint (evaluate / approve)
- Recommendation: not a candidate — intentionally a human. Accountability before
  the run is finalized and before the shared ticket record is written is the
  "use a human" column of the decision matrix.

---

## Summary
- Steps assessed: 7
- Strong candidates: 1 (Tester)
- Weak candidates: 1 (Project Manager)
- Not candidates: 5 (Orchestrator, Planner, Implementer, Reviewer, Human checkpoint)
- Already deterministic (for reference): the governance checks the harness runs
  (forbidden_operations, tool_grants, audit_matches_writes, no_unknown_caller)
  are already code, not agents.
- Chosen candidate to carry into the ADR: **Tester — convert the pass/fail
  determination to deterministic code.**