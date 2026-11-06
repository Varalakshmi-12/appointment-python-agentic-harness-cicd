# Decision 002 - Separate /tests Directory for Test Files

**Date:** 2026-09-03
**Review by:** 2026-12-02
**Status:** Active

**Decision:** Test files will be organized in a dedicated `/tests` directory
rather than alongside the source files they test.

**Rationale:** Recorded per user request on 2026-09-03. (No further rationale
was given in the conversation.)

**Current state note:** Existing test files (`appointment-backend/test_mysql.py`,
`appointment-backend/test_sms.py`) are not yet moved under this convention as of
2026-09-03. This decision governs go-forward organization; migrating existing
files is a separate, not-yet-scheduled task.
