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


  
  # Step-Classification — Lesson 4.3 addition


## Step under review: backend import / compile check

### What the step currently does
The import/compile check runs `python -m py_compile` on each file in the Flask backend
(excluding venv) and imports the app module, then reports per-file pass/fail and an explicit
recommendation on whether the backend is runnable. It is a pre-flight/baseline check that
runs before deeper work proceeds. Input: the backend source tree. Output: a per-file
pass/fail report plus a runnable / not-runnable recommendation.

### Four-signal classification

| Signal | Score | Evidence |
|---|---|---|
| **Stability** | High (operation is deterministic) | The operation depends only on the code state — `py_compile`/import give the same result for the same input. Baseline run scored 4/4 on Check Execution Accuracy with real per-file results including an exact traceback (Iteration Log, Run 001, Task B, 2026-08-17). *A formal across-reruns variance check is still to gather — one baseline run, not many — but the operation's determinism makes high stability the expected result.* |
| **Repeatability** | High | The same procedure runs identically every time: compile each file, import the app module, report per-file pass/fail. Task B ran it across all three backend files with per-file results (Iteration Log, Run 001, Task B). |
| **Specifiability** | High — the confirming signal | The step is already written as a deterministic procedure in its own prompt: `python -m py_compile` on each file, then import the app module, then report. There is no open-ended reasoning in the core operation. |
| **Run rate** | Moderate — the soft signal | Ran as a Module 1 baseline task; structurally it is a per-change pre-flight gate. *Honest note: the log shows one baseline run, so "runs on every change" is the intended cadence, not yet a measured frequency — confirm before converting so the script is worth maintaining.* |

### Known agent judgment / edge-case input
**An incidental import failure in a standalone/test script that does not affect app
runnability.** In the baseline run, `test_sms.py` failed to import because it fires a live
Twilio API call at module import time (unconditionally, no credentials). The agent judged
that this did **not** make the backend unrunnable — it distinguished `app.py` importing
cleanly from a standalone test script failing at import (Iteration Log, Run 001, Task B).
A deterministic version must preserve that distinction; it is not a fifth signal and does
not change the recommendation — it names what to protect.

### Recommendation: **Strong candidate**
The step passes stability, repeatability, and specifiability clearly, and it has a measured
baseline ($0.26/run, 372,900 in / 3,700 out, 8-minute review, 16/16) proving an agent is
being paid to run a mechanical procedure. Run rate is the one soft signal — it was a
baseline task, so I would confirm it runs often enough to justify a maintained script
before converting. The conversion is a small script (`py_compile` over the tree + a
targeted import of the app module) that must encode one rule: classify the app module's
runnability separately from incidental import failures in standalone/test scripts. The
recommendation follows from the specifiability of the operation and the measured cost of
running it agentically, not from hoped-for savings.

---

## Plan for tests, measurements, and rollback (for the deterministic replacement)

### Test plan (≥3 unit tests)
1. **Normal / success** — Input: a backend where every file compiles and the app module
   imports. Expected: all `PASS`, verdict "backend runnable," exit 0. *Why it matters:*
   confirms the check doesn't false-positive on a clean tree and lets legitimate work
   proceed.
2. **Invalid / failure** — Input: `app.py` with a syntax error (so `py_compile` fails).
   Expected: `FAIL` on `app.py` with the error, verdict "backend NOT runnable." *Why it
   matters:* a real app-module breakage is the core failure this check exists to catch and
   must block.
3. **Edge case (the `test_sms.py` judgment)** — Input: `app.py` imports cleanly but
   `test_sms.py` raises at import (live Twilio call at module load). Expected: `test_sms.py`
   reported as a failed import **but overall verdict = "backend runnable,"** with the
   failure marked non-blocking. *Why it matters:* this protects the exact judgment the agent
   made. A bug here — letting any import failure flip the runnability verdict — would
   wrongly report the backend as broken on every run. The test asserts the app-vs-script
   distinction, so it can't be silently lost.

### Measurement plan (before vs after)
- **Latency** — ~1m16s cycle + 8-min review (baseline) vs script wall-clock (seconds).
- **Token cost** — $0.26/run (372,900 in / 3,700 out) → ~$0 (no model call).
- **Predictability** — byte-identical per-file pass/fail across reruns vs agent prose.
- **Audit clarity** — structured per-file results vs a prose report.
- **Quality / harness** — does the script still return "backend runnable" on the
  `test_sms.py` case, and still block on a real `app.py` breakage? This is the regression to
  watch.
- **Rubric note:** the baseline scored prose dimensions (Error Reporting Clarity,
  Recommendation Quality). If the script emits structured output instead of prose, those
  dimensions may become **N/A** for the converted step — record this so a lower total isn't
  later misread as a regression.

### Rollback note
Ship as a **single, focused commit** that: (a) adds the import-check script + its tests,
(b) wires the orchestrator to run it at the pre-flight point, (c) adds the routing-map row,
(d) adds the governance-policy entry, (e) adds the CI step. Reverting is `git revert <sha>`,
restoring the prior path with no change to unrelated work. Because the check was a baseline
task rather than a standing subagent, the rollback mainly removes the new wiring; if a
dedicated agent artifact is created for it, retire that in the same commit so the revert is
clean.