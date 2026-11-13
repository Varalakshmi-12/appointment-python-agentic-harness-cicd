# Impact Report
## Governed pipeline vs. single-agent baseline — one matching task, five metrics

**Author:** Varalakshmi · **Date:** 2026-11-13
**Delivery path:** Job-seeker / no-deployment (representative workflow)

This report answers the question the rubric asks directly: *measure the full governed
pipeline against one matching baseline task, and report all five metrics — quality,
review latency, defect rate, cycle time, and cost per run — at that level.*

To do that cleanly, the comparison is a **controlled experiment**: the *same* defect is
fixed *two ways* — once by a single ungoverned agent, once by the full governed
pipeline — on the **same model** (`claude-sonnet-5-5`) and in the **same repository**.
Only the workflow differs, so the five-metric delta is attributable to governance, not
to a different task, a different model, or a different codebase.

A short note on provenance, kept deliberately honest: the Module 1 and Module 2
baselines referenced in the narrative (§4) were produced in the earlier-modules repo and
are cited to their own commits; they are **not** restaged here as native capstone
evidence. The headline experiment in §2–§3 was run and committed **natively in this
repo** (`eval/evidence/impact/`), with both the ungoverned and governed runs reproducible
from the recorded prompts and transcripts.

---

## 1. The matching task

**Defect:** `appointment-backend/test_sms.py` executes code at module *import* time — it
prints the three Twilio credential variables to stdout and attempts a live
`client.messages.create()` call. Importing the module therefore has side effects (a
credential-exposure pattern and a live-call attempt).

**Severity — stated, not assumed:** the Twilio integration is **not wired up** (dummy
credentials, no connected account), so nothing is actually sent or leaked today. This is
a **Warning-level import-safety + credential-print defect**, not a Critical "sends real
texts" vector. Stating that assumption explicitly is itself a lesson carried forward from
Module 2 (see §4, Cycle 1).

**Why this task:** it is a real defect your Module 1 import-check *detected but never
fixed*, it carries a security dimension (so the pipeline's security-reviewer role is
exercised), and it is small enough to run both ways cheaply and reproducibly.

