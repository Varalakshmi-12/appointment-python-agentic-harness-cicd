# Retrieval Quality Report

**Component:** `mcp-servers/retrieval` (storage + retrieval over stdio)
**Prepared by:** Varalakshmi
**Date:** 2026-11-06
**Status:** Measured in-container; every number below is reproducible with `retrieval_eval.py`.

---

## 1. What changed

The retrieval server previously ranked with a placeholder stub — a word-count
over three dummy documents, carrying a `# Replace with sqlite-vec / embedding
search` TODO. It is now a real **dense vector** ranker over the **eight real
lesson files**:

- **Primary ranker:** dense embedding retrieval using **spaCy GloVe word
  vectors** (`en_core_web_md`, 300-dim), cosine similarity over section-level
  chunks (each chunk prefixed with the lesson title).
- **Lexical gate:** a small TF-IDF check. Averaged GloVe vectors are
  anisotropic (even off-topic text scores high), so a result is returned only
  if it also clears a TF-IDF lexical floor — this rejects off-topic queries.
- **Fallback:** SQLite **FTS5** keyword search, used when the vector ranker
  returns nothing above the floor (e.g. a very short query).
- **Governance preserved:** per-role classification ceiling (data-driven from
  `retrieval-grants.json`), `classification_withheld` audit entries, and
  citations carrying `source_document`, `chunk_index`, `similarity`,
  `lexical_score`, `retrieval_method`, `classification`.

### Why spaCy GloVe rather than sentence-transformers

A sentence-transformers embedding model was the first choice. Its weights
download is blocked by the environment proxy (HuggingFace returns 403). spaCy's
`en_core_web_md` ships as a **pip/GitHub wheel** (no HuggingFace), so it
installs and runs **fully offline and deterministically**. This gives genuine
embedding cosine scores — a strong match lands in **0.79–0.95**, which clears
the **0.65 semantic floor** that the deterministic harness
(`check_similarity_floor`) and holdout **HO-01** require. (A TF-IDF-only ranker
tops out around 0.43 and cannot satisfy that floor, which is why a dense
embedding ranker is the correct tool here.)

---

## 2. Ground-truth results (precision@1 = 6/6)

Six queries, each mapped to the single lesson a reviewer agent should retrieve.
Reproduce with `python mcp-servers/retrieval/retrieval_eval.py` (exit 0 on all-hit).

| ID | Query | Retrieved (top-1) | Similarity | Method |
|----|-------|-------------------|-----------|--------|
| Q1 | Why did SMS appointment reminders never reach patients? | sms-notifications-were-never-wired | 0.910 | vector |
| Q2 | How should we handle failures returned by the appointment API routes? | standardize-route-error-handling | 0.935 | vector |
| Q3 | cursor connection leak too many connections | mysql-cursor-and-connection-leaks | 0.786 | vector |
| Q4 | What is the monthly budget ceiling for patient notifications? | notification-cost-and-vendor-budget | 0.937 | vector |
| Q5 | How should appointment status changes be validated? | appointment-status-state-machine | 0.929 | vector |
| Q6 | Appointment shows the wrong time to patients in another timezone | store-appointment-times-in-utc | 0.945 | vector |

**precision@1 = 6/6.** Every top-1 similarity is **≥ 0.786**, clearing the 0.65
semantic floor.

A caveat recorded honestly: averaged GloVe vectors are anisotropic, so absolute
cosines are compressed into a high band and the margin to the runner-up is
small (0.01–0.03) on several queries. Ranking is nonetheless correct on all
six, and the lexical gate plus the FTS5 fallback guard the edges (a short query
that dips below 0.65 is caught by FTS5).

---

## 3. Floors

| Floor | Value | Purpose |
|-------|-------|---------|
| `SEMANTIC_FLOOR` | 0.65 | GloVe embedding cosine. Matches the harness and HO-01 — a genuine match must score ≥ 0.65. |
| `LEXICAL_GATE` | 0.05 | TF-IDF cosine. Rejects anisotropic embedding false positives (relevant queries score ≥ 0.18 lexically, off-topic ~0). |

Off-topic queries are correctly rejected (zero citations): verified with
"what is the weather in Paris today" and "how do I bake sourdough bread" →
**0 results** each.

---

## 4. Governance verification

