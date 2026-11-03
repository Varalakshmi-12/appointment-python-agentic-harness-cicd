# Memory Architecture

## What this workflow needs to remember

This agent helps maintain the appointment-scheduling application (Flask + raw mysql.connector
backend, React/Vite frontend, MySQL database) by performing recurring engineering tasks such as
security review, feature implementation, and code review. Across sessions it needs to remember
the decisions that are not visible in the code (why an approach was chosen over an alternative),
the current phase of in-progress features, known quirks of the environment, deferred work, and
stable project conventions that the agent must follow. It does not need to store the contents of
source files, tests, or configuration, because those already exist as project artifacts and the
repository is the source of truth for current code. It must not store database credentials,
Twilio/SMTP secrets, patient data, or notes tied only to a task that is already complete.

## Layer 1: Project memory directory (.memory/project/)

### Belongs here
Evolving context the agent reads at startup (via MEMORY_INDEX.md) and may write to when a decision is made or project state changes. Examples: the status-field decisions (001, 003, 005), error- handling decision (004), test-location decision (002), credential-location decision (006), the "Twilio not wired up" state fact, and the no-migration-runner quirk.
- The decision to implement the appointment status field via a dedicated PATCH /appointments/<id>/status endpoint (Approach B), chosen over folding status into the PUT route because PUT always fires a misleading "updated to {time}" notification (decided 2026-08).
- The decision to keep DELETE as a hard delete and treat "cancelled" as a separate status, rather than converting cancel into a soft-delete.
- Current phase of the status-field feature: implemented (schema + PATCH route + frontend) but not yet verified end-to-end.
- Known environment quirk: there is no migration runner; schema.sql changes require a manual ALTER TABLE on existing databases.
- Known domain fact: Twilio SMS is not actually wired up / functional in this deployment, so cost-bearing-abuse severities on /test-sms and /test-email are conditional, not active.

### Does not belong here
- The actual contents of app.py or schema.sql (project artifacts; the repo is the source of truth).
- Database passwords, Twilio tokens, or SMTP credentials (secrets must never be stored in any memory layer -- they live in .env, gitignored).

### Governance
- **Scope:** Project-scoped -- this memory applies to this repository only.
- **Write permissions:** The agent may add new entries and update existing ones when a decision is made or a phase changes.
- **Pruning policy:**
  - Feature/branch-specific entries (e.g., the status-field phase) are archived when that feature is completed and merged.
  - Project-wide entries (conventions, known quirks, domain facts) are reviewed every 90 days or replaced immediately when a superseding decision is recorded.

## Layer 2: Knowledge files (.memory/knowledge/)

### Belongs here
Stable, human-maintained rules the agent reads but never edits: coding-standards.md (parameterized SQL, env-var secrets, no raw exceptions to clients, server-side validation, no ORM, controlled- input frontend, no speculative abstractions).
- Backend conventions: plain Flask with raw mysql.connector (no ORM, no validation library); each route hardcodes its column list positionally in the SQL string.
- Security convention: all SQL uses parameterized %s placeholders (no string-formatted queries) -- this must be preserved.
- API convention: routes return JSON; DB credentials come from environment variables, never hardcoded.
- Frontend convention: controlled-input pattern -- one form-state object with a single handleChange; constrained values use a <select> (provider_name is the precedent).
- Security policy: state-changing routes should require auth/ownership checks; debug mode must be off outside local dev; error responses must not leak raw exception text.

### Does not belong here
- Any evolving or in-progress decision (e.g., "the status feature is in phase X") -- that is current state and belongs in project memory, not in a stable rules file.
- Step-by-step procedures such as "how to run the test suite" -- those belong in a skill, not a knowledge file.

### Governance
- **Scope:** Project-scoped -- conventions and policies for this repository.
- **Write permissions:** Human-maintained only. The agent reads these but must not edit them, so the rules stay authoritative and consistent.
- **Pruning policy:** Reviewed only on deliberate human change (e.g., when a convention is intentionally revised); entries change slowly and only with human review, not automatically.

## Layer 3: Indexed reference documents (.memory/reference/)

