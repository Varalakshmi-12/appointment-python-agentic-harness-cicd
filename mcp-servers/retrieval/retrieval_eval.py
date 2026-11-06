"""
Ground-truth evaluation for the retrieval engine.

Six queries, each with the single lesson a reviewer agent should retrieve.
Reports top-1 hit, the winning score, and the margin over the runner-up, so
the similarity floor and ranker quality are verifiable rather than asserted.

Run: python retrieval_eval.py
Prepared by: Varalakshmi
"""

from retrieval_index import RetrievalIndex, SIMILARITY_FLOOR

GROUND_TRUTH = [
    ("Q1", "Why did SMS appointment reminders never reach patients?",
     "lesson-sms-notifications-were-never-wired"),
    ("Q2", "How should we handle failures returned by the appointment API routes?",
     "lesson-standardize-route-error-handling"),
    ("Q3", "cursor connection leak too many connections",
     "lesson-mysql-cursor-and-connection-leaks"),
    ("Q4", "What is the monthly budget ceiling for patient notifications?",
     "lesson-notification-cost-and-vendor-budget"),
    ("Q5", "How should appointment status changes be validated?",
     "lesson-appointment-status-state-machine"),
    ("Q6", "Appointment shows the wrong time to patients in another timezone",
     "lesson-store-appointment-times-in-utc"),
]


def main() -> int:
    idx = RetrievalIndex()
    hits = 0
    print(f"similarity_floor = {SIMILARITY_FLOOR}\n")
    print(f"{'ID':<4}{'top-1 hit':<10}{'score':<9}{'margin':<9}method")
    for qid, query, expected in GROUND_TRUTH:
        results = idx.search(query, limit=3)
        top = results[0]
        runner = results[1].similarity if len(results) > 1 else 0.0
        hit = top.doc_id == expected
        hits += hit
        print(f"{qid:<4}{('HIT' if hit else 'MISS'):<10}"
              f"{top.similarity:<9.3f}{top.similarity - runner:<9.3f}{top.retrieval_method}")
    print(f"\nprecision@1 = {hits}/{len(GROUND_TRUTH)}")
    return 0 if hits == len(GROUND_TRUTH) else 1


if __name__ == "__main__":
    raise SystemExit(main())
