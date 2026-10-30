# Architecture Write-Up
## Governed Multi-Agent Engineering Pipeline for an Appointment-Scheduling App

**Author:** Chetan
**Date:** 2026-10-30
**Delivery path:** Job-seeker / no-deployment (representative engineering workflow)
**Target codebase:** appointment-scheduling app (Flask + MySQL backend, React frontend)

---

## 1. Overview

This system takes a reported backend issue and drives it to a reviewed, tested
change through a team of specialized AI agents, deterministic code, and human
checkpoints — all inside a sandboxed, governed, observable pipeline.

The design goal is not "use agents everywhere." It is **right-sized authority**:
each step is handled by an agent, deterministic code, or a human, depending on
whether it needs judgment, a repeatable rule, or accountability. Every agent runs
under least-privilege permissions enforced in code, every action is audited, and
the governance itself is protected by CI checks that cannot be silently removed.

**End-to-end flow (happy path):**
Human reports an issue → Orchestrator decomposes it → Planner writes an ordered
fix plan → *(human approves the plan)* → Implementer writes the code → Reviewer
flags problems → deterministic Test step runs the suite → Project Manager drafts
the PR summary → *(human confirms before finalizing)* → run summary written.

---

## 2. System components

- **Containerized harness.** The whole system runs in a Docker container
  (`agentic_engineer_4`) with explicit boundaries: the workspace is mounted
  **read-only** for roles that should not write, the memory volume is **omitted**
  for roles that should not persist state, and the container runs with **no network
  egress** for agent work. This keeps agents from clobbering the host or leaking
  secrets.
- **Agents and subagents.** A parent **Orchestrator** coordinates scoped subagents
  (Planner, Implementer, Reviewer, Tester, Project Manager, Dependency-Auditor).
  Each is a versioned definition with its own tool grants and autonomy level.
- **MCP-backed storage.** A FastMCP **storage server** exposes record operations
  (`write_entry`, `read_entry`, `list_entries`, `update_entry`, `delete_entry`,
  `audit_read`) over stdio, with per-role authorization and JSON-Lines audit logging.
- **MCP-backed retrieval.** A **retrieval server** exposes `retrieve` over a
  reference corpus, with a per-role **classification ceiling** (internal /
  confidential) so an agent can only see documents up to its clearance.
- **Persistent memory.** A versioned memory layout carries prior lessons and
  decisions between runs; agents read it as context, and write is tightly scoped.
- **CI/CD pipeline.** A GitHub Actions workflow enforces governance and evaluation
  on every change (Section 7).

---

## 3. Agent roles and scoped permissions

Permissions follow least-privilege: every role starts with no access and is granted
only what its job requires. (Full matrix in `docs/governance-policy.md` and
`docs/routing-and-tool-grant-map.md`.)

| Role | Purpose | Storage access | Retrieval ceiling | Autonomy |
|---|---|---|---|---|
| Orchestrator | Coordinate, evaluate, route, escalate | read/write/update/delete + audit_read | confidential | medium (human-gated) |
| Planner | Turn the issue into an ordered fix plan | read-only (plan carries prior lessons) | internal | high (read), human-gated plan |
| Implementer | Write the code per the plan | `write_entry` only | internal | medium |
| Reviewer | Flag problems; edits nothing | read / list only | internal | high (read); never writes |
| Tester | Run tests, report pass/fail | **converted to deterministic code** | n/a | n/a (now a script) |
| Project Manager | Draft PR summary / ticket | read / list only | denied | medium |
| Dependency-Auditor | Read-only dependency audit | read / list only | internal | low |

The **Reviewer** is deliberately read-only — a review role that can change state could
quietly alter the work it is meant to inspect. The **Project Manager's** ticket tool
is isolated to that role so it stays out of every other agent's context.

---

## 4. Data flow and handoffs

1. **Human → Orchestrator:** issue text + repo path.
2. **Orchestrator → Planner:** issue + read-only code. Planner returns an ordered
   plan + file list.
3. **Human checkpoint:** the Orchestrator HALTS and presents the plan for approval
   before any code is written. It does not proceed on a timeout.
4. **Orchestrator → Implementer:** plan + file list. Implementer returns modified
   files (editing only the files the plan names).
5. **Orchestrator → Reviewer:** modified files. Reviewer returns a review report;
   a Critical finding loops back to the Implementer.
6. **Deterministic Test step:** the Orchestrator runs
   `scripts/run_tests_deterministic.py`, reads `result.json`, and loops back to the
   Implementer if the status is not `pass` (Section 5).
7. **Orchestrator → Project Manager:** the assembled result; PM drafts the PR summary.
8. **Human checkpoint:** HALT for explicit confirmation before finalizing.
9. **Output:** a run summary (what changed, review outcome, test outcome).

Handoffs are structured documents, so each step consumes a known shape — which is
what let the Tester be swapped for a script without changing anything downstream.

---

## 5. Right-tool decisions (agent vs deterministic vs human)

Each step was classified (`docs/step-classification.md`) against four signals —
stability, repeatability, specifiability, run rate — and placed in the column its
nature demands:

- **Agents** (judgment / synthesis): Orchestrator routing, Planner, Implementer,
  Reviewer. These need language understanding and reasoning across context.