### Belongs here
Large or infrequently-needed documents located via an index and read on demand. Currently empty (REFERENCE_INDEX.md explains the empty-layer decision); would be populated when past PRs, design docs, or a large security-review log make on-demand retrieval worthwhile.
- The security-review iteration log (docs/security-review-iteration-log.md) -- runs, scores, fixes.
- The context-management exercise artifacts (pre-session plan, technique plan, session summary).
- The continuity notes from the memory exercise (design rationale for the status feature).
- Any future design documents, past PR descriptions, or architecture discussion notes.

### Does not belong here
- Small, frequently-needed facts that should just live in project memory or knowledge (an index adds overhead for something read every session).
- Secrets or patient data (never stored in any layer).

### Governance
- **Scope:** Project-scoped. Consulted on demand via an index rather than loaded every session.
- **Write permissions:** The agent may add new reference documents and index entries; existing documents are generally append-only historical records and are not rewritten.
- **Pruning policy:** Documents are retained as historical record; the index is trimmed when a document is superseded, and the reference set is reviewed when it grows large enough to make the index hard to scan.

## Allocation decision table

| Information item                     | Layer chosen           | Why                      |
|------------------                    |--------------           |-----                            |
| Why Approach B was chosen for status | Project memory | Evolving decision/rationale not visible in code;may be revised. 
| "No ORM, raw mysql.connector, positional columns" | Knowledge file | Stable convention; changes only with human review. |
| Twilio not actually wired up | Project memory | Current domain/state fact that adjusts severity judgments; could change. |
| Security-review iteration log | Indexed reference | Large, historical, consulted on demand -- not needed every session. |
|Memory scope declaration (SCOPE.md)	|Project memory root (read-only to agent)	 |Identifies which project owns the mounted memory directory.
|Credential location (e.g. ANTHROPIC_API_KEY)	|Project memory	     |Records how a credential is accessed WITHOUT storing its value.
| How to run the app / tests | Skill (not memory) | Procedure, not memory. |
| .env credentials | Environment variable (no layer) | Secret; never stored in memory. |
| Current text of app.py | Context window / repo | Project artifact; repo is source of truth. |

Allocation decision table
Information item	Layer	Why
Why Approach B (PATCH) for status	Project memory	Evolving decision/rationale not in code; may be revised.
"No ORM, raw mysql.connector, positional columns"	Knowledge file	Stable convention; changes only with human review.
Twilio not actually wired up	Project memory	Current state fact that adjusts severity judgments; could change.
Security-review iteration log / past PRs	Indexed reference	Large, historical, consulted on demand.
Memory scope declaration (SCOPE.md)	Project memory root (read-only to agent)	Identifies which project owns the mounted memory directory.
Credential location (e.g. ANTHROPIC_API_KEY)	Project memory	Records how a credential is accessed WITHOUT storing its value.
How to run the app / tests	Skill (not memory)	Procedure, not memory.
.env credential values	Environment variable (no layer)	Secret; never stored in memory.
Current text of source files	Context window / repo	Project artifact; repo is source of truth.
## Alternatives considered

Considered storing the fact that "Twilio is not actually wired up" in a Knowledge File rather
than in Project Memory. The two locations I weighed were Layer 2 (knowledge, human-maintained,
read-only for the agent) and Layer 1 (project memory, agent-writable). I chose Project Memory
because this is an observation about the current state of the deployment that could change if
Twilio is later configured, and the agent should be able to update it when it learns otherwise --
whereas a Knowledge File is for stable rules that should only change under human review. The
tradeoff is that project memory is less authoritative than a knowledge file, but it is the right
fit for a fact that is true-for-now rather than true-by-policy.

## Data Classification

Before writing anything to a memory file, classify it:

- **Public** — Safe to commit to the repo and share broadly. Most project decisions and coding
  standards fall here.
- **Internal** — Safe within the team but not for public repos. Store in a non-committed volume or
  .gitignore the containing folder.
- **Confidential** — Sensitive business data. Do not store in agent memory. Retrieve from secure
  systems on demand.
