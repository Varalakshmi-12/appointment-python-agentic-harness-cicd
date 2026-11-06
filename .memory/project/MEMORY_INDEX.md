# Project Memory Index

Last updated: 2026-09-05

## Active entries

- `decisions/decision-001.md` — Appointment status is changed via a dedicated PATCH /appointments/<id>/status endpoint (not via PUT), to avoid the misleading "updated" notification and to validate status values. Recorded 2026-08-25. Review by 2026-11-23.

- `decisions/decision-002.md` — Test files go in a dedicated /tests directory, not alongside source. Existing tests not yet migrated. Recorded 2026-09-03. Review by 2026-12-02.

- `decisions/decision-003.md` — Appointment status values are validated server-side via a VALID_STATUSES set (scheduled/confirmed/cancelled/completed/no-show) on both POST /appointments and PATCH /appointments/<id>/status, rejecting invalid values with 400. See decision-001 for the VARCHAR-vs-ENUM storage choice; see decision-007 for the transition-graph check. Recorded 2026-09-03. Review by 2026-12-04.

- `decisions/decision-004.md` — API routes must not return raw exception text (str(e)) to clients; return a safe message with correct status code (400/404/500) and log details server-side. Per-route handling for now, no central error handler yet. Recorded 2026-09-03. Review by 2026-12-02.

- `decisions/decision-005.md` — PATCH /appointments/<id>/status sends status-specific SMS/email (not PUT's generic "updated" message); notification failures are caught and don't fail the status update. Twilio SMS is unwired (empty env vars) in this deployment. See decision-001. Recorded 2026-09-03. Review by 2026-12-02.

- `decisions/decision-006.md` — API connections to the data API use a service account; the key is stored in the ANTHROPIC_API_KEY environment variable and must never be written into any memory file, knowledge file, or code. Recorded 2026-09-05. Review by 2026-12-04. (Remediated from a prior version, `decision-bad.md`, that had a key-like string hardcoded in the rationale.)

- `decisions/decision-007.md` — PATCH /appointments/<id>/status enforces a legal status-transition graph (scheduled->confirmed/cancelled/no-show; confirmed->completed/cancelled/no-show; others terminal) on top of decision-003's value check; illegal transitions return 409, same-status resubmission is an idempotent 200. Motivated by lesson-appointment-status-state-machine.md (proj-lessons). Recorded 2026-09-25. Review by 2026-12-24.

- `../knowledge/coding-standards.md` — Coding standards for this project (parameterized SQL, env-var secrets, input validation, no ORM, controlled-input frontend). Human-maintained, read-only. Last reviewed 2026-08-25.

## Archived entries

(none yet)

## Pruning schedule

- Workflow-scoped entries: archived when the branch merges to main
- Project-scoped entries: reviewed every 90 days
