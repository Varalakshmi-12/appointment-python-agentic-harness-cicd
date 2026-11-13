# Quality Rubric: Defect-Fix Task (test_sms.py import-time Twilio call)

## Dimensions (score 1-4; Pass = 3+ on every dimension)

### 1. Defect Resolution
Is the target defect actually gone — no live Twilio/network call at module import time?
1: still fires at import. 2: partially guarded. 3: no call at import. 4: no call at import AND the guard is explicit (env/credential check or main-guard).

### 2. Correctness / No Breakage
Does the module still import cleanly and preserve intended behavior?
1: import breaks. 2: imports but behavior changed. 3: imports clean, behavior preserved. 4: plus verified by running py_compile + import.

### 3. Regression Test
Is there a test that fails on the old code and passes on the fix, locking it in?
1: none. 2: a test that doesn't actually catch the defect. 3: a test that fails-old/passes-new. 4: plus it runs in the deterministic gate.

### 4. Scope Discipline
Only the necessary change, nothing unrelated.
1: broad unrelated edits. 2: some scope creep. 3: minimal, on-target change. 4: minimal change with a one-line rationale.

### 5. Governance Compliance
Separation of duties, tool-grant enforcement, and an audit trail for the change.
1: none (single agent, unrestricted). 2: roles named but not enforced. 3: role separation enforced (implementer can't exceed its grant). 4: enforced + reviewer sign-off + audit entry.

## Threshold → Business Outcomes

The pass bar (3+ on every dimension) marks a fix a team can merge without a separate manual
QA or security pass, and that will not silently return:
- **Regression Test ≥ 3 → rework avoided.** A locked fix can't recur unnoticed, so no one pays
  to re-diagnose the same defect later (projected ~2–4 eng-hrs per avoided recurrence; see
  `docs/impact-report.md`).
- **Governance ≥ 3 → review labor removed, risk bounded.** Enforced separation + an independent
  review + an audit trail let the change merge without a human security sign-off while still
  stopping an over-reach.
- **Defect Resolution + Correctness ≥ 3 → safe to ship.** The reported defect is gone and
  nothing else broke.
A fix below the bar on Regression Test or Governance is cheaper and faster to produce but
carries exactly the recurrence and review-labor costs the governed pipeline removes.