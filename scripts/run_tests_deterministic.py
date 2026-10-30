#!/usr/bin/env python3
"""Deterministic replacement for the agentic appt-tester step.

Runs the project's test suite with pytest, classifies the outcome as
pass / fail / error, and writes a structured result document to a named
output file. No language model is involved.

The agentic appt-tester had no working test tool in this environment
(coursetools test_runner missing, Bash disallowed), so the pipeline halted
at the tester gate (calibration log, Holdout gap #2). This script runs
pytest directly and returns a verdict both the Orchestrator and CI can read.

Usage:
    python scripts/run_tests_deterministic.py --tests eval/ --output result.json
"""

import argparse
import json
import subprocess
import sys


# pytest exit codes (docs.pytest.org/en/stable/reference/exit-codes.html):
#   0  all collected tests passed
#   1  tests were collected and run, but some failed
#   2  test execution was interrupted
#   3  internal error
#   4  pytest usage/command-line error
#   5  no tests were collected
def classify_exit_code(code):
    """Map a pytest exit code to one of three states: pass / fail / error.

    This is the limitation the agent used to handle by judgment: a run that
    could NOT execute (interrupted, internal/usage error, or no tests
    collected) is not a test *failure*. A naive 'code == 0 -> pass else fail'
    check would mislabel every one of those as a failure. Returning 'error'
    preserves the three-state distinction the deterministic version must keep.
    """
    if code == 0:
        return "pass"
    if code == 1:
        return "fail"
    return "error"


def run_tests(tests_path):
    """Run pytest on tests_path; return (status, returncode, combined_output)."""
    completed = subprocess.run(
        [sys.executable, "-m", "pytest", tests_path, "-q"],
        capture_output=True,
        text=True,
    )
    output = completed.stdout + completed.stderr
    status = classify_exit_code(completed.returncode)
    return status, completed.returncode, output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tests", default="eval/", help="path to the tests to run")
    parser.add_argument("--output", required=True, help="path to write the result file")
    args = parser.parse_args()

    status, returncode, output = run_tests(args.tests)

    # Output goes to a NAMED FILE, never stdout, so a CI log step cannot sweep
    # up content that should not be archived (same least-privilege discipline
    # used for the governed agents).
    result = {
        "status": status,            # "pass" | "fail" | "error"
        "exit_code": returncode,
        "tests_path": args.tests,
        # Keep the last lines so a reviewer sees failing-test names / errors
        # (the detail the agent used to explain) without re-running anything.
        "output_tail": output.strip().splitlines()[-20:],
    }
    with open(args.output, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    # Exit non-zero on anything that is not a clean pass, so the Orchestrator
    # and CI both detect it. Both "fail" and "error" are non-zero.
    sys.exit(0 if status == "pass" else 1)


if __name__ == "__main__":
    main()