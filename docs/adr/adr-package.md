# ADR Package

**Author:** Varalakshmi

Architecture Decision Records for the governed multi-agent engineering pipeline
(appointment-app). Each record captures one durable decision, the alternatives
rejected with evidence, consequences, and open risks.

- **ADR-001** — Convert the Test step from agent to deterministic code.
  (Full record in `docs/adr/ADR-001-tester-deterministic-conversion.md`; summarized
  at the end of this package.) Status: **Accepted** — implemented and measured.
- **ADR-002** — Convert the backend import/compile check from agent to deterministic
  code. (Full record in `docs/adr/ADR-002-import-check-deterministic-conversion.md`;
  summarized at the end.) Status: **Proposed** — a right-tool readiness analysis;
  not yet implemented, so no after-numbers are claimed.
- **ADR-003** — Quality rubric design.
- **ADR-004** — Persistent memory layout.
- **ADR-005** — MCP tool boundaries.
- **ADR-006** — Subagent scoping and routing.
- **ADR-007** — Governance policy and two-layer enforcement.

> Two conversions are recorded at different maturity: **ADR-001** is an *implemented,
> measured* agent-to-deterministic conversion (the required one); **ADR-002** is a
> *proposed* conversion documented at decision time, before any code exists.

---

# ADR-003: Multi-dimensional, threshold-gated quality rubric

## Status
Accepted

## Context
Agent output quality had to be measured objectively and reproducibly, not judged by
impression. In Module 1 each task was scored on four dimensions (1–4) with a pass
floor of 3+ on every dimension, so a run could not pass by excelling on one dimension
while failing another.

## Decision
Score agent output on a small set of task-specific dimensions (1–4 each) with a hard
floor of 3+ on **every** dimension; deterministic checks act as the pass/fail gate,
and the rubric scores quality above that floor. A rubric-scored run is only meaningful
when the deterministic floor passes.

## Alternatives considered
- **Single human pass/fail.** Rejected — not reproducible and slow: baseline review
  latency was 8 minutes per run (iteration log, Run 001 A/B).
- **One aggregate numeric score.** Rejected — an aggregate hides a single failing
  dimension (e.g. "accurate but unreadable"). A per-dimension floor prevents trading
  safety or correctness for polish. Evidence: baseline runs scored 16/16 across four
  dimensions each with explicit per-dimension notes; the per-dimension structure is
  what lets a later regression fail on exactly one dimension instead of being averaged
  away.

## Consequences
A reproducible, auditable quality signal that can gate a release. Costs: rubric
authoring is upfront work, and using a model as judge introduces its own run-to-run
variance, which is why rubric checks start advisory and deterministic checks gate.

## Evidence
`docs/iteration-log.md`, Run 001 Task A (16/16) and Task B (16/16), with per-dimension
scoring notes and the 8-minute review-latency measurement.

## Open risks
Agent-as-judge variance; rubric dimensions tuned for one task type may not generalize,
requiring per-task rubrics.

---

# ADR-004: Persistent memory layout with scoped write

## Status
Accepted

## Context
Agents benefit from prior lessons and decisions across runs, but unrestricted memory
write is a governance risk and re-deriving context every run is expensive.

## Decision
Use a versioned persistent memory layout: agents read prior lessons/decisions as
context, and write access is tightly scoped per role (e.g. the Implementer may record
exactly one lesson per run via `write_entry` with `project_id=proj-lessons`,
`classification=internal`, and has no read/list/update/delete or retrieval access —
the plan it receives already carries the relevant prior lessons).

## Alternatives considered
- **Prompt-stuff all history each run.** Rejected on cost: baseline runs already
  consumed ~320k–370k input tokens at $0.23–$0.26 each (iteration log); carrying full
  history in-prompt would compound that and bloat context.
- **Give every agent full read/write memory.** Rejected — violates least-privilege;
  an agent could rewrite or delete shared history. Scoped, append-oriented writes keep
  the memory surface small and auditable.

## Consequences
Durable context with a bounded, auditable write surface. Cost: memory must be curated
to avoid drift, and the layout must be versioned alongside the code.

## Evidence
Baseline token costs and per-run dollar figures (iteration log, Run 001 A/B); the
Implementer's scoped single-lesson write grant in the agent definition and policy.

## Open risks
Memory staleness; the shared-process role near-miss means per-role memory scoping is
not fully enforced within a single session (recorded in the calibration log).

---

# ADR-005: Expose capabilities only through governed MCP tool boundaries

## Status
Accepted

## Context
Agents need to read/write records and retrieve reference documents, but must not be
able to exceed their role, and every access must be auditable.

## Decision
Expose all such capability only through MCP servers (storage, retrieval). Every
operation passes an `_authorize()` guard against a per-role allow-list; an ungranted
call raises `ToolError` (stdio equivalent of HTTP 403) and is written to the audit log
as `authorization_denied`. Retrieval additionally enforces a per-role classification
ceiling (internal / confidential).

