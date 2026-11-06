# Decision 005 - Status-Specific, Failure-Tolerant Notifications on PATCH

**Date:** 2026-09-03
**Review by:** 2026-12-02
**Status:** Active

**Decision:** The `PATCH /appointments/<id>/status` endpoint sends a status-specific notification (SMS + email) describing the new status, rather than the generic "updated to {time}" message the PUT route sends. Notification sending is wrapped so that a failure to send does not fail the status update itself.

**Rationale:** Accurate, per-transition notifications are the core reason status changes live in their own PATCH endpoint (see [[decision-001]]) -- PUT's always-on "updated" notice would be misleading on a status-only change. Wrapping the send in a try/except means a notification-provider outage doesn't roll back or block a valid DB update.

**Alternatives rejected:** We rejected reusing PUT's generic "updated to {time}" notification, since it would misdescribe a status-only change (e.g. a cancellation). We also rejected making the DB update depend on notification success, since an external provider failure should not prevent a valid status change from being recorded.

**Checkable specifics:** In `appointment-backend/app.py`, `update_appointment_status` should build its message from a per-status mapping (not the generic PUT message), call `send_sms` and `send_email` after the DB commit, and catch/log (not raise) any email-send exception so the 200 response is still returned. Note that in this deployment, `TWILIO_SID`/`TWILIO_AUTH`/`TWILIO_NUMBER` are unset in `appointment-backend/.env`, so `send_sms` currently fails and is caught internally (logged, returns `False`) -- the SMS path is exercised in code but not functionally wired up here.
