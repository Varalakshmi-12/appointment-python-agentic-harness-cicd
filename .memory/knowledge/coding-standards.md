# Coding Standards

Last reviewed: 2026-08-25
Maintained by: the developer (project owner)

These standards apply to all code in this project. The agent should consult this
file before writing or reviewing any code. These rules are set by humans and the
agent should never modify this file.

## Parameterized SQL only
All database queries must use parameterized %s placeholders. Never build SQL with
string formatting, f-strings, or concatenation, to avoid SQL injection.

## Credentials from environment only
Database, Twilio, and SMTP credentials must come from environment variables (loaded
from .env, which is gitignored). Never hardcode secrets or commit them.

## Return JSON with clear structure
API routes return JSON. Do not return raw exception text (str(e)) to clients, as it
leaks internal database and library details; return a safe error message instead.

## Validate request input
Validate presence and type of request data (JSON body, query params, URL params)
before using it. Do not trust the client's <select> to constrain values -- validate
server-side.

## Follow the existing stack conventions
The backend is plain Flask with raw mysql.connector (no ORM, no validation library).
Match the existing style: routes list their columns positionally in the SQL string.
Do not introduce an ORM without a deliberate, human-approved decision.

## Frontend controlled-input pattern
React components use the controlled-input pattern: one form-state object with a single
handleChange handler. Constrained values use a <select> (provider_name is the precedent).

## No new state-machine or speculative abstractions
Do not add patterns the codebase does not already use (e.g., status-transition state
machines) unless a logged decision motivates it. Prefer the smallest change consistent
with existing structure.