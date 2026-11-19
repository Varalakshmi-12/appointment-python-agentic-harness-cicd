# Autonomous Workflow Run - deterministic gate + reliability controls

Author: Varalakshmi * Date: 2026-11-18

This write-up demonstrates that the test gate runs with no human filling a step, closing
the gap noted in the earlier interactive run (`docs/run-summary.md`, 2026-11-03), where
the appt-tester could not run and a human supplied the result.

## 1. The test step runs autonomously (no manual test-result input)

`python scripts/run_gate.py --tests eval/` runs the whole `eval/` suite as a deterministic
gate, with timeout and budget controls active, and returns pass/fail on its own - no human
reports a number.

Result (`eval/evidence/autonomous-gate-run.json`, `.log`):
- gate status: **pass**
- controls active: timeout 300s, per-run budget
- reported spend: $0.0010

The same command is the CI "Deterministic Test Gate" (`.github/workflows/ci.yml`), run
unattended on every push. The `coursetools` dependency that blocked the original tester is
gone - the step is `scripts/run_tests_deterministic.py` (ADR-001).

## 2. Reliability and cost controls each fire

`python scripts/controls_demo.py` exercises each control to the point it engages
(`eval/evidence/controls-demo-run.log`; `fired` events in
`eval/evidence/controls-firing-evidence.jsonl`):

- **timeout** - FIRED: a step exceeding its 1s limit is aborted.
- **retry** - FIRED: a transient failure is retried once, then succeeds.
- **max-iterations** - FIRED: phase `implement<->review` failing twice (limit 2) halts.
- **per-call budget** - FIRED: a $0.20 call over the $0.05 per-call cap is refused.
- **per-workflow budget** - FIRED: cumulative $0.12 over the $0.10 per-run cap is refused.

The max-iterations control is the escalation path: after a phase fails its retry ceiling,
the run halts and escalates to a human rather than looping (rollback / escalation policy in
`docs/failure-mode-playbook.md`).

## 3. What this closes (Production Integration & Tool-Evolution Drill)

- Removed the dependency on the unavailable tester tool (ADR-001).
- The deterministic test gate runs automatically, with no manual test-result input.
- Successful gate execution shown (status pass).
- Timeout, retry, budget exhaustion, and max-iteration escalation each demonstrated firing.

Evidence: `eval/evidence/autonomous-gate-run.{json,log}`, `eval/evidence/controls-demo-run.log`,
`eval/evidence/controls-firing-evidence.jsonl`; gate command in `.github/workflows/ci.yml`;
reliability/escalation policy in `docs/failure-mode-playbook.md`; conversion in ADR-001.