- **Deterministic code** (structural, one correct answer): the governance checks
  (`forbidden_operations`, `tool_grants`, `audit_matches_writes`, `no_unknown_caller`),
  the policy test suite, and — after this project's conversion — the **Test step**.
  The Tester was converted from an agent to `scripts/run_tests_deterministic.py`,
  which runs the suite and classifies the result as **pass / fail / error**. The
  decision, evidence, and before/after are recorded in **ADR-001** and the
  calibration log. Benefits: zero token cost, deterministic verdict, and it fixed a
  step that was non-functional as an agent. (The three-state classification preserves
  the one judgment the agent used to apply — an un-runnable suite is an *error*, not
  a test *failure*.)
- **Humans** (accountability): plan approval before any code, and confirmation before
  finalizing — the decisions consequential enough to require a person.

A healthy pipeline has all three side by side; this one does.

---

## 6. MCP boundaries and least-privilege enforcement

Governance is enforced in **two independent layers** (defense in depth), not a
document alone:

- **Layer 1 — container.** Read-only workspace mount, omitted memory volume, and no
  network egress, scoped per role at launch via `AGENT_ROLE`.
- **Layer 2 — MCP allow-lists.** Every storage/retrieval operation passes an
  `_authorize()` check against a per-role allow-list; an ungranted call raises a
  `ToolError` (the stdio equivalent of HTTP 403) and is written to the audit log as
  `authorization_denied`. Retrieval additionally enforces a classification ceiling
  per role.

Because the two layers have independent sources of truth, a mistake that blinds one
is caught by the other. This was demonstrated in practice: when the Implementer was
accidentally granted `delete_entry`, the grant-map check passed but the independent
audit-log policy (`forbidden_operations`) caught the violation (see the tool-evolution
drill and calibration log, 2026-09-29).

---

## 7. CI/CD governance integration

A GitHub Actions pipeline runs governance and evaluation automatically on every
change, so the controls cannot be quietly skipped:

- **Change Classifier** — decides which files changed; sets outputs; never blocks.
- **Policy Test Suite** (gating) — verifies the enforced code still matches the
  written governance policy.
- **Governed File Check / Evaluation** (gating, on agent-affecting changes) — runs
  the harness so a change can't silently degrade agent behavior.
- **Pipeline Integrity Check** (gating) — inspects the workflow file itself and
  fails if a gate was demoted, the classifier removed, or the audit trail disabled —
  so the guardrails can't be weakened in the same PR they're meant to evaluate.
- **Advisory Code Review** (advisory) — an AI reviewer posts a PR comment but never
  blocks; it starts advisory and must earn the right to gate by showing a low
  false-positive rate.
- **Audit Trail** (observational, `if: always()`) — combines every job's output into
  one durable record, even from jobs that failed.

Gating checks are marked **required status checks** in branch protection, so a red
check blocks the merge button. Secrets (the model API key) live in the CI secret
store, are injected only into the steps that call the model, and are never logged —
the same least-privilege discipline applied to credentials.

---

## 8. Where governance is enforced (not just described)

| Control | Enforced in |
|---|---|
| Role → tool access | MCP allow-lists + `_authorize()` guard |
| Data classification | retrieval ceiling per role |
| Filesystem / network / memory | container mount + network config per `AGENT_ROLE` |
| Policy ↔ code consistency | `eval/test_policy.py`, gated in CI |
| No weakened guardrails | Pipeline Integrity Check, gated in CI |
| Secrets | CI secret store, step-scoped injection |
| Human accountability | Orchestrator HALT checkpoints |

A written policy alone is insufficient; every row above is connected to code,
configuration, or a CI check.

---

## 9. Observability and audit

Every tool call, authorization decision, denial, and human approval is logged. The
storage server writes JSON-Lines audit records; the CI audit-trail job assembles
policy results, evaluation results, agent actions, and denials into one reviewable
artifact per run. A reviewer — or an auditor months later — can answer "what did the
agent touch, and did anything get blocked?" without rerunning anything.

---

## 10. Known limitations (recorded, not hidden)

- **`calling_role: "unknown"` attribution gap.** Real runs can log an unknown caller,
  so the audit-log role attribution `forbidden_operations` relies on is not fully
  trustworthy on live runs. Named fix: require a valid `calling_role` at the storage
  enforcement point.
- **Shared-process role.** In-session subagents share one MCP server process, so the
  server sees a single `AGENT_ROLE`; per-role least-privilege is not fully enforced
  within a single session.
- **Retrieval zero-score fallback.** On a query matching nothing, the retrieval stub
  returned top-k documents anyway (up to the role's ceiling) — a search miss could
  become a classification leak. Recorded as a near-miss.

These are tracked in the calibration log and near-miss notes. Documenting them is part
of the self-improving loop: the system is trustworthy because its gaps are known and
named, not because they are assumed absent.

---

## Appendix: key artifacts
- `docs/governance-policy.md`, `docs/routing-and-tool-grant-map.md` — role→tool matrix
- `docs/orchestration-diagram.md` — the workflow
- `docs/step-classification.md` — agent/deterministic/human decisions
- `docs/adr/ADR-001-...md` — the deterministic conversion decision
- `docs/calibration-log.md` — evidence (before/after, near-misses)
- `docs/tool-evolution-drill.md` — change-under-governance evidence
- `.github/workflows/ci.yml` — the governed pipeline
- `mcp-servers/storage`, `mcp-servers/retrieval` — MCP enforcement points
- `scripts/run_tests_deterministic.py` — the converted Test step