# Decision 001 - Dedicated PATCH Endpoint for Status

**Date:** 2026-08-25
**Review by:** 2026-11-23
**Status:** Active

**Decision:** We chose to implement the appointment status field through a dedicated PATCH /appointments/<id>/status endpoint instead of folding status into the existing PUT route.

**Rationale:** The PUT route always fires an "updated to {time}" SMS/email on every call, so routing status changes through PUT would send a misleading notification on a status-only change. A dedicated PATCH endpoint decouples lifecycle changes from detail edits, allows accurate per-transition notifications, and gives a clean place to validate allowed status values.

**Alternatives rejected:** We rejected Approach A (adding status to PUT) because it would trigger the misleading "updated to {time}" notification on status-only changes. We also rejected a DB-level ENUM in favor of a VARCHAR column with app-level validation, to match the existing schema style.
