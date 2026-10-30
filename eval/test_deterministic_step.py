"""Unit tests for the deterministic tester's result-classification logic.

The real decision logic is the pure function classify_exit_code: given a
pytest exit code, it returns pass / fail / error. Keeping that logic pure
(no subprocess, no files) is what makes it directly testable.
"""

import sys
from pathlib import Path

# Make the script importable when pytest runs from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from run_tests_deterministic import classify_exit_code


# --- Three representative outcomes (the states the step must report) --------
def test_all_passed_is_pass():
    assert classify_exit_code(0) == "pass"


def test_some_failed_is_fail():
    assert classify_exit_code(1) == "fail"


def test_no_tests_collected_is_error():
    # pytest exit 5 = no tests collected. A naive check might treat this as a
    # pass; the step must report that the suite did not actually run.
    assert classify_exit_code(5) == "error"


# --- Edge cases the agent handled: an un-runnable suite is not a failure ----
def test_internal_error_is_error():
    assert classify_exit_code(3) == "error"


def test_usage_error_is_error():
    assert classify_exit_code(4) == "error"


# --- The limitation from the classification doc: three states, not two ------
# "exit code != 0 -> fail" would wrongly label an un-runnable suite as a test
# failure. These pin the pass / fail / error distinction, so a future change
# that collapsed it back to two states turns red immediately.
def test_interrupted_is_error_not_fail():
    assert classify_exit_code(2) == "error"
    assert classify_exit_code(2) != "fail"