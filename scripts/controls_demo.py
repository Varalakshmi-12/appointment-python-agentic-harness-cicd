"""Demonstrate each reliability/cost control FIRING, once, in one run.

Prints a line as each control engages and records the `fired` events to
eval/evidence/controls-firing-evidence.jsonl (override with CONTROLS_LOG). This
is the "show each one firing" artifact: run it and watch all five fire.

    python scripts/controls_demo.py

Prepared by: Varalakshmi
"""

import os
import sys
import time

os.environ.setdefault("CONTROLS_LOG", "eval/evidence/controls-firing-evidence.jsonl")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from controls import (  # noqa: E402
    BudgetExceeded, ControlTimeout, MaxIterationGuard, MaxIterationsExceeded,
    WorkflowBudget, with_retries, with_timeout,
)


def main() -> None:
    log = os.environ["CONTROLS_LOG"]
    parent = os.path.dirname(log)
    if parent:
        os.makedirs(parent, exist_ok=True)
    open(log, "w").close()  # start fresh so the file holds exactly this run

    print("Firing each control once:\n")

    # 1. timeout
    @with_timeout(1)
    def slow():
        time.sleep(2)
    try:
        slow()
    except ControlTimeout as e:
        print(f"  1. timeout        -> FIRED  ({e})")

    # 2. retry (transient error, then succeeds)
    attempts = {"n": 0}

    @with_retries(retries=2, backoff_s=0)
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 2:
            raise ValueError("transient model/API error")
        return "ok"

    flaky()
    print(f"  2. retry          -> FIRED  (retried {attempts['n'] - 1}x, then succeeded)")

    # 3. max-iteration guard
    guard = MaxIterationGuard(phase="implement<->review", limit=2)
    try:
        guard.record_failure()
        guard.record_failure()
    except MaxIterationsExceeded as e:
        print(f"  3. max-iterations -> FIRED  ({e})")

    # 4. per-call budget
    try:
        WorkflowBudget(per_call_usd=0.05, per_workflow_usd=1.00).charge(0.20, "oversized-call")
    except BudgetExceeded as e:
        print(f"  4. per-call budget-> FIRED  ({e})")

    # 5. per-workflow budget
    try:
        b = WorkflowBudget(per_call_usd=1.00, per_workflow_usd=0.10)
        b.charge(0.06, "step-1")
        b.charge(0.06, "step-2")
    except BudgetExceeded as e:
        print(f"  5. per-workflow   -> FIRED  ({e})")

    print(f"\nAll five fired. Evidence written to {log}")


if __name__ == "__main__":
    main()