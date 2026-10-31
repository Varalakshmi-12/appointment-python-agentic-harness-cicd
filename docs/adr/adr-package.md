# ADR Package

Architecture Decision Records for the governed multi-agent engineering pipeline
(appointment-app). Each record captures one durable decision, the alternatives
rejected with evidence, consequences, and open risks.

- **ADR-001** — Convert the Test step from agent to deterministic code.
  (Full record in `docs/adr/ADR-001-tester-deterministic-conversion.md`; summarized
  at the end of this package.) Status: **Accepted**.
- **ADR-002** — Quality rubric design.
- **ADR-003** — Persistent memory layout.
- **ADR-004** — MCP tool boundaries.
- **ADR-005** — Subagent scoping and routing.
- **ADR-006** — Governance policy and two-layer enforcement.

---

# ADR-002: Multi-dimensional, threshold-gated quality rubric

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

# ADR-003: Persistent memory layout with scoped write

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

# ADR-004: Expose capabilities only through governed MCP tool boundaries

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

# ADR-005: Orchestrated, least-privilege subagent scoping and routing

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

# ADR-006: Least-privilege governance with two-layer enforcement in code

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
(see ADR-001).

## Evidence
`docs/governance-policy.md`; the CI governed pipeline and Pipeline Integrity Check
(with its deliberate-weakening verification); calibration log 2026-09-29.

## Open risks
Governance machinery is costly to maintain; the `calling_role: "unknown"` gap weakens
audit-based enforcement on live runs until the storage server requires a valid caller.

---

# ADR-001 (summary — full record in docs/adr/)

## Status
Accepted

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