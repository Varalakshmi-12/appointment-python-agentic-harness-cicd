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