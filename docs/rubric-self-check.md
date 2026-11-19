# Rubric Self-Check

**Author:** Varalakshmi
**Repository:** appointment-python-agentic-harness-cicd

This self-check maps each rubric criterion to its evidence in the repository, states the
grader's original comment, and describes what this resubmission changed to address it.
First-submission total: 35/52.

| # | Criterion | 1st | Target | Where to verify |
|---|---|---|---|---|
| 1 | Workflow Scoping | 2 | 4 | `docs/capstone-scope.md` |
| 2 | Sandboxed Environment | 3 | 3 | `Dockerfile`, `docker-entrypoint.sh`, `scripts/run-agent.*`, README §1–§10 |
| 3 | Quality Spec & Baseline | 3 | 4 | `docs/security-review-rubric.md`, PRDs, `eval/test-sms-fix-rubric.md` |
| 4 | Agent, Skills & Memory | 3 | 4 | `.memory/`, `docs/reflection-log.md` |
| 5 | Orchestration & MCP | 2 | 4 | `mcp-servers/retrieval/retrieval_index.py`, `docs/routing-and-tool-grant-map.*` |
| 6 | Evaluation & Calibration | 2 | 4 | `eval/evidence/holdout/HO-01…06.*`, `docs/calibration-log.md` |
| 7 | Governance, Security & CI/CD | 3 | 4 | `mcp-servers/storage/server.py`, `eval/test_per_role_enforcement.py`, `eval/evidence/` |
| 8 | Right-Tool Decisions & ADRs | 4 | 4 | `docs/adr/`, `docs/step-classification.md` |
| 9 | Production Integration & Drill | 2 | 4 | `scripts/controls.py`, `eval/evidence/controls-firing-evidence.jsonl`, CI |
| 10 | Iteration Narrative & Impact | 2 | 4 | `docs/impact-report.md`, `eval/evidence/impact/` |
| 11 | Stakeholder Communication | 3 | 4 | `docs/stakeholder-one-pager.md`, walkthrough video |
| 12 | Clarity & Flow | 3 | 3 | walkthrough presentation |
| 13 | Design | 3 | 3 | walkthrough presentation |

---

## A note on evidence citations (why artifacts, not commit SHAs)

This repository was assembled by importing the project's files, so this repo's own
`git log` does not reproduce the full run → review → fix → rerun cadence — that
incremental history was produced over the course in the working repositories where each
change was originally made. To keep every citation verifiable *in this repository*,
evidence throughout these docs is cited by **artifact** — the committed file, the
before/after evidence under `eval/evidence/`, the relevant calibration-log entry, or the
scored holdout run — rather than by a commit SHA that would not resolve here. Where a
specific change is referenced, the reader can open the named file or evidence directly.
The self-improving cadence itself is documented in `docs/reflection-log.md` and
`docs/calibration-log.md` with before/after scores.


## 1 · Workflow Scoping (2 → 4)
**Comment:** "No capstone scoping document exists. No stakeholder or failure modes in the PRDs, and there's no argument against a prebuilt agent."
**Addressed:** Added `docs/capstone-scope.md` — workflow, quantified baseline pain (review latency, cycle time, cost per run), stakeholder (engineer, reviewer/team, non-engineer manager), trigger/inputs/outputs, six pass/fail acceptance criteria checkable on a real run, ten failure modes, demo requirements, and an explicit argument for a custom pipeline over both a prebuilt agent and a simpler script. Stakeholder and failure modes also added to both PRDs (`docs/lint-prd.md`, `docs/import-check-prd.md`).

## 2 · Sandboxed Environment (3 → 3)
**No comment.** Containerized harness with explicit filesystem/network/credential boundaries (`Dockerfile`, `docker-entrypoint.sh`), per-role read-only vs read-write mounts (`scripts/run-agent.*`), credentials injected at runtime and never baked in, parallel-session isolation documented. README covers prerequisites, env vars, run path, and troubleshooting.

## 3 · Quality Spec & Baseline (3 → 4)
**Comment:** "Now, tie thresholds to business outcomes."
**Addressed:** `docs/security-review-rubric.md` now ties each dimension's pass threshold to a specific business outcome, and the gate-outcome paragraph ties the pass bar to the dollar outcome (merge without a human security sign-off while keeping the risk bar, avoiding a shipped-vulnerability cost). `eval/test-sms-fix-rubric.md` carries the same threshold→outcome mapping. PRDs name trigger, decisions, actions, acceptance criteria; baseline in `docs/iteration-log.md` covers quality, review latency, cycle time, cost.

## 4 · Agent, Skills & Memory (3 → 4)
**Comment:** "Commit the project and knowledge layers (scrubbed), prune a stale entry with a written reason, and gather reflections into one log with before and after scores."
**Addressed:** The full memory tree is committed and scrubbed (`.memory/project/`, `.memory/knowledge/`, `.memory/reference/`). `docs/reflection-log.md` consolidates the self-improving loop: each entry names the trigger, the change, before/after scores, and whether it held on a rerun, plus a "Memory curation" section recording a pruned stale lesson (the outdated status-transition rule, superseded by `decision-007` and replaced with the corrected state-machine lesson) with a written reason.

