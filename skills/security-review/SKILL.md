---
name: security-review
description: Methodology the reviewer subagent follows to audit a code change for the appointment app — what to check, how to rate severity, and the gate rule. Use before a change reaches the test gate.
version: 1.0.0
---

# Security Review

Use this when reviewing a code diff before it reaches the test gate. Read-only: report
findings, never modify code.

## What to check (in order)
1. **Input validation** — every external input is validated before use (body shape, types,
   allowed values, normalization) *before* any database access.
2. **Injection** — no string-built SQL; parameterized queries only. No command or template
   injection.
3. **Secret exposure** — no hardcoded credentials, keys, or tokens anywhere in the diff.
4. **Information disclosure** — error responses do not leak internals (stack traces,
   internal IDs, DB errors) to unauthenticated callers.
5. **Authorization / authentication** — state-changing routes are authorized; object access
   checks ownership (guard against broken-object-level authorization, e.g. fetching a record
   by raw ID with no owner check).
6. **Resource safety** — connections and handles are closed on every path (try/finally);
   no leaks on the error path.
7. **Test honesty** — tests do not give false confidence (e.g. assertions generated from the
   same source they claim to verify; failure paths left untested).

## Severity
- **Critical** — exploitable now, or causes data loss/leak. Blocks the pipeline; send back
  to the implementer.
- **High** — serious but not directly exploitable in this change. Blocks unless explicitly
  accepted by the human.
- **Medium / Low** — record as follow-ups; do not block.

## Gate rule
Pass the security gate only when there are **no unresolved Critical findings**. List Medium
and Low findings for the human to decide. For any denied operation, cite
`docs/governance-policy.md`.

## Output
A findings list grouped by severity, each with `file:line` and a one-line fix. Separate
issues **introduced by this change** from **pre-existing** ones.

## Change log
- 1.0.0 — Initial version, extracted from the appt-security-reviewer agent definition and the
  findings pattern observed across runs (see `docs/calibration-log.md`).