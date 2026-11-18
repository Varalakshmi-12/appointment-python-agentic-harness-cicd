# Sanitization & Data-Classification Note

**Author:** Varalakshmi
**Repository:** appointment-python-agentic-harness-cicd

This note records how secrets and personal data are kept out of the submitted artifacts and
how data is classified in the system.

## Secrets handling
- **No API keys are committed.** The OpenRouter key is injected at runtime with `-e` and is
  never baked into the image or written to a tracked file.
- **`.env` is gitignored** (both root and `appointment-backend/.env`); only dummy Twilio
  values (`TWILIO_SID=dummy`, `TWILIO_AUTH=dummy`, `TWILIO_NUMBER=dummy`) are ever used, so no
  live credential exists to leak and no SMS is ever sent.
- **`appointment-backend/test_mysql.py` is gitignored** (it carries a local DB password).
- A policy test (`eval/test_policy.py`) and a CI integrity check scan for credential-shaped
  strings so a secret cannot merge unnoticed.

## PII handling
- The hardcoded contact details flagged on the first review (a gmail address and a phone
  number) have been removed from the application source.
- A full repository sweep for emails, phone numbers, and key formats (`sk-ant-`, `sk-or-`,
  AWS keys) returns no real secrets or PII. The only matches are placeholders (e.g.
  `sk-or-v1-…` in the README run instructions), detection regexes in the policy test, and
  documentation describing the agent *refusing* to store a credential-shaped string — none of
  which are live data.

## Data classification
- **No real customer or patient data is used.** The pipeline runs on the appointment app's
  own source code and a representative internal-lessons corpus (`proj-lessons`) authored for
  this project.
- Lessons carry a classification label (`public` / `internal` / `confidential` / `secret`),
  and the retrieval server enforces a per-role classification ceiling: a role is only returned
  documents at or below its ceiling, and anything above it is withheld with an audit entry
  (`eval/evidence/retrieval-governance-live.jsonl`).
- In a real deployment the same controls — classification ceilings, allow-lists, audit
  logging, and human approval — would carry production data; the no-deployment path here uses
  representative data only.

## Scope
This note covers the GitHub repository and the uploaded PDFs. Runtime logs under `logs/` are
gitignored and are not part of the submission; the committed audit evidence lives under
`eval/evidence/`.