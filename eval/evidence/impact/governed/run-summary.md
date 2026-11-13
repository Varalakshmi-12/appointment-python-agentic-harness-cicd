# Run Summary: make appointment-backend/test_sms.py import-safe

## Defect and severity
Importing `appointment-backend/test_sms.py` executed top-level code that printed the Twilio credential variables (TWILIO_SID / TWILIO_AUTH / TWILIO_NUMBER) to stdout and attempted a live `client.messages.create()` call, so the module was not import-safe.

Severity: low to medium. The Twilio integration is not live and the credentials are dummy, so nothing was actually leaked or sent. Printing credentials is still a secret-exposure pattern, and the send attempt on import is a side-effect-on-import defect. Both would become real once live credentials are configured.

## What changed
- `appointment-backend/test_sms.py`: all executable code moved under `main()`, with `if __name__ == "__main__": main()`. The three credential prints were deleted. Direct-run behavior is unchanged (it may still send when run as a script), the recipient is still hardcoded, and no opt-in or fail-fast was added. No function is named `test_*`.
- `eval/test_sms_import_safe.py` (new): regression test that imports `test_sms` fresh with `twilio` stubbed and sockets blocked. It asserts nothing is printed on import, a sentinel credential value never appears in output, `Client` is never constructed, `messages.create` is never called, and the module top level contains only imports, function definitions and the `__main__` guard (AST check). It also asserts no `test_*` function exists in the module.

Not touched, per the user's scope decisions: `conftest.py` (the `collect_ignore` for `test_sms.py` remains), `app.py`, `test_mysql.py`, and all docs (left as historical evidence).

## Security review
Reviewer: appt-security-reviewer. Verdict: approve. 0 unresolved Critical, 0 High, 0 Medium findings. The review was read-only; the reviewer read the code and did not run it.

## Deterministic test gate
Run by the main session (the orchestrator has no shell): `python scripts/run_tests_deterministic.py --tests eval/` returned status "pass", exit_code 0, 40 passed, including the 3 new tests in `eval/test_sms_import_safe.py`. `result.json` was written to the session scratchpad, not the repo: `/tmp/claude-0/-workspace/b55c0f05-ee19-4faa-8481-3e239cdfcd8f/scratchpad/result.json`. The main session also read the final `test_sms.py` and confirmed all code is under `main()` with the `__main__` guard, no credential prints, recipient still hardcoded and no opt-in.

## Low items left out of scope
- The comment on line 1 of `appointment-backend/conftest.py` is stale (it still says `test_sms.py` sends a real SMS on import). The `collect_ignore` itself is intact.
- The AST check in the new test accepts any `if __name__ <compare>` guard, not only `== "__main__"`.
- `socket.getaddrinfo` is not patched in the network guard, so DNS lookups would not be caught.
- No test calls `main()` with the stub `Client` to check the direct-run path for credential leaks.
- If a real send hits a Twilio API error, the exception text may include the Account SID (an identifier, not the auth token).

## Status
Acceptance criteria met: change addresses the reported issue, no unresolved Critical findings, gate status "pass". Human confirmation to finalize was given.
