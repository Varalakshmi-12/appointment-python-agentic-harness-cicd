"""Each reliability/cost control is shown FIRING (Production / safety limits).

Not a to-do list: every control raises its typed exception at the boundary and
logs a `fired` event to the controls log. Run:

    python -m pytest eval/test_controls.py -q

Prepared by: Varalakshmi
"""

import json
import os
import sys
import tempfile
import time

import pytest

_TMP = tempfile.mkdtemp()
os.environ["CONTROLS_LOG"] = os.path.join(_TMP, "controls-log.jsonl")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import controls  # noqa: E402
from controls import (  # noqa: E402
    BudgetExceeded, ControlTimeout, MaxIterationGuard, MaxIterationsExceeded,
    WorkflowBudget, with_retries, with_timeout,
)


def _fired(control: str) -> bool:
    """True if the controls log recorded a `fired` event for this control."""
    with open(os.environ["CONTROLS_LOG"], encoding="utf-8") as fh:
        return any(
            (r := json.loads(ln)).get("control") == control and r.get("event") == "fired"
            for ln in fh if ln.strip()
        )


def test_timeout_fires():
    @with_timeout(1)
    def slow():
        time.sleep(3)
    with pytest.raises(ControlTimeout):
        slow()
    assert _fired("timeout")


def test_retry_fires_then_succeeds():
    calls = {"n": 0}

    @with_retries(retries=2, backoff_s=0)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("transient")
        return "ok"

    assert flaky() == "ok"
    assert calls["n"] == 2
    assert _fired("retry")


def test_retry_exhausts_and_reraises():
    @with_retries(retries=1, backoff_s=0)
    def always_fails():
        raise ValueError("permanent")
    with pytest.raises(ValueError):
        always_fails()


def test_max_iteration_guard_fires():
    guard = MaxIterationGuard(phase="implement<->review", limit=2)
    with pytest.raises(MaxIterationsExceeded):
        guard.record_failure()  # count 1
        guard.record_failure()  # count 2 -> fires
    assert _fired("max_iterations")


def test_per_call_budget_fires():
    budget = WorkflowBudget(per_call_usd=0.05, per_workflow_usd=1.00)
    with pytest.raises(BudgetExceeded):
        budget.charge(0.20, label="oversized-call")
    assert _fired("budget")


def test_per_workflow_budget_fires():
    budget = WorkflowBudget(per_call_usd=1.00, per_workflow_usd=0.10)
    budget.charge(0.06, label="step-1")
    with pytest.raises(BudgetExceeded):
        budget.charge(0.06, label="step-2")  # 0.12 > 0.10 cap


def test_timeout_and_budget_never_retried():
    """A control exception must not be swallowed by the retry wrapper."""
    @with_retries(retries=3, backoff_s=0)
    def over_budget():
        raise BudgetExceeded("hard stop")
    with pytest.raises(BudgetExceeded):
        over_budget()