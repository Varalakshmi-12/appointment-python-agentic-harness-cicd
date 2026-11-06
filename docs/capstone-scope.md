# Capstone Scope

**Author:** Varalakshmi

The single scope document for the capstone: what the workflow is, who it serves, how a run
is judged pass/fail, how it can fail, what the demo must show, and why a custom governed
multi-agent pipeline is the right tool rather than a prebuilt agent or a simpler automation.

## Workflow

**Governed implementation of a backend code change to the appointment-scheduling app**
(Flask + MySQL). The representative task used throughout is: *add input validation to the
appointment status-transition route* (`PATCH /appointments/<id>/status`). The pipeline
plans the change, implements it, security-reviews it, and runs the tests — with governance
and human checkpoints around every step.

**Delivery path:** job-seeker / no-deployment. The pipeline runs on the application's own
source and a representative internal-lessons corpus; no real customer or patient data is
used. In a real deployment the same controls (classification ceilings, audit logging,
approvals) would carry production data.

## Baseline pain (quantified)

The problem is not output quality — it is the **cost and burden around** each change.
Measured in Module 1 across two representative backend-check tasks (`docs/iteration-log.md`,
Run 001), the manual, un-governed workflow cost:

| Metric | Lint task | Import-check task |
|---|---|---|
| Quality (rubric) | 16/16 | 16/16 |
| **Human review latency** | **~8 min** | **~8 min** |
| Cycle time | ~1 min 16 s | ~1 min 16 s |
| **Cost per run** | **$0.23** (319.6k in / 3.1k out) | **$0.26** (372.9k in / 3.7k out) |

So the before-state is concrete and checkable: quality was already maxed, yet every change
still cost ~8 minutes of a human's review and ~$0.25 in tokens — including on mechanical
steps a human shouldn't need to review. That recurring review burden and spend is the pain
the governed pipeline is built to cut (by routing mechanical steps to deterministic code and
reserving human attention for judgment and the final checkpoint).

## Stakeholder, trigger, inputs, outputs

- **Stakeholder:** the engineer shipping the change (primary), plus the reviewer/team who
  rely on the governance and audit trail. Non-engineer stakeholder: an engineering manager
  who needs the review burden and risk reduced.
- **Trigger:** a requested backend code change (a ticket or a described change to a route).
- **Inputs:** the change request, the current codebase, and prior engineering lessons from
  the retrieval corpus.
- **Outputs:** the implemented change, a security-review finding list, a deterministic test
  result, a storage/retrieval audit trail, and a run summary.

## Acceptance criteria (pass/fail on a real run)

A run **passes** when all of the following hold — each checkable without asking the author:

1. The planner produces a plan that meets the orchestrator's stated acceptance criteria,
   and a human approves it at the plan checkpoint.
2. The implementer makes only the approved change (no out-of-scope edits).
3. The security review returns **no unresolved Critical or High** findings.
4. The deterministic test gate returns **`status: pass`, exit 0** on the change's tests,
   **without manual intervention**.
5. The deterministic governance checks all pass: `forbidden_operations`, `tool_grants`,
   `audit_matches_writes`, `no_unknown_caller` (14/14).
6. The audit log records every tool call with a valid `calling_role`.

A run **fails** if any check above fails; a Critical review finding or a non-pass test
routes back to the implementer, and the same phase failing twice halts and escalates.

## Failure modes

Detailed in `docs/failure-mode-playbook.md` (detection → response → rollback → recovery).
The ten tracked modes include over-broad tool grant, unattributed action
(`calling_role: unknown`), retrieval classification leak, shared-process role, agentic
tester unable to run, missing dependency, Critical security finding, unverified/relayed
approval, secret exposure, and MCP server unreachable.

## Demo requirements

The walkthrough must: run the pipeline end-to-end on the representative task; show subagent
delegation and scoped tool grants; show MCP-backed storage and retrieval plus at least one
evaluation result; and **show the governance policy refusing a deliberately over-reaching
request** (the `delete_entry` denial), with the audit record.

## Why a custom agentic pipeline — not a simpler tool

This workflow mixes **judgment-heavy steps** (planning a fix, reasoning about contextual
security flaws like broken-object-level authorization) with **mechanical steps** (compiling,
running tests, pattern-based secret detection) and **hard governance requirements** (per-role
least privilege, classification boundaries, an audit trail). No single off-the-shelf tool
combines those three. Specifically:

- **A prebuilt / general coding agent** (e.g. a generic autonomous coder) handles the
  judgment steps but offers **no per-role least privilege, no classification-enforced
  retrieval, and no audit trail** — it acts with one broad identity. The over-reach this
  project catches (`delete_entry` by a write-only role) is exactly the failure a prebuilt
  agent cannot prevent, because it has no concept of role-scoped tool grants enforced at the
  server. Evidence: the `forbidden_operations` catch (13/14 → 14/14) and the server-side
  classification ceiling (Q4a vs Q4b) in this repo.
- **A simpler automation** (a plain CI script or linter) handles the mechanical steps
  cheaply and deterministically — which is exactly why this project *converts* those steps
  to code (ADR-001). But a script **cannot do the judgment steps**: it can't plan a fix or
  reason about a logic-level authorization flaw that matches no pattern. A pure script would
  either miss those or hard-fail on anything novel.

The right tool is therefore a **governed pipeline that routes each step to the cheapest
mechanism that can do it safely** — agent for judgment, deterministic code for the
specifiable, human for the irreversible — with governance enforced in the container, the
MCP allow-lists, and CI. The right-tool matrix (`docs/step-classification.md`) and the two
conversion ADRs (ADR-001 implemented, ADR-002 proposed) are the record of that reasoning.

## Module 1–4 artifact map (and gaps addressed in this resubmission)

- **Module 1:** PRDs (`docs/lint-prd.md`, `docs/import-check-prd.md`), rubrics, baseline
  (`docs/iteration-log.md`). *Resubmission adds:* this scope doc; rubric thresholds tied to
  business outcomes; a like-for-like full-pipeline baseline for the impact comparison.
- **Module 2:** agent definitions (`agents/`), two versioned skills (`skills/`), memory
  layout (`docs/memory-architecture.md`), reflection log. *Resubmission adds:* committed
  (scrubbed) memory layers, a consolidated reflection log with before/after scores, and a
  pruned stale entry with a written reason.
- **Module 3:** orchestration diagram, routing-and-tool-grant map, MCP schemas + allow-lists,
  retrieval quality report, eval harness, holdout set, calibration log. *Resubmission adds:*
  the **real validated retrieval server** committed (replacing the placeholder) and **HO-01…HO-05**
  run, scored, and committed.
- **Module 4:** governance policy, role-to-tool matrix, CI guardrails, audit log,
  failure-mode playbook, decision matrix, deterministic conversion, ADR package.
  *Resubmission adds:* shared-role fix so per-role limits hold in a live session, reconciled
  implementer grants, and reliability/cost controls shown firing.