## Alternatives considered
- **Direct database / filesystem access from agents.** Rejected — no single
  enforcement point and no audit; a mistake is unbounded and invisible.
- **One shared tool set for all agents.** Rejected — no least-privilege. Demonstrated
  concretely: when the Implementer was accidentally granted `delete_entry`, the
  independent, audit-log-backed `forbidden_operations` check caught the violation
  (13/14 deterministic) even though the grant-map check passed — because enforcement
  is per-operation and audited. Evidence: calibration log, 2026-09-29.

## Consequences
A single enforcement-and-audit point per capability, enabling least-privilege and a
full action record. Cost: a bug in the server (e.g. the retrieval zero-score fallback)
can itself become a leak, so the servers need their own tests.

## Evidence
Calibration log 2026-09-29 (over-broad-grant catch, 13/14 → 14/14 after fix, HO-06
generalization); retrieval zero-score-fallback near-miss note.

## Open risks
The retrieval zero-score fallback (a search miss could return a confidential doc up to
the ceiling); the `calling_role: "unknown"` attribution gap undermines audit-based
enforcement on live runs. Both have named fixes.

---

# ADR-006: Orchestrated, least-privilege subagent scoping and routing

## Status
Accepted

## Context
A single general-purpose agent with broad access is hard to govern, audit, and reason
about. Responsibilities needed to be separated so each could be scoped and traced.

## Decision
An Orchestrator delegates to specialized subagents — Planner, Implementer, Reviewer,
Test step (now deterministic), Project Manager, Dependency-Auditor — each scoped to
only the tools its job requires. Routing follows a standard sequence with branching
(loop back to the Implementer on a Critical review finding or a non-pass test; halt and
escalate after the same phase fails twice) and mandatory human checkpoints (plan
approval; final confirmation).

## Alternatives considered
- **One generalist agent.** Rejected — no least-privilege and no way to attribute an
  action to a responsibility; the whole blast radius is one role.
- **Fully autonomous orchestration with no human gates.** Rejected — delegation is
  irreversible once code is written, so human gates bound the blast radius. The PM's
  ticket tool is isolated to its role specifically to prevent premature ticket changes
  from other agents' contexts.

## Consequences
Clear responsibility boundaries, least-privilege per role, and auditable handoffs.
Cost: coordination overhead and more artifacts (agent definitions, routing map,
policy) that must be kept in sync — which the CI policy test enforces.

## Evidence
`docs/orchestration-diagram.md`; `docs/routing-and-tool-grant-map.md`; the orchestrator's
max-iteration guard (halt + escalate after two failures) and human checkpoints.

## Open risks
Shared-process role gap (in-session subagents share one `AGENT_ROLE`, so per-role
least-privilege is not fully enforced within a session); coordination complexity grows
with each added role.

---

# ADR-007: Least-privilege governance with two-layer enforcement in code

## Status
Accepted

## Context
A written governance policy enforces nothing on its own. Controls had to be enforced
in code and configuration, and protected from being quietly disabled.

## Decision
Adopt least-privilege defaults (every role starts with no access; access is granted
with written justification and removed when no longer needed) enforced in **two
independent layers**: the container (read-only mount, omitted memory, no network
egress, per `AGENT_ROLE`) and the MCP allow-lists plus classification ceilings. Back
this with audit logging and CI gating — a policy test suite, an evaluation gate, and a
Pipeline Integrity Check — marked as required status checks so a red check blocks a
merge.

## Alternatives considered
- **Policy document only.** Rejected — unenforced, and the capstone/rubric explicitly
  requires governance connected to tool grants, container permissions, MCP allow-lists,
  CI checks, or audit logs.
- **A single enforcement layer.** Rejected — a single point of failure. Demonstrated:
  the grant-map check passed while the independent audit-log check (`forbidden_operations`)
  caught the `delete_entry` over-reach — defense in depth with independent sources of
  truth. Evidence: calibration log, 2026-09-29.

## Consequences
Enforceable, auditable, self-protecting governance (even an attempt to weaken a gate is
caught by the Pipeline Integrity Check and blocked). Cost: governance overhead — each
agentic step needs a policy entry, an allow-list, audit coverage, and an eval slot,
which is itself a standing reason to convert stable steps to deterministic code
(see ADR-001 and ADR-002).

## Evidence
`docs/governance-policy.md`; the CI governed pipeline and Pipeline Integrity Check
(with its deliberate-weakening verification); calibration log 2026-09-29.

## Open risks
Governance machinery is costly to maintain; the `calling_role: "unknown"` gap weakens
audit-based enforcement on live runs until the storage server requires a valid caller.

---

# ADR-001 (summary — full record in docs/adr/)

