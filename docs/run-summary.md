# Run Summary: status-transition input validation

Date: 2026-11-03
Issue: Add input validation to the appointment status-transition route (`PATCH /appointments/<int:id>/status`).

## What changed
- `appointment-backend/app.py`
  - `update_appointment_status` now validates the request before any DB access. The body must be a JSON object, `status` must be present, and `status` must be a string in `VALID_STATUSES` (exact match, no trimming or case-folding). Errors do not echo raw input.
  - An `id < 1` guard returns 400. A scoped app-level 404 handler returns a JSON 400 for non-integer ids on `PATCH /appointments/<x>/status`. All other 404s are unchanged.
  - The missing-appointment 404 returns both `error` and `message` keys, because the frontend was not checked for dependence on `message`.
  - The 409 body now includes `current_status` and `allowed`.
  - The DB cursor and connection are closed in try/finally.
  - HTTP exceptions are re-raised and are no longer turned into 500. The generic 500 returns a generic message.
  - The docstring was updated.
- `appointment-backend/test_status_route.py` (new): validation, transition, not-found, same-status and connection-cleanup tests. It does not import `test_mysql.py`.
- `appointment-backend/requirements.txt`: added `pytest==8.4.2` (version not independently verified).

## Review outcome (appt-security-reviewer)
No Critical or High findings in the code introduced by this change. Acceptance criterion met.

Medium and Low findings are accepted as documented follow-ups (human decision, no loop back):
- Medium: race condition on the transition check. Fix with `UPDATE ... WHERE id=%s AND status=%s` and a `rowcount` check, or `SELECT ... FOR UPDATE`.
- Medium: the 409 `current_status` field plus sequential ids lets unauthenticated callers enumerate appointment states. This is mainly a consequence of there being no auth.
- Low: a notification-code failure after commit returns 500 although the status changed. The scoped 404 handler is imprecise (e.g. trailing slash). `except HTTPException` is dead code. Logging uses raw `print(e)`. pytest should move to a dev requirements file.
- Test gaps: valid-transition tests are generated from `STATUS_TRANSITIONS` itself. Transitions out of terminal states are untested. Several failure paths are untested. No tests show the 404 handler leaves other routes unchanged. The SELECT parameters are never asserted.
- Open item: the frontend was never grepped for use of the 404 `message` key. Both keys are returned until that is confirmed.
- Open item: the `pytest==8.4.2` pin is unverified.

Pre-existing issues, out of scope for this change:
- High: no authentication or authorisation on any state-changing route.
- High: `app.run(debug=True)`.
- Medium: CORS open to all origins.
- Medium: unauthenticated `/test-sms` and `/test-email` routes with hardcoded PII.
- Medium: unvalidated phone and email on POST and PUT.
- Low: connection leaks on other routes, and no `MAX_CONTENT_LENGTH`.
- `PUT /appointments/<id>` may accept `status` and bypass `STATUS_TRANSITIONS`. This was not checked.
- `test_mysql.py` connects to the DB at import and contains a hardcoded password.
- The retrieval server returned a confidential document above the agents' access ceiling. It was not used, but the server's classification filtering should be checked.

## Test outcome
appt-tester could not run because the `coursetools` MCP tools were unavailable. The human supplied the result of the deterministic step `scripts/run_tests_deterministic.py` (ADR-001): status "pass", exit_code 0, 23 passed in 1.03s. This result was reported by the human and was not independently re-run by the orchestrator. Acceptance criterion met on that basis.

## Pipeline notes
- Planner output was approved by the human before any code was written.
- The implementer made a stray `write_entry` call (key `noop`) to the storage MCP server. It carries no lesson and can be deleted.
- Final confirmation was given by the human.