- **Secret** — Credentials, tokens, API keys, PII. Must never appear in any memory file. If the
  agent encounters a secret during a run, use it for the immediate task only and explicitly do not
  write it to any memory layer. Reference the environment variable name instead.

### Guardrails

- **Soft guard:** The CLAUDE.md write policy requires the agent to classify data before writing and
  to refuse to store Confidential or Secret values (see CLAUDE.md > Write policy). This depends on
  the agent following the instruction.
- **Hard stop:** A Git pre-commit hook at `.git/hooks/pre-commit` scans staged files under
  `.memory/` for common credential patterns (sk-, password=, secret=, token=, api_key=, apikey=)
  before each commit. If a pattern is found, the commit is blocked regardless of agent behavior.
  Note: the hook lives in `.git/hooks/`, which is NOT committed to the repo, so it must be
  re-created on a fresh clone (or managed via a tool like `pre-commit` for team use). It also only
  scans `.memory/`; a repo-wide secret scan would need separate configuration.


  Enforcement (soft guards vs. hard stops)
Scope verification (soft guard): Each .memory/ root carries a SCOPE.md declaring its owning repo. The agent reads it on startup, before any other memory, and halts on a mismatch.
Stale-memory policy (soft guard): Review dates are checked before an entry is used. An expired entry is flagged and acted on only after human confirmation.
Write policy / classification (soft guard): The agent classifies data before writing; Public/Internal may be written, Confidential is not stored (pointer to source instead), Secret is never stored and is flagged if found.
Read-only knowledge (soft guard here): knowledge/ is intended read-only. NOTE: chmod-based filesystem read-only does NOT persist on this Windows Docker bind-mount, so read-only is enforced by the CLAUDE.md instruction rather than OS permissions. On a Linux-native filesystem, chmod would add an OS-level layer.
Secrets at commit (hard stop): A Git pre-commit hook at .git/hooks/pre-commit scans staged files under .memory/ for credential patterns (sk-, password=, secret=, token=, api_key=, apikey=) and blocks the commit on a match, independently of agent behavior. NOTE: the hook lives in .git/hooks/, which is NOT committed and does not travel on clone; it scans only .memory/.
Why these safeguards exist (tied to observed failures)
Stale memory

Review dates are checked before use because a test that backdated decision-003's review date and changed its recorded status values to a wrong set showed the risk of acting on superseded facts. With the policy in place, a fresh session flagged the expired date AND cross-checked the entry's "checkable specifics" against the code, catching the mismatch rather than trusting it.

Scope verification

The SCOPE.md check exists because a test mounted another project's (project-b) memory into this container. Without the check, the agent would have applied project-b's contradictory decision (return raw exceptions to clients) to this project. With the check, the agent halted on the mismatch and refused to read the wrong-project entries.

Data classification, credential handling, and the pre-commit hook

A credential-in-memory test showed two things: the agent (soft guard) refused to WRITE a credential-shaped string into memory, but a human could still create such a file directly. The committed fake key then persisted in git history. This is why both layers exist: the write-policy soft guard prevents the agent from making the mistake, and the pre-commit hard stop catches the mistake regardless of who introduced it (agent or human), blocking the commit before the secret enters history. Credential VALUES are never stored; only a pointer to the env var name (e.g. ANTHROPIC_API_KEY) is recorded.

Alternatives considered (ADR raw material)

Considered storing "Twilio is not wired up" in a Knowledge File vs. Project Memory. Chose Project Memory because it is current state that could change if Twilio is configured, and the agent should be able to update it -- whereas Knowledge Files are stable rules changed only by humans. Tradeoff: project memory is less authoritative than a knowledge file, but correct for a true-for-now fact.

Considered relying on chmod for read-only knowledge (a hard stop). Ruled out as the primary mechanism because it does not persist on the Windows bind-mount; the portable guardrail is the CLAUDE.md instruction (soft guard), with chmod as an optional OS-level layer on Linux-native filesystems. General principle captured for a future ADR: when a mechanism (hard stop) cannot be enforced on the target platform, a clear policy instruction (soft guard) to a capable agent can substitute, and the two should be layered where both are available -- as with the write policy (soft) plus pre-commit hook (hard) for secrets.