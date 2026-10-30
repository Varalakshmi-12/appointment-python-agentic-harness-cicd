# Ops-Ready Runbook
## Governed Multi-Agent Engineering Pipeline (appointment-app)

**Owner:** Chetan · **Last updated:** 2026-10-30

This runbook is for whoever operates the pipeline. It covers normal operation, what
to monitor, the reliability and cost controls, an incident playbook, escalation
rules, and rollback procedures. The guiding rule throughout: **when in doubt, stop
and escalate to a human — the system is designed to pause safely, not to push
through.**

---

## 1. Normal operation

- **Run environment:** Docker container `agentic_engineer_4`. Source mounted
  read-only for read-only roles; no network egress for agent work; `AGENT_ROLE` set
  per role at launch.
- **Trigger:** a human provides an issue + repo path to the Orchestrator.
- **Flow:** Orchestrator → Planner → *(human approves plan)* → Implementer → Reviewer
  → deterministic Test step → Project Manager → *(human confirms)* → run summary.
- **Secrets:** the model API key lives in the CI secret store / the operator's shell
  env and is injected only into steps that call the model (`-e`), never committed,
  never printed.

**Healthy run looks like:** each phase passes its acceptance gate before the next
starts; the Test step returns `status: "pass"`; both human checkpoints are answered;
CI gates are green; the audit trail records the run with no `authorization_denied`
entries.

---

## 2. Monitoring and health signals

| Signal | Where to look | Healthy | Investigate if |
|---|---|---|---|
| Authorization denials | storage audit log (JSON-Lines) | none in a normal run | any `authorization_denied` an operator didn't expect |
| CI gate status | GitHub Actions tab | all gates green | any gating job red |
| Pipeline integrity | Pipeline Integrity Check job | green | red — a guardrail was weakened |
| Test verdict | `result.json` from the deterministic step | `status: "pass"` | `fail` (code) or `error` (suite didn't run) |
| Classification | retrieval responses | within role ceiling | any above-ceiling document returned |
| Loop/iteration | orchestrator run log | advances phases | same phase fails its gate twice |

The **Audit Trail** CI job assembles policy results, evaluation results, agent
actions, and denials into one artifact per run — that is the first place to look
after any incident.

---

## 3. Reliability and cost controls

**In place today:**
- **Max-iteration guard:** the Orchestrator halts and escalates if the same phase
  fails its gate twice in a row (prevents infinite revise loops).
- **Human checkpoints:** mandatory HALT after the Planner and before finalizing;
  the run does not proceed on a timeout — it waits for a person.
- **Model scope as a cost cap:** the API key is restricted to a single approved
  model (`anthropic/claude-haiku-4.5`), bounding per-call cost and preventing
  accidental use of an expensive model.
- **Deterministic fallback:** structural steps (tests, policy checks) run as code
  with zero token cost and no inference.

**Recommended to add / confirm (Workstream 6 reliability controls):**
- Per-call and per-workflow **token/$ budgets** with a hard stop when exceeded.
- **Timeout** per agent call and an overall **wall-clock cap** per run.
- **Retry with backoff** (bounded, e.g. 1–2 retries) for transient model/API errors,
  distinct from the revise loop.
- **Rate limit** on model calls to stay within provider limits.

---

## 4. Incident playbook

| Incident | Detection | Immediate response | Escalate when |
|---|---|---|---|
| **Agent attempts an unauthorized action** | `authorization_denied` in audit log; or `forbidden_operations` fails | No action needed — the MCP allow-list already blocked it. Record the attempt. | Pattern repeats, or a denial appears for a role that should have had access (possible mis-scoped grant) |
| **A gating CI check fails** (policy / eval / governed-file) | GitHub Actions job red; merge blocked | Read the failing job's log + the uploaded report. Fix the drift/regression; do not bypass the gate | Fix is non-obvious, or the gate seems wrong |
| **Pipeline Integrity Check fails** | Integrity job red | A guardrail was removed/weakened in the change. Do **not** merge. Restore the gate/classifier/audit-trail setting | Anytime — this is always human-reviewed |
| **Secret exposure** (key printed, committed, or pasted) | Key visible in a log, file, or chat | Treat as compromised: **revoke** the key at the provider, generate a new one, update the secret store only. Never reuse | Immediately |
| **Agent stuck in a revise loop** | Same phase fails its gate twice | Orchestrator auto-halts and escalates. Review the failing report; the Implementer likely can't satisfy the gate | On the halt |
| **Model/API unavailable or over budget** | Model step errors, times out, or budget cap hit | Stop the run; fall back to deterministic steps where possible; retry later within budget | If it blocks a time-sensitive run |
| **Retrieval returns above-ceiling content** | A confidential doc appears for an internal-ceiling role | Treat as a classification leak: stop using that output, record the near-miss, fix the retrieval fallback (don't return top-k on a zero-score match) | Immediately (data-exposure class) |
| **Deterministic step returns a wrong-but-consistent result** | A real-world case the unit tests didn't cover | A script fails the same way 100% of the time — add a test for that input class, fix the logic, re-measure | On discovery |

---

## 5. Escalation matrix

Escalate to a human (stop and wait) when any of these is true:

- A change touches governance (policy, allow-lists, CI gates, container permissions).
- A gating check fails and the fix is not obviously safe.
- The Pipeline Integrity Check is red.
- A secret may be exposed.
- A classification/data-exposure concern arises.
- The same phase fails its gate twice (automatic — the Orchestrator already halts).
- Anything the system was not designed to handle (the Orchestrator's rule:
  "if the run cannot proceed for an environmental reason, stop and report the blocker").

The default is **stop safely**, never "push through to finish."

---

## 6. Rollback procedures

- **Revert a bad change.** Every significant change (including the deterministic
  conversion) lands as a **single commit**, so one `git revert <commit>` restores the
  prior behavior completely — e.g. reverting the Tester-integration commit brings the
  agentic tester back. Then push; CI re-validates.
- **Revoke/rotate a credential.** Revoke at the provider, mint a new key, update the
  secret store (GitHub Secrets / shell env). No code change is needed because the
  pipeline references the secret by name, not value.
- **Tighten or remove an agent's access.** Remove the grant from the allow-list +
  agent definition + policy together, in one commit (keeps them in sync so the policy
  test stays green). Least-privilege: remove access the moment it's no longer needed.
- **Fall back to deterministic behavior.** If an agentic step is unreliable, route
  that step to its deterministic equivalent (as done for the Test step) rather than
  trying to "fix the prompt" under pressure.
- **Disable a run.** If the pipeline must be paused, the human checkpoints already
  provide safe stop points; do not auto-approve past them.

---

## 7. Recovery and post-incident

After any incident:
1. Confirm the system is back to a known-good state (CI green, no unexpected denials).
2. Record what happened in `docs/calibration-log.md` (and a near-miss note if a
   control almost failed): the change, what broke, what caught it, the fix, the result.
3. If the incident revealed a durable decision, write or update an **ADR**.
4. If a guardrail gap was found, add the missing test/check so the same failure turns
   a check red next time.

Documenting the near-miss is part of the system's self-improving loop: the pipeline
is trustworthy because its gaps are known, named, and closed — not assumed absent.

---

## Quick reference

- **Audit log:** storage server JSON-Lines + CI Audit Trail artifact
- **Gates (required):** Policy Test Suite, Governed File Check, Pipeline Integrity Check
- **Rollback:** `git revert <commit>` (changes are single revertible commits)
- **Secret rotation:** provider revoke → new key → secret store only
- **Safe default:** stop and escalate to a human