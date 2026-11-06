# Failure-Mode Playbook

How the governed pipeline detects, responds to, and recovers from known failure modes.
Every mode below has actually occurred during development; detection and response are the
controls that caught it. See `docs/calibration-log.md`, `eval/enforcement-verification.md`,
and `docs/run-summary.md` for the source evidence.

## Escalation & rollback policy (general)

- **Stop and escalate to a human** when the same phase fails twice (the orchestrator's
  max-iteration guard), when a Critical security finding cannot be resolved, or when a
  governance check fails and the cause is not obvious.
- **Roll back** by reverting the single focused commit for the change (every conversion and
  integration ships as one revertible commit). No unrelated work is undone.
- **Fall back to deterministic behavior** where a deterministic path exists (e.g. the test
  gate falls back to `scripts/run_tests_deterministic.py` when the agentic tester cannot run).
- **Never** relax a human checkpoint or widen a tool grant to get past a failure.

## Failure modes

| # | Failure mode | Detection signal | Automated response | Escalation / rollback | Recovery |
|---|---|---|---|---|---|
| 1 | **Over-broad tool grant** — a role gets a destructive op it shouldn't (e.g. implementer granted `delete_entry`) | `forbidden_operations` deterministic check fails against the audit log (13/14); `tool_grants` may still pass | Run fails the eval gate; merge blocked in CI | Remove the grant from the routing map and agent definition; escalate if the grant's origin is unclear | Re-run harness → 14/14; confirmed on holdout (HO-06). Evidence: calibration log 2026-09-29 (induce `b564f82`, fix `c26bdaf`) |
| 2 | **Unattributed action** — a storage write logs `calling_role: "unknown"` | `no_unknown_caller` check fails on a real run | Flag the run; audit-based enforcement is untrustworthy until fixed | Open item: the storage server must require a valid `calling_role` and reject `"unknown"` | Enforcement-point fix (server-side role requirement); its own calibration cycle |
| 3 | **Retrieval classification leak** — a search miss returns `top_k` docs including one above the caller's ceiling | Classification-boundary check (Q4a/Q4b) / `classification_withheld` absent when it should fire | Server ceiling filter drops over-classified docs | Raise the vector threshold or add a query-shaped sentence to the lesson; re-index | Re-run the ground-truth set; confirm Q2 fix holds without regressing Q1/Q6 (see `docs/retrieval-quality-report.md`) |
| 4 | **Shared-process role** — in-session subagents share one `AGENT_ROLE`, so per-role scope isn't enforced within a session | Noted in calibration near-miss patterns | Container-level role still bounds the blast radius | Run sensitive roles in separate role-scoped containers (`scripts/run-agent.*`) | Per-role process isolation; tracked as an open risk |
| 5 | **Agentic tester cannot run** — the tester's `coursetools` tools are absent, so it spawns with zero tools | Tester step errors: `unrecognized [mcp__coursetools__test_runner]` | Pipeline halts at the test gate rather than passing untested | Fall back to the deterministic test step | `python scripts/run_tests_deterministic.py …` runs the suite (~1s, $0); this is the ADR-001 conversion |
| 6 | **Missing runtime dependency** — e.g. `flask_cors` not in the container | Deterministic test returns `status: "error"`, `exit_code: 2` (collection error, *not* a test failure) | Three-state classifier reports `error`, not `fail` — the distinction matters | Install the app's deps; bake them into the Dockerfile for reproducibility | Re-run → `status: "pass"`; the error-state result is kept as evidence of the classifier |
| 7 | **Critical security finding** | Security reviewer returns a Critical finding | Change routes back to the implementer | After two failed attempts, halt and escalate to the human | Implementer fixes; re-review; Medium/Low findings recorded as follow-ups |
| 8 | **Unverified / relayed approval** — approval reaches the orchestrator second-hand, or a checkpoint is relaxed without the human asking | Orchestrator refuses to proceed on relayed authority | No implementation runs; nothing changes | Human approves the orchestrator **directly** (`claude --agent appt-orchestrator`) | Re-run with direct approval; observed and handled in `docs/run-summary.md` |
| 9 | **Secret exposure** — hardcoded credential or `.env` in the tree | Security review (secret-exposure check) and secret scan; `test_policy.py` patterns | Finding raised; file kept out of git | Rotate the exposed credential; add to `.gitignore`; scrub history if ever committed | `.env` and `test_mysql.py` are gitignored; key supplied at runtime via `-e`, scoped to one model |
| 10 | **MCP server unreachable** — storage/retrieval show `✘` in `/mcp` | Connection check at startup | Pipeline cannot record or retrieve | Confirm `.mcp.json` uses **stdio** transport matching the servers (not an `http` URL) | Correct transport; relaunch; `/mcp` shows both ✔ |

## Reliability & cost controls

- **Timeouts / retries / fallbacks** on agent steps; a deterministic fallback for the test gate.
- **Max-iteration guard:** the same phase may retry at most twice before the run halts and escalates.
- **Per-call and per-workflow budgets** cap token spend; converting stable steps to code removes their cost entirely.
- **Audit logging** on every storage/retrieval call (`logs/*-audit-log.jsonl`) so failures, retries, denials, and rollbacks are all recorded.

## Monitoring

- Watch the audit logs for `authorization_denied` and `classification_withheld` events.
- A red required status check in CI (policy test, eval gate, pipeline-integrity) blocks merges.
- Deterministic check results (`forbidden_operations`, `tool_grants`, `audit_matches_writes`,
  `no_unknown_caller`) are the health signals for a governed run.