## Status
Accepted — implemented and measured

## Decision
Convert the `appt-tester` step from an agent to `scripts/run_tests_deterministic.py`,
which runs the test suite and classifies the result as pass / fail / error.

## Why (evidence-backed)
The agentic tester was non-functional (no test tool; pipeline halted at the tester
gate). The deterministic script runs in ~2.3s wall-clock at $0 token cost with an
identical verdict across runs, and preserves the one judgment the agent applied (an
un-runnable suite is an *error*, not a *failure* — a three-state distinction pinned by
unit tests). Rejected alternatives: keep the agent (non-functional, costs tokens and
variance for a structural task); give the agent a shell (over-broad-grant anti-pattern,
the exact failure mode caught in the 2026-09-29 calibration entry).

## Consequences
Lower latency, zero token cost, deterministic output, the tester gate unblocked;
trade-off is a terse structured verdict instead of prose. Integrated as one revertible
commit; ADR accepted after an end-to-end regression (11/11 local + CI green).

## Open risks
If the test-pass/fail rule ever needs judgment (e.g. tolerating known-flaky tests),
the step may need enrichment in code before any return to an agent.

---

# ADR-002 (summary — full record in docs/adr/)

## Status
Proposed — readiness analysis, not yet implemented

## Decision
Replace the backend import/compile-check agent (`appt-import-checker`) with a
deterministic script that compiles every backend file, imports the app module, reports
per-file pass/fail, and classifies the app module's runnability separately from
incidental import failures in standalone/test scripts.

