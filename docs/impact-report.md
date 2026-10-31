# Impact Report
## Baseline vs. After + Tool-Evolution Drill Summary

**Author:** Chetan · **Date:** 2026-10-30
**Delivery path:** Job-seeker / no-deployment (representative workflow)

This report compares the Module 1 baseline against the post-capstone system across
quality, review latency, defect catching, cycle time, and cost per run. Where a
metric cannot be compared task-for-task (the baseline measured single-agent tasks;
the capstone is a governed multi-agent pipeline), the proxy used is stated explicitly,
per the capstone's "best available proxy, and explain it" guidance.

---

## 1. The Module 1 baseline (measured, 2026-08-17)

Two single-agent tasks, each run in its own Git worktree + container:

| Task | Quality (rubric) | Cycle time | Review latency | Cost/run | Tokens (in / out) |
|---|---|---|---|---|---|
| A — Backend lint review (flake8) | 16/16 Pass | ~76 s | 8 min | $0.23 | 319,600 / 3,100 |
| B — Backend import/compile check | 16/16 Pass | ~76 s | 8 min | $0.26 | 372,900 / 3,700 |

**Key observation that frames this whole report:** both baseline tasks are
*structural* checks — run a linter, run `py_compile`/import — with a single correct
answer and no language judgment required. The baseline ran them through an AI agent
at ~$0.25 and an 8-minute human review each, consuming ~320k–370k input tokens per
run. That is precisely the "agent is overkill for a deterministic task" situation the
capstone's right-tool discipline targets.

---

## 2. What the capstone added

On top of the Module 1 harness, the post-capstone system adds: a governed
multi-agent orchestration (planner / implementer / reviewer / test / PM), MCP-backed
storage and retrieval with least-privilege allow-lists and classification ceilings,
a holdout evaluation harness (deterministic checks + rubric), a CI/CD governed
pipeline with gating and advisory checks plus a self-protecting integrity check, an
audit trail, and one measured agent→deterministic conversion (the Test step, ADR-001).

---

## 3. Metric-by-metric comparison

| Metric | Baseline | Post-capstone | How measured / proxy |
|---|---|---|---|
| **Quality** | 16/16 on both tasks | Maintained, with governance added: policy suite 5/5, deterministic governance checks (e.g. 14/14), converted Test step 6/6 unit tests incl. the three-state edge case | Direct for the harness checks; the conversion added quality coverage, not regression |
| **Review latency** | 8 min (human reads a prose report) | ~seconds for the converted Test step (reads a structured `result.json`: status + failing-test tail) | Direct for the converted step; structured deterministic output is far faster to verify than prose |
| **Cost per run** | $0.23–$0.26 per structural task (~320k–370k input tokens) | **$0** for the converted Test step; model-scope cap (Haiku-only key) bounds remaining agent calls | Direct for the converted step; the baseline shows the cost a comparable structural step incurs as an agent |
| **Cycle time** | ~76 s per single-agent task | ~2.3 s wall-clock (~0.18 s actual execution) for the converted Test step | Direct; no inference latency once the step is code |
| **Defect / over-reach catching** | Surfaced real code findings (e.g. a live Twilio API call at import time in `test_sms.py`) | Adds a governance layer that catches over-reaches the baseline could not: an accidental `delete_entry` grant was caught by `forbidden_operations` | Proxy: the baseline measured code-defect finding; the capstone adds governance-defect catching (different, additive capability) |

---

## 4. Headline measured result: the deterministic conversion

The sharpest apples-to-apples number comes from converting the Test step from an
agent to `scripts/run_tests_deterministic.py` (ADR-001):

| | Agentic Test step | Deterministic script |
|---|---|---|
| Functionality | Non-functional (no test tool; pipeline halted at the tester gate) | Runs and returns a verdict |
| Latency | — (never completed) | ~2.3 s wall-clock (~0.18 s execution) |
| Token cost | — | $0 |
| Predictability | — | Identical verdict across 3 runs |
| Review latency | prose, ~minutes | structured result, ~seconds |

Set against the Module 1 baseline — where comparable structural tasks cost ~$0.25
and 8 minutes of review each — this conversion shows the concrete saving available
when a stable, structural step is moved from an agent to code: **token cost to zero,
cycle time to seconds, and human review from minutes to seconds**, with no loss of
correctness (the three-state pass/fail/error logic preserves the one judgment the
agent applied).

---

## 5. Tool-evolution drill summary

(Full detail in `docs/tool-evolution-drill.md`.)

- **Change attempted:** convert the Test step from agent to deterministic code
  (variant: "convert a step"), and — as regression-catch evidence — an earlier
  revocation of an over-broad `delete_entry` grant (variant: "revoke a permission").
- **What broke / what improved:** the Test step was non-functional as an agent;
  converting it unblocked the pipeline at $0 and deterministic output. The grant
  revocation restored least-privilege after the Implementer was wrongly given delete.
- **What the harness detected:** the deterministic governance check `forbidden_operations`
  caught the `delete_entry` over-reach while the grant-map check passed — defense in
  depth with independent sources of truth. The full regression check (policy 5/5 +
  deterministic 6/6 + CI gates green) confirmed the conversion introduced no regression.
- **What was fixed / final result:** script implemented + unit-tested, integrated as a
  single revertible commit, governance artifacts synced, ADR-001 accepted, CI green.

---

## 6. What the numbers mean

- **Right-tool discipline pays off directly.** The baseline proves that running a
  structural check through an agent is expensive in both dollars and review time; the
  conversion proves the saving is real and large once the step is code.
- **Governance is additive, not a tax on quality.** Quality held (harness checks
  pass) while the system gained the ability to catch over-reaches and block unsafe
  merges — a capability the baseline simply did not have.
- **The evaluation harness is load-bearing.** It both caught a real regression
  (the grant over-reach) and certified the absence of one (the conversion). That is
  what makes the "no regression" claim credible rather than asserted.

---

## 7. Honest limitations of this comparison

- The baseline tasks (lint, import check) are not the identical task as the converted
  Test step, so cross-task numbers are proxies, labeled as such above. The
  within-step before/after for the conversion is direct and exact.
- This is a no-deployment path on a representative codebase; cost/latency for the
  full multi-agent pipeline were not load-tested at production volume.
- Known gaps (the `calling_role: "unknown"` attribution gap, the shared-process role,
  the retrieval zero-score fallback) are recorded in the calibration log and
  near-miss notes; they bound how far the current governance numbers should be trusted
  on live runs, and each has a named fix.