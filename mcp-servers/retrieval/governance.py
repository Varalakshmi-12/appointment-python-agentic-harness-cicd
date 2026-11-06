"""
Retrieval governance: classification ceiling + withheld-audit + citations.

Kept separate from the MCP transport so it is unit-testable and so server.py
stays a thin wrapper: the tool handler calls retrieve_with_governance() and
returns its citations. This module is transport-agnostic (no MCP imports),
which is why it can be exercised by retrieval_eval/governance tests directly.

Classification model
--------------------
Three levels, least to most sensitive: public < internal < confidential.
Each calling role has a ceiling. A candidate above the caller's ceiling is
NOT returned; instead a `classification_withheld` line is written to the
audit log so the refusal is observable. Returned candidates get a `retrieve`
audit line. Citations carry the fields a reviewer agent needs to verify a
claim: source_document, chunk_index, similarity, retrieval_method,
classification.

Prepared by: Varalakshmi
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from retrieval_index import Candidate, RetrievalIndex

CLASSIFICATION_ORDER = ["public", "internal", "confidential"]

PROJECT_ID = "proj-lessons"

# The per-role retrieve grant map is DATA, not code: it is read from
# retrieval-grants.json (the single source of truth, also referenced by the
# routing/tool-grant map). Role names are normalized (underscores -> hyphens,
# lower-cased) so "project_manager" and "project-manager" resolve the same.
_GRANTS_PATH = os.path.join(_HERE_DIR := os.path.dirname(os.path.abspath(__file__)),
                            "retrieval-grants.json")


def _load_grants() -> dict:
    with open(_GRANTS_PATH, encoding="utf-8") as fh:
        raw = json.load(fh)["retrieve"]
    return {role.replace("_", "-").lower(): spec for role, spec in raw.items()}


RETRIEVE_GRANTS = _load_grants()


def _grant_for(calling_role: str) -> dict | None:
    return RETRIEVE_GRANTS.get(calling_role.strip().replace("_", "-").lower())


def _rank(level: str) -> int:
    return CLASSIFICATION_ORDER.index(level)


def _audit(audit_path: str, record: dict) -> None:
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), **record}
    os.makedirs(os.path.dirname(audit_path), exist_ok=True) if os.path.dirname(audit_path) else None
    with open(audit_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def retrieve_with_governance(
    index: RetrievalIndex,
    query: str,
    calling_role: str,
    audit_path: str,
    limit: int = 5,
) -> list[dict]:
    """Rank, enforce the caller's classification ceiling, audit, return citations."""
    grant = _grant_for(calling_role)
    if grant is None or not grant.get("granted"):
        reason = (grant or {}).get("denial_reason", "role_not_authorized_to_retrieve")
        _audit(audit_path, {
            "operation": "retrieve_denied", "project_id": PROJECT_ID,
            "calling_role": calling_role, "reason": reason,
        })
        raise PermissionError(f"role {calling_role!r} is not authorized to retrieve: {reason}")

    ceiling = grant["classification_ceiling"]
    # over-fetch so withheld confidential docs don't starve the result set
    candidates: list[Candidate] = index.search(query, limit=limit + 3)

    citations: list[dict] = []
    for c in candidates:
        if _rank(c.classification) > _rank(ceiling):
            _audit(audit_path, {
                "operation": "classification_withheld", "project_id": PROJECT_ID,
                "entry_id": c.doc_id, "classification": c.classification,
                "calling_role": calling_role, "ceiling": ceiling,
            })
            continue
        _audit(audit_path, {
            "operation": "retrieve", "project_id": PROJECT_ID,
            "entry_id": c.doc_id, "classification": c.classification,
            "calling_role": calling_role,
        })
        citations.append({
            "source_document": c.doc_id,
            "title": c.title,
            "chunk_index": c.chunk_index,
            "similarity": c.similarity,
            "retrieval_method": c.retrieval_method,
            "classification": c.classification,
            "source": c.source,
            "last_updated": c.last_updated,
            "text": c.text,
        })
        if len(citations) >= limit:
            break
    return citations
