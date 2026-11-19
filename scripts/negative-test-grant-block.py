#!/usr/bin/env python3
"""Reproducible negative test: an unauthorized tool grant is blocked by the eval gate.

Demonstrates eval-gated change control end to end, so the "a change was blocked
because an evaluation failed" claim is reproducible rather than asserted:

  1. Introduce an unauthorized grant - the implementer gains ``delete_entry`` in
     the storage allow-list (contradicting its write-only charter).
  2. Run the governance enforcement test (eval/test_per_role_enforcement.py) - it
     FAILS, because the implementer is no longer denied.
  3. Run the CI gate (scripts/run_gate.py --tests eval/, the exact command the CI
     "Deterministic Test Gate" runs) - status FAIL, so the pull request would be
     blocked from merging.
  4. Correct the grant (restore the allow-list).
  5. Re-run - the enforcement test PASSES again.

The allow-list is restored in a ``finally`` block, so the repository is left clean
even if a step errors. A transcript is written to
eval/evidence/negative-test-grant-block.log. Exit code 0 only if the gate blocked
the unauthorized grant and passed the corrected one.

Usage (from the repository root):
    python scripts/negative-test-grant-block.py
"""
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
ALLOW = ROOT / "mcp-servers" / "storage" / "allow-list.json"
EVID = ROOT / "eval" / "evidence" / "negative-test-grant-block.log"
ENF_TEST = "eval/test_per_role_enforcement.py"

_lines: list[str] = []


def log(s: str = "") -> None:
    print(s)
    _lines.append(s)


def run(cmd: list[str]) -> tuple[int, str]:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr)


def main() -> int:
    original = ALLOW.read_text(encoding="utf-8")
    ok = True
    try:
        log("# Negative test - unauthorized tool grant blocked by the eval gate")
        log("# The allow-list is restored automatically; the repo is left clean.\n")

        # Step 1 - introduce the unauthorized grant.
        d = json.loads(original)
        d["delete_entry"] = sorted(set(d.get("delete_entry", []) + ["implementer"]))
        ALLOW.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
        log("Step 1 - introduced unauthorized grant: 'implementer' added to delete_entry in")
        log(f"         mcp-servers/storage/allow-list.json (delete_entry now: {d['delete_entry']}).\n")

        # Steps 2-3 - the governance enforcement test must FAIL.
        rc, out = run([sys.executable, "-m", "pytest", ENF_TEST, "-q"])
        log("Step 2 - ran the governance enforcement test (eval/test_per_role_enforcement.py):")
        for ln in out.strip().splitlines()[-4:]:
            log("           " + ln)
        test_failed = rc != 0
        log(f"         => test {'FAILED, as required' if test_failed else 'PASSED (UNEXPECTED)'}.\n")
        ok &= test_failed

        # Step 3 - the CI gate (what CI runs) must report fail, blocking the PR.
        rc_g, out_g = run([sys.executable, "scripts/run_gate.py", "--tests", "eval/",
                           "--output", "/tmp/_neg_gate_bad.json"])
        status = None
        try:
            status = json.load(open("/tmp/_neg_gate_bad.json")).get("status")
        except Exception:
            pass
        gate_line = [l for l in out_g.splitlines() if "gate status" in l]
        log("Step 3 - ran the CI gate (scripts/run_gate.py --tests eval/, the Deterministic Test Gate command):")
        if gate_line:
            log("           " + gate_line[-1])
        gate_blocked = status == "fail"
        log(f"         => gate status '{status}' => pull request "
            f"{'BLOCKED, as required' if gate_blocked else 'NOT blocked (UNEXPECTED)'}.\n")
        ok &= gate_blocked
    finally:
        # Step 4 - always correct the grant.
        ALLOW.write_text(original, encoding="utf-8")
        restored = ALLOW.read_text(encoding="utf-8") == original
        log("Step 4 - corrected the grant: restored mcp-servers/storage/allow-list.json "
            f"({'verified clean' if restored else 'RESTORE FAILED'}).\n")
        ok &= restored

    # Step 5 - re-run after correction; it passes.
    rc, out = run([sys.executable, "-m", "pytest", ENF_TEST, "-q"])
    log("Step 5 - re-ran the governance enforcement test after correction:")
    for ln in out.strip().splitlines()[-3:]:
        log("           " + ln)
    passed = rc == 0
    log(f"         => test {'PASSED, as required' if passed else 'FAILED (UNEXPECTED)'}.\n")
    ok &= passed

    log("RESULT: " + (
        "PASS - the eval gate blocked the unauthorized grant and passed the corrected one."
        if ok else "FAIL - the demonstration did not behave as required."))
    EVID.parent.mkdir(parents=True, exist_ok=True)
    EVID.write_text("\n".join(_lines) + "\n", encoding="utf-8")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())