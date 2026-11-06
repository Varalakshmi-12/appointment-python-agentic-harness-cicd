# Decision 004 - No Raw Exception Text in API Responses

**Date:** 2026-09-03
**Review by:** 2026-12-02
**Status:** Implemented (2026-09-07) — all six routes in `appointment-backend/app.py` updated to log detailed errors server-side via `print` and return generic `{"error": ...}` messages with 400 (bad input, via KeyError/TypeError/AttributeError on request body access) or 500 (unexpected/DB errors) instead of `str(e)`. Existing 404 "not found" branches were already generic and left unchanged.

**Decision:** API routes must not return raw exception text (`str(e)`) to clients. On error, return a generic, safe message with the correct HTTP status code (400 bad input, 404 missing resource, 500 server error) and log the detailed error server-side.

**Rationale:** The original routes returned `str(e)` directly to callers, which leaks internal database and driver details -- an information-disclosure risk flagged in the security review. Separating the client-facing message from the server-side detail preserves debuggability (via server logs) without exposing internals to the outside.

**Alternatives rejected:** We rejected keeping `str(e)` in responses for easier debugging, since the disclosure risk outweighs the convenience and server-side logs provide the same debugging value safely. We also considered a central error handler but deferred it in favor of per-route handling until a logged decision introduces one.

**Checkable specifics:** Route handlers in `appointment-backend/app.py` should catch exceptions and return a generic `{"error": ...}` message (not `str(e)`) with an appropriate status code -- 400 for bad input, 404 for missing resources, 500 for unexpected server errors -- and the detailed exception should be logged server-side (e.g. via `print` or a logger) rather than sent in the response body.
