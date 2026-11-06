# Decision 003 - Application-Level Status Validation

**Date:** 2026-09-03
**Review by:** 2026-12-04
**Status:** Active

**Decision:** Allowed appointment status values are enforced in application code via a `VALID_STATUSES` set (`scheduled`, `confirmed`, `cancelled`, `completed`, `no-show`), checked on both `POST /appointments` and `PATCH /appointments/<id>/status`, with any value outside the set rejected as HTTP 400. `PATCH /appointments/<id>/status` additionally enforces a legal-transition graph on top of this value check; see [[decision-007]].

**Rationale:** Centralizing the allowed-values check in one constant next to the routes keeps validation logic in a single, easy-to-find place, and makes adding a new status a one-line code change rather than a schema migration. The API must not rely on the frontend `<select>` to constrain values, since a client can send arbitrary input directly to the API.

**Alternatives rejected:** We rejected trusting the frontend `<select>` as the sole constraint on status values, because the API must validate server-side regardless of what the UI restricts. (See [[decision-001]] for the related decision to store status as VARCHAR rather than a DB-level ENUM.)

**Checkable specifics:** `VALID_STATUSES = {"scheduled", "confirmed", "cancelled", "completed", "no-show"}` should appear in `appointment-backend/app.py`; both the `create_appointment` (POST `/appointments`) and `update_appointment_status` (PATCH `/appointments/<id>/status`) handlers should check submitted status values against this set and return HTTP 400 with an error message when a value is not in the set. See [[decision-007]] for the transition-graph check layered on top of this for the PATCH route.
