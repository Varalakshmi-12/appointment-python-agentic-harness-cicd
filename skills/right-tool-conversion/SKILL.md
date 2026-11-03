---
name: right-tool-conversion
description: Decide whether a workflow step should be an agent, deterministic code, or a human checkpoint — and, if converting, produce the readiness package before writing code. Use when classifying a step or proposing a conversion.
version: 1.0.0
---

# Right-Tool Conversion

Use this before converting any agentic step to deterministic code, or when classifying a new
step. Decide first, write the record, **then** build — commit timestamps prove the order.

## 1. Classify against four signals (cite evidence from the logs)
- **Stability** — same input → same decision across runs? (Calibration / Iteration Log)
- **Repeatability** — does the operation repeat unchanged each run?
- **Specifiability** — can the rule be written out completely, with no open-ended judgment?
- **Run rate** — does it run often enough that conversion pays off?

## 2. Name the safety field
The one class of input the agent currently handles by judgment that a deterministic version
must preserve (e.g. an incidental failure that must not flip the verdict). "None identified"
is allowed; never leave it blank. This is not a fifth signal and does not make a weak step
strong.

## 3. Recommend
One of: **strong candidate / weak candidate / not a candidate / already deterministic.** The
recommendation follows the cited evidence, not hoped-for savings. A well-evidenced "not a
candidate" is a valid, successful outcome.

## 4. Write the ADR at Status: Proposed
Title, status, context, decision, **≥2 alternatives considered** (≥1 citing concrete evidence
from logs, evals, cost, or calibration), consequences, evidence, open risks. Do not invent
after-numbers before the code exists — that is why the record stays Proposed.

## 5. Plan the proof (before building)
- **≥3 unit tests:** one normal/success, one failure, one for the named safety case.
- **Before/after measurements to collect:** latency, token cost, predictability, audit
  clarity, quality/harness results. Note any rubric dimension that becomes N/A if output
  shifts from prose to structured data.
- **Rollback note:** a single revertible conversion commit (orchestrator wiring, routing-map
  row, governance-policy entry, CI step).

## 6. Implement, measure, integrate, accept
Only after an end-to-end regression passes does the ADR move **Proposed → Accepted**, with the
measured comparison filled in.

## Examples in this repo
- `docs/adr/ADR-001-tester-deterministic-conversion.md` — **Accepted** (tester → script;
  measured ~2.3s / $0).
- `docs/adr/ADR-002-import-check-deterministic-conversion.md` — **Proposed** (readiness
  analysis, not yet built).
- `docs/step-classification.md` — the full agent-vs-deterministic-vs-human matrix.

## Change log
- 1.0.0 — Initial version, extracted from the Module 4 right-sizing work (ADR-001 conversion
  and the ADR-002 readiness exercise).