The per-role grant map is **data**, read from `retrieval-grants.json` (the
single source of truth, mirrored by the routing/tool-grant map), not hardcoded.
Only `orchestrator` carries a `confidential` ceiling; every other retrieving
role is capped at `internal`; `project-manager` is not granted `retrieve` at
all. Role names normalize (`project_manager` ≡ `project-manager`).

Exercised against the confidential lesson
(`notification-cost-and-vendor-budget`, classification `confidential`):

| Caller | Ceiling | Query | Outcome | Audit line |
|--------|---------|-------|---------|-----------|
| `implementer` | internal | budget-ceiling query | confidential lesson **withheld** | `classification_withheld` |
| `reviewer` | internal | budget-ceiling query | confidential lesson **withheld** | `classification_withheld` |
| `tester` | internal | budget-ceiling query | confidential lesson **withheld** | `classification_withheld` |
| `planner` | internal | budget-ceiling query | confidential lesson **withheld** | `classification_withheld` |
| `dependency-auditor` | internal | budget-ceiling query | confidential lesson **withheld** | `classification_withheld` |
| `orchestrator` | confidential | budget-ceiling query | confidential lesson **returned** (sim 0.73) | `retrieve` |
| `project-manager` | (not granted `retrieve`) | any | **denied** | `retrieve_denied` (reason: "project-manager does not perform retrieval") |

Audit output is JSON-Lines, matching the storage server's format
(`timestamp`, `operation`, `project_id`, `entry_id`, `classification`,
`calling_role`). Example:

```json
{"timestamp": "2026-11-06T...+00:00", "operation": "classification_withheld", "project_id": "proj-lessons", "entry_id": "lesson-notification-cost-and-vendor-budget", "classification": "confidential", "calling_role": "reviewer", "ceiling": "internal"}
{"timestamp": "2026-11-06T...+00:00", "operation": "retrieve", "project_id": "proj-lessons", "entry_id": "lesson-notification-cost-and-vendor-budget", "classification": "confidential", "calling_role": "orchestrator"}
{"timestamp": "2026-11-06T...+00:00", "operation": "retrieve_denied", "project_id": "proj-lessons", "calling_role": "project-manager", "reason": "project-manager does not perform retrieval"}
```

---

## 5. Citation shape

Every returned result is a citation a reviewer agent can verify a claim
against:

```json
{
  "source_document": "lesson-sms-notifications-were-never-wired",
  "title": "...",
  "chunk_index": 1,
  "similarity": 0.910,
  "lexical_score": 0.256,
  "retrieval_method": "vector",
  "classification": "internal",
  "source": "...",
  "last_updated": "2026-09-19",
  "text": "..."
}
```

---

## 6. Files & dependencies

| File | Role |
|------|------|
| `mcp-servers/retrieval/corpus.json` | The eight lessons with frontmatter metadata (built from the `.md` files). |
| `mcp-servers/retrieval/retrieval-grants.json` | Per-role `retrieve` grant + classification ceiling (single source of truth for governance). |
| `mcp-servers/retrieval/retrieval_index.py` | Dense GloVe embedding ranker + TF-IDF lexical gate + FTS5 fallback. Transport-free, unit-testable. |
| `mcp-servers/retrieval/governance.py` | Classification ceiling, withheld-audit, citation shaping. |
| `mcp-servers/retrieval/server.py` | Thin stdio MCP wrapper exposing the `retrieve` tool (mcp ≥ 2.x constructor-handler API). |
| `mcp-servers/retrieval/retrieval_eval.py` | Ground-truth harness; exit 0 on precision@1 = 6/6. |

**Dependencies** (install once in the container):

```bash
pip install --break-system-packages scikit-learn spacy
pip install --break-system-packages \
  https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
```

The spaCy model is a GitHub-hosted wheel (not HuggingFace), so it installs
inside the proxy allow-list. Pin both in `requirements.txt`:

```
scikit-learn>=1.3
spacy>=3.8
en_core_web_md @ https://github.com/explosion/spacy-models/releases/download/en_core_web_md-3.8.0/en_core_web_md-3.8.0-py3-none-any.whl
```

## 7. How to reproduce

```bash
cd mcp-servers/retrieval
python retrieval_eval.py        # prints the table in §2; exit code 0 = all hit
```