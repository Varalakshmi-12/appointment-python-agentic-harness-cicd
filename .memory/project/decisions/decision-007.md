# Decision 007 - Appointment Status Transition Graph

**Date:** 2026-09-25
**Review by:** 2026-12-24
**Status:** Active

**Decision:** `PATCH /appointments/<id>/status` enforces a legal-transition graph in addition to the existing value-set check ([[decision-003]]). The allowed states are `scheduled`, `confirmed`, `completed`, `cancelled`, `no-show`. Legal transitions:

- `scheduled` -> `confirmed`, `cancelled`, `no-show`
- `confirmed` -> `completed`, `cancelled`, `no-show`
- `completed`, `cancelled`, `no-show` -> (terminal, no outbound transitions)

Resubmitting the appointment's current status (e.g. `confirmed` -> `confirmed`) is treated as an idempotent no-op and returns HTTP 200, not a transition error. Any other target that is not listed as reachable from the current status is rejected as HTTP 409. This is a distinct error case from an unrecognized status value, which remains HTTP 400 per [[decision-003]].

**Rationale:** `.memory/knowledge/coding-standards.md` prohibits adding a new state-machine pattern without a logged decision motivating it; this decision is that motivating record. It is prompted by `lesson-appointment-status-state-machine.md` (proj-lessons corpus), which documents a prior incident where a `cancelled` appointment was illegally reset back to `confirmed` with no server-side guard against it. `scheduled -> no-show` is legal because a patient can fail to show for an appointment that was never confirmed. Idempotent same-status resubmission returns 200 rather than 409 because PATCH is expected to be idempotent under HTTP semantics, and a duplicate request (double-click, client retry) should not surface as an error.

**Alternatives rejected:** Rejected making all terminal-state transitions (e.g. `cancelled -> confirmed`) return the generic 400 used for invalid values, since that would conflate "not a real status" with "a real status that isn't reachable from here" — the lesson calls for these to be distinguishable by the caller, so illegal transitions use 409 instead. Rejected requiring `no-show` to pass through `confirmed` first, since scheduling-without-confirmation is a normal clinic workflow state from which a no-show can occur directly.

**Checkable specifics:** `STATUS_TRANSITIONS` dict should appear in `appointment-backend/app.py` next to `VALID_STATUSES`, matching the graph above. `update_appointment_status` should: (1) reject unknown status values with 400 (per decision-003), (2) return 200 as a no-op when the target equals the appointment's current status, (3) reject any other target not present in `STATUS_TRANSITIONS[current_status]` with 409, (4) otherwise proceed with the update.