## Why (evidence-backed)
Iteration Log Run 001 Task B shows an agent performing a fully specified procedure
(`py_compile` + import) at 16/16 quality but $0.26/run and 8 minutes of review — model
cost and latency for a mechanical check. The one judgment it applied (treating
`test_sms.py`'s live-Twilio-at-import failure as non-blocking for backend runnability)
is itself expressible as an explicit rule. Rejected alternatives: keep it fully agentic
(pays for a specified procedure); a naive "any import fails → not runnable" check
(would wrongly report the backend broken on every run). The record stays Proposed
because no replacement has been built or measured — inventing after-numbers would
defeat the purpose.

## Consequences (expected)
Near-zero cost, seconds not minutes, byte-identical verdict, structured audit output;
cost is an exclusion rule for incidental import failures that must be kept correct as
the test suite grows.

## Open risks
The exclusion rule could hide a real import regression in a test file; the "incidental"
set needs periodic review.

---

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
- Convert to deterministic code. Preferred and adopted. The after-conversion
  calibration-log entry (`docs/calibration-log.md`) shows the script runs in ~2.3s
  wall-clock (~0.18s of actual pytest execution) at $0 token cost, produced an
  identical verdict on all three runs (the only diff was pytest's embedded timing
  string, not a decision), and passes 6/6 unit tests including the three-state
  pass/fail/error limitation. It also resolves the tester-gate instrumentation gap
  (the agentic step could not run at all). It was integrated into the running workflow
  (`scripts/run_tests_deterministic.py`); the end-to-end regression passed, so the ADR is
  now **Accepted** (see Status).
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
the result file. Integration check: every deterministic harness check still passes
end-to-end. Acceptance: met — integrated into the running workflow, governance artifacts
updated, and the end-to-end regression passed.
Rollback: the integration lands as a single commit so it can be undone with one
git revert if the script misbehaves in the running workflow.


## Evidence
Calibration log, before/after entry dated 2026-10-29 (`docs/calibration-log.md`).
Implementation: `scripts/run_tests_deterministic.py`. Unit tests: `eval/test_deterministic_step.py`, 6/6 passing in container.

---

# ADR-001: Convert JSON schema validation step from agent to deterministic code

## Status

Accepted

## Context

The orchestration includes a step that validates each handoff document against `schemas/handoff.json` before the next subagent consumes it. The step-classification document marks it a strong candidate on all four signals: stable harness scores, identical output on repeated runs, a specification a developer can implement directly, and a run on every workflow invocation. The classification also names the edge case the deterministic version must preserve: a required field that is present but blank must be treated as invalid, not accepted just because the key exists.

## Decision

Replace the agentic validation step with a small script that checks the handoff document against `schemas/handoff.json` and rejects it with a clear error if any required field is missing, null, or empty.

## Alternatives considered

- Keep the agentic step. Rejected. The calibration log before-conversion entry shows this step averaged 45 seconds of cycle time and $0.003 in token cost per run across three runs, while passing all 7 deterministic harness checks. It contributes no language understanding the task requires.
- Convert to deterministic code. Accepted after integration. The after-conversion entry shows the script averaged 0.2 seconds and $0 token cost across three runs, produced identical output on all three, and passed the same 7 deterministic checks with no regression.
- Shrink the agent with a tighter prompt and a smaller model. Rejected. It lowers token cost but keeps inference latency, output variance, and governance overhead.

## Consequences

Cycle time fell from 45 seconds to 0.2 seconds, token cost fell from $0.003 per run to zero, and output variance fell to zero. Known trade-off: the script returns a terse structured result rather than a generated prose explanation. If the structured problem list proves too thin for debugging, enrich the deterministic messages before considering a return to an agent.

## Evidence

- Classification: `docs/step-classification.md`, JSON schema validation marked strong candidate.
- Before-conversion measurement: `docs/calibration-log.md`, before-conversion entry.
- After-conversion measurement in isolation: `docs/calibration-log.md`, after-conversion entry.
- Integrated end-to-end regression check: `docs/calibration-log.md`, integrated end-to-end regression check.


---

# ADR-002: Convert the backend import/compile check from an agent to deterministic code

## Status
**Proposed** — nothing has been built, measured, or merged. The measured after-conversion
comparison belongs to an implementation this exercise deliberately does not reach, so no
after numbers are claimed here.

## Context
The backend import/compile check runs `python -m py_compile` on each file in the Flask
backend and imports the app module to confirm the backend is runnable. The Iteration Log
(Run 001, Task B, 2026-08-17) shows an agent performing this with 16/16 quality at $0.26
per run (372,900 tokens in / 3,700 out) and 8 minutes of review latency — model cost and
review time spent on a procedure that is already fully specified in its own prompt. The one
piece of judgment the agent applied was distinguishing the app module's runnability from an
incidental import failure in a standalone test script: `test_sms.py` fails to import because
it fires a live Twilio call at module load, and the agent correctly judged the backend still
runnable.

## Decision
Replace the agent with a deterministic script that compiles every backend file, imports the
app module, reports per-file pass/fail, and classifies the app module's runnability
separately from incidental import failures in standalone/test scripts. Status remains
Proposed; no replacement has been written and no after numbers are claimed.

## Alternatives considered
1. **Keep the step fully agentic.** Rejected — it pays $0.26 and ~8 minutes of review per
   run for a procedure already expressed deterministically in the prompt (`py_compile` +
   import). The only judgment involved (the test-script distinction) is itself expressible
   as an explicit rule. Evidence: Iteration Log, Run 001, Task B measurements and the
   documented `test_sms.py` judgment.
2. **Naive deterministic check: import every file; any failure → "not runnable."**
   Rejected — this would report the backend as not runnable whenever a standalone script
   such as `test_sms.py` fails at import, repeating the wrong verdict on every run. Evidence:
   Iteration Log, Run 001, Task B, where the agent explicitly avoided exactly this error.
3. **(Chosen) Deterministic script that preserves the app-vs-standalone-script distinction.**
   Captures the cost and predictability win while encoding the one judgment that matters.

## Consequences
Near-zero cost, seconds instead of minutes, byte-identical verdict, and structured audit
output. Costs: the script must carry an explicit exclusion rule for incidental import
failures, and that rule must be kept correct as the test suite grows — too broad and it
hides a real import regression, too narrow and it flips the verdict on scripts like
`test_sms.py`.

## Evidence
- Iteration Log, Run 001, Task B (2026-08-17): 16/16; cost $0.26 (372,900 in / 3,700 out);
  cycle ~1m16s; review 8 min; the `test_sms.py` live-Twilio-at-import finding and the
  agent's runnable judgment. The baseline is measured; the after-conversion numbers are not
  — which is why this record stays Proposed.
- **To gather (would settle keep-vs-convert):** an across-reruns variance check confirming
  the step's output is stable run to run, and the real run frequency confirming the
  conversion is worth maintaining.

## Open risks
The exclusion rule for incidental import failures could hide a genuine import regression in
a test file; the set of "incidental" failures may need periodic review as the suite changes.

---

# ADR-002: Convert path-based routing step from agent to deterministic code

## Status

Proposed

## Context

The workflow contains a routing step that assigns work to a role based on changed file paths. The decision is structural: files under `tests/` go to the tester, files under `docs/` go to documentation/project-management work, and source changes go to the implementer. The main edge case is an unmatched path.

## Decision

Replace the agentic routing step with `scripts/route_task_deterministic.py`, which applies explicit ordered path rules and defaults unmatched paths to `implementer`.

## Alternatives considered

- Keep the agentic router. Rejected for the sample because the behavior is a lookup table, not judgment.
- Convert to deterministic code. Preferred, pending integration and full measurement.
- Keep both router and agent as fallback. Rejected because that preserves cost and governance complexity for a structural operation.

## Related decisions

Builds on ADR-001. Two lessons from that conversion shaped this one: identify the input class an agent handled by judgment that a script might miss, and write a test for it; mark model-only rubric dimensions as not applicable rather than failures.

## Evidence

Pending measurement and integration.