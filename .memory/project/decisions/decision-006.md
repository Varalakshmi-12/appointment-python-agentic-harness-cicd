# Decision 006 - API Connection Approach

**Date:** 2026-09-05
**Review by:** 2026-12-04
**Status:** Active

**Decision:** We connect to the data API using a service account.

**Rationale:** The service account was set up by the infrastructure team. The API key is stored in the environment variable ANTHROPIC_API_KEY and must never be written into any memory file, knowledge file, or code. To use it, reference the environment variable only.

**Alternatives rejected:** Using personal credentials was rejected for security reasons.