## 5 · Orchestration & MCP Tools (2 → 4)
**Comment:** "The required vector tool isn't there — the committed server is a word-counting sample."
**Addressed:** The retrieval server is now a real dense-vector ranker (`mcp-servers/retrieval/retrieval_index.py`, spaCy GloVe embeddings) with a lexical gate and FTS5 fallback, validated in `docs/retrieval-quality-report.md` (6/6 precision@1) against `docs/proj-lessons-ground-truth.md`. Narrow per-role tool grants (`docs/routing-and-tool-grant-map.{md,json}`), schema-validated MCP servers with classification tags and citations, orchestration diagram, and human-in-the-loop plan checkpoint.

## 6 · Evaluation & Calibration (2 → 4)
**Comment:** "Run HO-01 through HO-05, score them with your rubric, and commit the logs."
**Addressed:** All six holdouts are run, scored 14/14, and committed (`eval/evidence/holdout/HO-01…06.{json,log}`) covering normal, edge, context-bleed, two-reviewer-block, and native re-run cases. The `HO-06-before-fix.*` pair preserves the 13/14 → 14/14 regression trace. `docs/calibration-log.md` ties each change to a specific holdout score or failure.

## 7 · Governance, Security & CI/CD (3 → 4)
**Comment:** "Fix the shared-role issue so per-role limits hold in a live session, reconcile the implementer's grants, and the hardcoded gmail + phone."
**Addressed:** The storage server now takes `calling_role` per call (`mcp-servers/storage/server.py`), so per-role limits hold in a live multi-subagent session; proven by `eval/test_per_role_enforcement.py` (5/5). Implementer grants reconciled across the grant map, allow-list, and agent definition. PII scrubbed; a full secrets/PII sweep is clean (`docs/sanitization-note.md`). Live denial/withhold evidence in `eval/evidence/retrieval-governance-live.jsonl` and `eval/evidence/run-*`. A reproducible negative test shows the gate blocking a change because an eval failed: `scripts/negative-test-grant-block.py` introduces an unauthorized `delete_entry` grant, the enforcement test and CI gate fail (PR blocked), the grant is corrected, and the rerun passes (`eval/evidence/negative-test-grant-block.log`).

## 8 · Right-Tool Decisions & ADRs (4 → 4)
Deterministic conversion with before/after evidence (ADR-001), agent/deterministic/human matrix (`docs/step-classification.md`), and an ADR package (`docs/adr/`) where each record carries context, decision, rejected alternatives with evidence, consequences, and open risks.

## 9 · Production Integration & Tool-Evolution Drill (2 → 4)
**Comment:** "Build the timeout, retry, and budget controls and show each one firing. Then get a run that passes the test gate without manual help."
**Addressed:** Reliability/cost controls implemented (`scripts/controls.py`: timeout, retry, max-iteration guard, per-call and per-workflow budgets), each shown firing in `eval/evidence/controls-firing-evidence.jsonl` with a test proving it (`eval/test_controls.py`, 7/7). An autonomous gate (`scripts/run_gate.py`) runs the suite under those controls and passes with no manual help (`eval/evidence/gate-result.json`), wired into CI and green.

## 10 · Iteration Narrative & Impact (2 → 4)
**Comment:** "Your 'before' is a lint check and your 'after' is a test script. Measure the full pipeline against one matching baseline task, then report all five metrics."
**Addressed:** `docs/impact-report.md` now reports a controlled like-for-like experiment: the same defect (`test_sms.py` import-time Twilio call) fixed two ways — a single ungoverned agent vs the full governed pipeline — on the same model, in this repo. All five metrics at the pipeline level (quality 13/20 vs 20/20, review, defect rate, cycle time, cost $0.15 vs $0.90), with measured vs projected clearly separated. Evidence in `eval/evidence/impact/{ungoverned,governed}/`; improvement cycles across the course in `docs/reflection-log.md` and `docs/security-review-iteration-log.md`.

## 11 · Stakeholder Communication (3 → 4)
**Comment:** "Add hours and dollars as labeled projections. The one-pager is also not necessarily one page."
**Addressed:** `docs/stakeholder-one-pager.md` adds a labeled hours/dollars projections table (review labor returned, model spend, rework avoided, right-tool conversion), separates measured inputs from projected totals, and is trimmed to a single page.

## 12–13 · Clarity & Flow / Design (3 → 3)
Addressed in the walkthrough presentation, submitted separately.

---

## Known open items (honest tracking)
- `docs/reflection-log.md` Entry 4 (retrieval near-miss on a paraphrased query) is tracked as an open item for the next cycle, not yet closed.
- ADR-002 (import-check deterministic conversion) is Proposed, not yet integrated.
These are recorded deliberately; they bound how far the current numbers should be trusted and are the natural next cycle of the self-improving loop.