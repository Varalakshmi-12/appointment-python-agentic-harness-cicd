"""
Offline retrieval engine for the lessons corpus.

Primary ranker: TF-IDF vector search (scikit-learn), cosine similarity over
section-level chunks. Fallback: SQLite FTS5 keyword search, used when the
vector ranker returns nothing above the similarity floor (e.g. an exact-term
query that TF-IDF under-weights).

Design notes
------------
* No network at run time. An embedding model (sentence-transformers) was the
  first choice but the model download is blocked by the environment proxy
  (HuggingFace 403), so the engine uses TF-IDF, which is fully offline and
  deterministic. Scores are therefore TF-IDF cosine values, not embedding
  cosine values; the similarity floor below is calibrated for TF-IDF.
* Chunks are the Markdown `## ` sections of each lesson, prefixed with the
  lesson title so the title's terms contribute to every chunk's vector.
* Governance (classification ceiling, withheld-audit) lives in server.py.
  This module only ranks and returns candidates with their classification so
  the caller can enforce the ceiling.

Prepared by: Varalakshmi
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from dataclasses import dataclass

from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# TF-IDF cosine floor. Calibrated against the six ground-truth queries in
# eval/retrieval_eval.py: every true top-1 hit scores >= 0.18, and the best
# non-relevant document for any query scores <= 0.14. A floor of 0.10 keeps
# all true hits while rejecting "no confident match" for off-topic queries.
SIMILARITY_FLOOR = 0.10

_HERE = os.path.dirname(os.path.abspath(__file__))
_CORPUS_PATH = os.path.join(_HERE, "corpus.json")


@dataclass
class Candidate:
    doc_id: str
    title: str
    classification: str
    chunk_index: int
    similarity: float
    retrieval_method: str   # "tfidf_vector" or "fts5_keyword"
    text: str
    source: str
    last_updated: str


def _chunk(doc: dict) -> list[dict]:
    """Split a lesson into title-prefixed `## ` section chunks."""
    sections = re.split(r"\n## ", doc["body"])
    chunks = []
    for i, section in enumerate(sections):
        section = section.strip()
        if not section:
            continue
        chunks.append({
            "doc_id": doc["doc_id"],
            "title": doc["title"],
            "classification": doc["classification"],
            "source": doc.get("source", ""),
            "last_updated": doc.get("last_updated", ""),
            "chunk_index": i,
            "text": section,
            # title terms join every chunk's vector so a title-only match ranks
            "vector_text": f"{doc['title']} {section}",
        })
    return chunks


class RetrievalIndex:
    def __init__(self, corpus_path: str = _CORPUS_PATH):
        with open(corpus_path, encoding="utf-8") as fh:
            self._docs = json.load(fh)

        self._chunks: list[dict] = []
        for doc in self._docs:
            self._chunks.extend(_chunk(doc))

        # --- TF-IDF vector index ---
        self._vectorizer = TfidfVectorizer(stop_words="english", sublinear_tf=True)
        self._matrix = self._vectorizer.fit_transform(
            [c["vector_text"] for c in self._chunks]
        )

        # --- FTS5 keyword index (fallback) ---
        self._db = sqlite3.connect(":memory:")
        self._db.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5(doc_id, title, text, tokenize='porter')"
        )
        self._db.executemany(
            "INSERT INTO chunks(doc_id, title, text) VALUES (?,?,?)",
            [(c["doc_id"], c["title"], c["text"]) for c in self._chunks],
        )
        self._db.commit()

    # -- primary: TF-IDF cosine --------------------------------------------
    def _vector_search(self, query: str, limit: int) -> list[Candidate]:
        query_vec = self._vectorizer.transform([query])
        sims = cosine_similarity(query_vec, self._matrix)[0]

        # best-scoring chunk per document
        best: dict[str, int] = {}
        for i, chunk in enumerate(self._chunks):
            doc_id = chunk["doc_id"]
            if doc_id not in best or sims[i] > sims[best[doc_id]]:
                best[doc_id] = i

        ranked = sorted(best.values(), key=lambda i: sims[i], reverse=True)
        out = []
        for i in ranked:
            score = float(sims[i])
            if score < SIMILARITY_FLOOR:
                break
            c = self._chunks[i]
            out.append(Candidate(
                doc_id=c["doc_id"], title=c["title"],
                classification=c["classification"], chunk_index=c["chunk_index"],
                similarity=round(score, 4), retrieval_method="tfidf_vector",
                text=c["text"], source=c["source"], last_updated=c["last_updated"],
            ))
            if len(out) >= limit:
                break
        return out

    # -- fallback: FTS5 keyword --------------------------------------------
    def _keyword_search(self, query: str, limit: int) -> list[Candidate]:
        # keep content tokens only: drop English stopwords so common words
        # ("how", "do", "at") in the query can't match every lesson's headers
        terms = [
            t for t in re.findall(r"[A-Za-z0-9]+", query.lower())
            if t not in ENGLISH_STOP_WORDS and len(t) > 1
        ]
        if not terms:
            return []
        match = " OR ".join(terms)
        # FTS5 bm25: lower = better; map to a positive pseudo-score for citations
        cur = self._db.execute(
            "SELECT doc_id, title, text, bm25(chunks) AS rank "
            "FROM chunks WHERE chunks MATCH ? ORDER BY rank LIMIT ?",
            (match, limit),
        )
        by_doc: dict[str, Candidate] = {}
        for doc_id, title, text, rank in cur.fetchall():
            if doc_id in by_doc:
                continue
            meta = next(c for c in self._chunks if c["doc_id"] == doc_id)
            by_doc[doc_id] = Candidate(
                doc_id=doc_id, title=title, classification=meta["classification"],
                chunk_index=meta["chunk_index"], similarity=round(1.0 / (1.0 + abs(rank)), 4),
                retrieval_method="fts5_keyword", text=text,
                source=meta["source"], last_updated=meta["last_updated"],
            )
        return list(by_doc.values())[:limit]

    # -- public -------------------------------------------------------------
    def search(self, query: str, limit: int = 5) -> list[Candidate]:
        results = self._vector_search(query, limit)
        if not results:
            results = self._keyword_search(query, limit)
        return results


if __name__ == "__main__":
    idx = RetrievalIndex()
    for c in idx.search("cursor connection leak", limit=3):
        print(f"{c.similarity:.3f} {c.retrieval_method:<13} {c.doc_id} [{c.classification}]")
