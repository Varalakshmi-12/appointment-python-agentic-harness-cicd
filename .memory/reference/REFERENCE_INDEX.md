# Reference Index

Last updated: 2026-11-06

## Indexed reference documents

The project-lessons corpus (project: proj-lessons). These are the durable,
cross-session lessons the retrieval server ranks on demand; the same set is
indexed for search in `mcp-servers/retrieval/corpus.json`. Each lesson carries a
classification the retrieval server enforces against the calling role's ceiling,
so a confidential lesson is never returned to an internal-ceiling role.

- `lesson-appointment-status-state-machine.md` — Appointment status must be a validated state machine, not a free-text field. Classification: internal. Last updated 2026-09-19. Supersedes the pruned status-transition lesson (see Pruned entries).
- `lesson-cors-config-for-react-frontend.md` — React frontend was blocked by missing CORS configuration. Classification: internal. Last updated 2026-09-19.
- `lesson-mysql-cursor-and-connection-leaks.md` — Unclosed MySQL cursors exhausted connections under light load. Classification: internal. Last updated 2026-09-19.
- `lesson-notification-cost-and-vendor-budget.md` — Patient-notification vendor costs and monthly budget ceiling. Classification: confidential (negotiated rates and spend ceiling; must not surface to internal-ceiling roles). Last updated 2026-09-19.
- `lesson-sms-notifications-were-never-wired.md` — SMS reminders looked implemented but never reached patients. Classification: internal. Last updated 2026-09-19.
- `lesson-standardize-route-error-handling.md` — Routes leaked raw exceptions instead of a consistent error response. Classification: internal. Last updated 2026-09-19.
- `lesson-store-appointment-times-in-utc.md` — Appointment times stored in server-local time displayed wrong to patients. Classification: internal. Last updated 2026-09-19.
- `lesson-validate-input-at-the-route-boundary.md` — CRUD routes trusted the request body and accepted unintended fields. Classification: internal. Last updated 2026-09-19.

## Purpose

This layer holds the project-lessons corpus: durable lessons that are consulted
on demand through retrieval rather than loaded into every session. Each lesson is
a short "what happened / what was learned / how to apply it" record. The retrieval
server (`mcp-servers/retrieval`) ranks these by dense-vector similarity and enforces
each lesson's classification against the calling role's ceiling.

## Pruned entries

- Status-transition lesson (superseded 2026-11-06). The earlier status-transition
  lesson was pruned because its transition table no longer matched the authoritative
  rule in decision-007; it was replaced by
  `lesson-appointment-status-state-machine.md`. The removal and its written reason
  are recorded in `docs/reflection-log.md` (Memory curation) so curation is auditable.

## Maintenance

- A lesson is added here when it is durable and worth consulting across sessions.
- A lesson is pruned when a newer decision contradicts it; the removal and reason
  are recorded in `docs/reflection-log.md`.
- When a lesson is added or changed, re-index the retrieval corpus
  (`mcp-servers/retrieval/corpus.json`) so search stays in step with this index.