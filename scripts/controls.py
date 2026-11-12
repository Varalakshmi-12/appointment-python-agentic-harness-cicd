"""Reliability and cost controls for the agentic pipeline.

Four controls, each of which logs a structured event to logs/controls-log.jsonl
when it engages, so "the control fired" is observable evidence rather than an
assertion:

  * with_timeout(seconds)          - abort a step that runs too long (ControlTimeout)
  * with_retries(retries, backoff) - retry a transient failure with backoff
  * MaxIterationGuard(phase, limit)- stop an agent loop that will not converge
  * WorkflowBudget(per_call, per_workflow) - cap spend per call and per run

These wrap the deterministic parts of the pipeline (the test gate, tool calls,
the review loop). See scripts/run_gate.py for the test gate run under all four,
and eval/test_controls.py for each control shown firing.

Prepared by: Varalakshmi
"""

from __future__ import annotations

import functools
import json
import os
import signal
import time
from datetime import datetime, timezone

CONTROLS_LOG = os.environ.get("CONTROLS_LOG", "logs/controls-log.jsonl")


class ControlTimeout(Exception):
    """Raised when a step exceeds its time budget."""


class BudgetExceeded(Exception):
    """Raised when a per-call or per-workflow cost budget is exceeded."""


class MaxIterationsExceeded(Exception):
    """Raised when a phase retries past its iteration ceiling."""


def _log(control: str, event: str, **fields) -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "control": control,
        "event": event,
        **fields,
    }
    path = CONTROLS_LOG
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


# -- 1. timeout ---------------------------------------------------------------
def with_timeout(seconds: int):
    """Decorator: abort the wrapped call if it runs longer than `seconds`.

    Uses SIGALRM (Unix). Logs a `fired` event and raises ControlTimeout.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def _handler(signum, frame):
                _log("timeout", "fired", limit_s=seconds, label=func.__name__)
                raise ControlTimeout(f"{func.__name__} exceeded {seconds}s")

            old = signal.signal(signal.SIGALRM, _handler)
            signal.alarm(seconds)
            try:
                return func(*args, **kwargs)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old)
        return wrapper
    return decorator


# -- 2. retry -----------------------------------------------------------------
def with_retries(retries: int = 2, backoff_s: float = 0.0,
                 retry_on: tuple[type[Exception], ...] = (Exception,)):
    """Decorator: retry a transient failure up to `retries` times with backoff.

    Logs a `retry` event per attempt and `exhausted` if all attempts fail.
    ControlTimeout/BudgetExceeded/MaxIterationsExceeded are never retried.
    """
    never = (ControlTimeout, BudgetExceeded, MaxIterationsExceeded)

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while True:
                try:
                    return func(*args, **kwargs)
                except never:
                    raise
                except retry_on as exc:
                    attempt += 1
                    if attempt > retries:
                        _log("retry", "exhausted", attempts=attempt, label=func.__name__,
                             error=str(exc)[:200])
                        raise
                    _log("retry", "fired", attempt=attempt, of=retries, label=func.__name__,
                         error=str(exc)[:200])
                    if backoff_s:
                        time.sleep(backoff_s * attempt)
        return wrapper
    return decorator


# -- 3. max-iteration guard ---------------------------------------------------
class MaxIterationGuard:
    """Stop an agent loop (e.g. implementer <-> reviewer) that will not converge.

    Call record_failure() each time the phase fails to pass; it raises
    MaxIterationsExceeded once the limit is reached.
    """

    def __init__(self, phase: str, limit: int = 2):
        self.phase = phase
        self.limit = limit
        self.count = 0

    def record_failure(self) -> None:
        self.count += 1
        if self.count >= self.limit:
            _log("max_iterations", "fired", phase=self.phase, limit=self.limit)
            raise MaxIterationsExceeded(
                f"phase '{self.phase}' failed {self.count} times (limit {self.limit})"
            )
        _log("max_iterations", "record", phase=self.phase, count=self.count, limit=self.limit)


# -- 4. cost budget -----------------------------------------------------------
class WorkflowBudget:
    """Cap spend per call and across the whole workflow (USD).

    charge(usd, label) adds to the running total and raises BudgetExceeded if
    either the per-call or the per-workflow cap is crossed.
    """

    def __init__(self, per_call_usd: float, per_workflow_usd: float):
        self.per_call = per_call_usd
        self.per_workflow = per_workflow_usd
        self.spent = 0.0

    def charge(self, usd: float, label: str = "") -> float:
        if usd > self.per_call:
            _log("budget", "fired", scope="per_call", charge=usd, cap=self.per_call, label=label)
            raise BudgetExceeded(f"call '{label}' cost ${usd:.4f} > per-call cap ${self.per_call:.4f}")
        if self.spent + usd > self.per_workflow:
            _log("budget", "fired", scope="per_workflow", charge=usd,
                 spent=self.spent, cap=self.per_workflow, label=label)
            raise BudgetExceeded(
                f"workflow spend ${self.spent + usd:.4f} > per-workflow cap ${self.per_workflow:.4f}"
            )
        self.spent += usd
        _log("budget", "charge", charge=usd, spent=self.spent, cap=self.per_workflow, label=label)
        return self.spent