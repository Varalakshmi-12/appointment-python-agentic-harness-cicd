"""Autonomous deterministic test gate, run under the reliability + cost controls.

One command runs the gate end to end with NO human filling the tester gap: the
deterministic test step (ADR-001) executes under a timeout, retries a transient
*execution* error (never a test failure), and charges a per-run budget. Exits 0
only on a clean pass. This is the "run that passes the test gate without manual
help" — the gap the Orchestrator could not fill (it has no shell tool) is
closed by running the code-converted gate directly, with the controls active.

    python scripts/run_gate.py --tests eval/ --output gate-result.json

Prepared by: Varalakshmi
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import run_tests_deterministic as gate  # noqa: E402
from controls import (  # noqa: E402
    BudgetExceeded, ControlTimeout, MaxIterationsExceeded,
    WorkflowBudget, with_retries, with_timeout,
)

GATE_TIMEOUT_S = int(os.environ.get("GATE_TIMEOUT_S", "300"))
# The deterministic gate makes no model calls, so its real cost is ~0; the
# budget control is still active and logged, and it bounds a run that somehow
# retries many times. Overridable for a demo of the budget firing.
GATE_COST_USD = float(os.environ.get("GATE_COST_USD", "0.001"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default="eval/")
    ap.add_argument("--output", default="gate-result.json")
    ap.add_argument("--per-run-budget", type=float, default=0.50)
    args = ap.parse_args()

    budget = WorkflowBudget(per_call_usd=args.per_run_budget,
                            per_workflow_usd=args.per_run_budget)

    @with_timeout(GATE_TIMEOUT_S)
    @with_retries(retries=1, backoff_s=1.0, retry_on=(RuntimeError,))
    def run_once():
        budget.charge(GATE_COST_USD, label="deterministic-test-gate")
        status, code, output = gate.run_tests(args.tests)
        if status == "error":
            # transient execution error (not a test failure) -> retryable
            raise RuntimeError(f"gate execution error (pytest exit {code})")
        return status, code, output

    try:
        status, code, output = run_once()
    except (ControlTimeout, BudgetExceeded, MaxIterationsExceeded, RuntimeError) as exc:
        status, code, output = "error", -1, str(exc)

    result = {
        "status": status,              # "pass" | "fail" | "error"
        "exit_code": code,
        "tests_path": args.tests,
        "controls": {
            "timeout_s": GATE_TIMEOUT_S,
            "per_run_budget_usd": args.per_run_budget,
            "spent_usd": round(budget.spent, 6),
        },
        "output_tail": output.strip().splitlines()[-20:] if isinstance(output, str) else [],
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    print(f"gate status: {status} (controls active; spent ${budget.spent:.4f}, "
          f"timeout {GATE_TIMEOUT_S}s)")
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()