Both runs were given the **same base instruction** ("make the module import-safe: move
executable code under a `__main__` guard, remove the credential prints, keep direct-run
behavior"). Neither prompt asked for a test; what each workflow *did* about test coverage
is one of the measured results.

---

## 2. The five-metric comparison (measured)

| Metric | Ungoverned single agent | Governed pipeline | M / P |
|---|---|---|---|
| **Task** | Fix `test_sms.py` import defect | **Same** defect | — |
| **Model** | `claude-sonnet-5-5` | `claude-sonnet-5-5` | — |
| **Quality** (fix rubric /20) | **13/20 — fails the bar** (Defect 4 · Correctness 3 · **RegTest 1** · Scope 4 · **Governance 1**) | **20/20 — passes** (4 · 4 · 4 · 4 · 4) | **Measured** |
| **Review latency** | **none** — ran in auto mode, change shipped unreviewed | **automated** security review in-pipeline (read-only reviewer, verdict *approve*, 0 Critical/High/Medium) | **Measured** |
| **Defect rate / escape** | **no regression test** → recurrence would go undetected; the deterministic gate passes *vacuously* (nothing covers import-safety) | **3 regression tests** added (`eval/test_sms_import_safe.py`), fail-on-old / pass-on-new, **running inside the gate** (40 passed) | **Measured** |
| **Cycle time** | **~1 min** wall · 16 s active compute | **~15 min** wall · **3 m 56 s** active compute (the extra wall is the deliberate human plan-approval gate) | **Measured** |
| **Cost per run** | **$0.1496** | **$0.90** (~**6×**) | **Measured** |

Scoring instrument for the Quality row: `eval/test-sms-fix-rubric.md` (a defect-fix
rubric, 1–4 per dimension, pass = 3+ on every dimension). The rubric's dimension 5
(Governance) is where the two runs structurally diverge — the lone agent scores 1 (no
separation, no review, no audit), the pipeline scores 4 (enforced separation + reviewer
sign-off + audit trail).

**Headline, stated without inflation:** governance here costs **~6× the dollars, ~15× the
compute, and ~15× the wall-clock** — and in exchange the fix moves from **13/20 (fails)
to 20/20 (passes)**, gains a **regression test that locks it**, a **real security review**,
and a **full audit trail**. The ungoverned agent is cheaper and faster and produces
*correct code* — but unreviewed, untested, and unaudited.

---

## 3. What the governance actually bought (evidence)

Four things the governed run did that the lone agent structurally could not — each backed
by a committed artifact, not an assertion:

1. **Separation of duties.** The run fanned out across distinct, scoped roles —
   `appt-planner` (read-only) → `appt-implementer` (write) → `appt-security-reviewer`
   (read-only) — visible in the per-run usage breakdown (orchestrator 23% · planner 10% ·
   implementer 7% · security-reviewer 7% · retrieval 8%). A single agent has no such
   separation; it reviews its own work or not at all.

2. **Institutional memory fed the fix.** The planner retrieved a prior lesson —
   `lesson-sms-notifications-were-never-wired` — under `calling_role: planner`, and the
   security-reviewer re-retrieved it under its own role
   (`eval/evidence/impact/governed/retrieval-audit-thisrun.jsonl`, 2026-11-13). That prior
   lesson is *why* the pipeline correctly calibrated severity to "dummy creds, nothing
   sent." The lone agent had no corpus to draw on and retrieved nothing. This is the
   self-improving loop (§4) feeding forward into a live run.

3. **Least-privilege enforcement has teeth.** The governance layer that wraps the run
   records refused over-reaches: `reviewer` denied `write_entry`, `implementer` denied
   `delete_entry`, `dependency-auditor` denied both
   (`eval/evidence/impact/governed/storage-enforcement-evidence.jsonl`). (These denials
   are cross-run enforcement evidence, not from this particular fix — labeled as such.)

4. **A traceable audit record.** The pipeline produced a run-summary documenting the
   defect, the change, the review verdict, the gate result, **and the five low-severity
   items it consciously left out of scope**
   (`eval/evidence/impact/governed/run-summary.md`). The lone agent produced a code change
   and nothing else.

---

## 4. The self-improving loop across the whole course (iteration narrative)

The system did not arrive fixed; it improved in discrete, evidence-backed cycles. Each
cycle below is a *change made because of run/eval evidence, plus a rerun confirming it
held* — the rubric's definition of an improvement cycle.

**Cycle 1 — Module 2, security-reviewer agent (v0.1.0 → v0.1.1).** *(earlier-modules
repo, cited to its commits)*
- **Baseline run (v0.1.0):** reviewing `app.py` scored **18/20**. Misfire: it flagged the
  `/test-sms` and `/test-email` routes as **Critical** cost-bearing vectors while
  *assuming* Twilio was live — but it is not wired up, so the real-world severity was
  overstated.
- **Change, from that evidence:** added an instruction to state the assumption behind any
  integration-dependent finding and verify whether the integration is live before rating
  it Critical (commit `643f49d`, v0.1.1).
- **Rerun confirmed it held:** **20/20**, with Finding-Accuracy and Severity-Classification
  each 3→4, no regressions, and *lower* cost ($0.30→$0.25) and faster cycle (7m16s→5m59s).
- **Why it matters here:** this is the exact lesson the capstone pipeline applied in §1
  when it rated the `test_sms` defect "Warning, not Critical — integration not live."

**Cycle 2 — Capstone, native (`no_unknown_caller`, HO-06 before → after).**
- **Failing run:** holdout HO-06 scored **13/14** — the `no_unknown_caller` deterministic
  check failed because the storage server read the caller's role from a single
  module-global env var, so a subagent's write was attributed to `unknown`
  (`eval/evidence/holdout/HO-06-before-fix.json/.log`).
- **Change, from that evidence:** reworked `mcp-servers/storage/server.py` to take
  `calling_role` as a per-call argument, with a per-role enforcement test
  (`eval/test_per_role_enforcement.py`, 5/5).
- **Rerun confirmed it held:** HO-06 re-run scored **14/14**
  (`eval/evidence/holdout/HO-06.json/.log`), and the before/after pair is kept side by side
  as the regression record.

**Cycle 3 — Capstone, native (this controlled experiment).** The §2–§3 ungoverned-vs-
governed comparison is itself the final cycle: it quantifies, on one matched task, what
the governance layer is worth (13/20 → 20/20) and what it costs (~6× dollars). Evidence:
`eval/evidence/impact/`.

**The loop is visible in the record, not just asserted:** the lessons corpus accumulated
across the course (`lesson-sms-notifications-were-never-wired`,
`lesson-deterministic-gate-misses-backend-tests`,
`lesson-status-state-machine-enforced-on-every-write-path`, …) and was *read back* by the
planner during Cycle 3 — the calibration log and commit history trace the same arc.

---

## 5. Secondary measured result: right-tool conversion (agent → deterministic)

Separate from the governance comparison, one step was converted from an agent to code and
measured within-step (ADR-001). Converting the Test step to
`scripts/run_tests_deterministic.py` took its **token cost to $0**, **cycle time to
seconds**, and **review from prose to a structured `result.json`** — with no loss of
correctness. This is a genuine, exact within-step before/after; it is reported here as a
*secondary* result, not the headline, precisely because it is not a like-for-like *task*
comparison (which §2 now provides).

---

## 6. Measured vs. projected — what to trust

- **Measured (both runs, directly):** quality (13/20 vs 20/20), cost ($0.1496 vs $0.90),
  cycle time (1 min/16 s vs 15 min/3 m 56 s), regression-test coverage (0 vs 3 in-gate),
  gate result (40 passed), review verdict (none vs approve/0 findings), and the governance
  artifacts in §3.
- **Projected (assumption stated):** the ungoverned path's *human* review latency is given
  as **~6–8 min** by analogy to the Module 1 baselines' measured review times; the actual
  ungoverned run had **zero** review (auto mode), so 6–8 min is the cost a responsible team
  *would* add, not a cost this run incurred. The governed run's security review is measured
  (in-pipeline, part of the 3 m 56 s compute); its human plan-approval gate adds wall-clock
  by design.
- **Not claimed:** production-volume cost/latency for the full pipeline were not
  load-tested; both runs were cache-heavy, so the dollar figures are cache-inclusive
  measured costs, and the ~6× ratio is the comparable quantity.

---

## 7. Honest limitations

- The governed fix left `from twilio.rest import Client` at module top, so the module still
  requires the (declared) `twilio` dependency to import — import-*safe*, not
  dependency-free. The same is true of the ungoverned fix.
- Five low-severity items were consciously left out of scope to keep the two runs'
  *code-change scope* matched (stale `conftest.py` comment, a loose AST check in the new
  test, `socket.getaddrinfo` not patched, no direct-run leak test, Account-SID-in-exception
  path). They are listed in the governed run-summary.
- The storage-enforcement denials in §3 are cross-run evidence that the grants have teeth,
  not events from this particular fix (which touched files, not the storage server).
- This is a no-deployment, representative-workflow path; the numbers bound what the current
  governance is worth on one small defect, not at production scale.

---

## 8. What the numbers mean

- **Governance is not free, and this report does not pretend it is.** On one matched task
  it cost ~6× the dollars and ~15× the time.
- **What that buys is quality you can verify and defects that cannot silently return:** a
  fix that passes the bar instead of failing it (20/20 vs 13/20), a regression test inside
  the gate, an independent security review, institutional memory applied to severity, and
  an audit trail — none of which the faster, cheaper lone agent produced.
- **The decision this supports is a routing decision, not a verdict:** use the ungoverned
  path for low-stakes, reversible, well-covered changes where speed dominates; use the
  governed pipeline where a defect's cost of recurrence, or the need for review and
  auditability, justifies the premium. The §5 conversion is the third option — when a step
  is stable and structural, take it out of the agent entirely.