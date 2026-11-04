# Governed Multi-Agent Engineering Pipeline — Appointment App

A containerized, governed, multi-agent engineering pipeline for an appointment-scheduling
application (Flask + MySQL backend, React frontend). An orchestrator delegates to
least-privilege subagents (planner, implementer, reviewer, tester, project-manager) that
reach tools only through audited MCP servers, with evaluation, CI/CD guardrails, and
right-tool (agent → deterministic) conversions.

**A reviewer can fork, run the pipeline end-to-end, and see governance block an
over-reaching agent in under 15 minutes by following this README.**

---

## 1. Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.
- An **OpenRouter API key** (free to create at [openrouter.ai](https://openrouter.ai)),
  restricted to the model `anthropic/claude-haiku-4.5`.
- ~2 GB free disk for the image.
- Windows users: the run commands below are given for **PowerShell**; a Git Bash / WSL
  variant is noted where it differs.

No local Python or Node setup is required — everything runs inside the container.

## 2. Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `OPENROUTER_API_KEY` | **Yes** | Model access (scope it to `anthropic/claude-haiku-4.5`). Injected at runtime with `-e`; never baked into the image. |
| `AGENT_ROLE` | Yes for a run | The role the container runs as (`orchestrator`, `implementer`, `reviewer`, …). Sets least-privilege scope and audit identity. |
| `SLACK_BOT_TOKEN`, `SLACK_TEAM_ID` | Optional | Only needed for the Slack notification tool; the core pipeline does not require them. |
| `STORAGE_AUDIT_LOG`, `RETRIEVAL_AUDIT_LOG` | Optional | Override audit-log paths (default `logs/…`). |

> **Never commit secrets.** `.env` and `appointment-backend/test_mysql.py` (which carries a
> local DB password) are gitignored. Set the key in your shell before running:
> ```powershell
> $env:OPENROUTER_API_KEY = "sk-or-v1-…"   # PowerShell
> ```
> ```bash
> export OPENROUTER_API_KEY="sk-or-v1-…"   # bash
> ```

## 3. Get the image

Pull the prebuilt image (fastest):
```bash
docker pull heatonresearch/agentic_engineer_4
docker tag heatonresearch/agentic_engineer_4 agentic_engineer_4
```
…or build it from the repo:
```bash
docker build -t agentic_engineer_4 .
```

## 4. Run the pipeline end-to-end (~5 min)

From the repo root:

**PowerShell**
```powershell
docker run -it --rm `
  -e OPENROUTER_API_KEY=$env:OPENROUTER_API_KEY `
  -e AGENT_ROLE=orchestrator `
  -v "${PWD}:/workspace" `
  -v "${PWD}/.memory:/memory" `
  agentic_engineer_4
```
**bash**
```bash
docker run -it --rm \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -e AGENT_ROLE=orchestrator \
  -v "$(pwd):/workspace" \
  -v "$(pwd)/.memory:/memory" \
  agentic_engineer_4
```
The container drops you at a shell inside `/workspace`. Then:

```bash
claude                 # start the agent runtime
```
Inside, confirm the governed tool servers are connected:
```
/mcp                   # expect: storage ✔ (6 tools), retrieval ✔ (1 tool)
```
Give the orchestrator a task:
```
Use the appt-orchestrator to add input validation to the appointment
status-transition route. Plan first and wait for my approval, then
implement, security review, and run the tests.
```
Approve at the plan checkpoint. The pipeline runs plan → implement → security review →
deterministic test gate. Audit evidence is written to `logs/storage-audit-log.jsonl`.

> **Role-scoped runs:** `scripts/run-agent.ps1 <role>` (PowerShell) or
> `scripts/run-agent.sh <role>` (bash) launch the container with the correct
> read-only / read-write mounts and memory policy for any single role.

## 5. See governance stop an over-reach (~1 min)

The implementer may write but not delete. Inside the container:
```bash
AGENT_ROLE=implementer python3 scripts/probe.py mcp-servers/storage/server.py delete_entry
AGENT_ROLE=implementer python3 scripts/probe.py mcp-servers/storage/server.py write_entry
```
Expected:
```
DENIED: delete_entry -> authorization_denied: role 'implementer' may not call 'delete_entry'. See docs/governance-policy.md.
ALLOWED: write_entry
```
The denial is recorded in the audit log:
```bash
tail -n 3 logs/storage-audit-log.jsonl
```

## 6. Run the deterministic test step and the eval harness

Deterministic test gate (the agent → code conversion from ADR-001):
```bash
python scripts/run_tests_deterministic.py --tests appointment-backend/test_status_route.py --output logs/test-result.json
```
Deterministic governance harness (reads an evidence base `<name>.json` + `<name>.log`):
```bash
python eval/harness_deterministic.py eval/evidence/<evidence-base>
```

---

## 7. Repository map — evidence index

Every required artifact and where to find it.

| Required content | Location |
|---|---|
| **README & run path** | `README.md` (this file) |
| **Containerized harness** (fs/network/credential boundaries) | `Dockerfile`, `docker-entrypoint.sh`, `scripts/run-agent.sh`, `scripts/run-agent.ps1` |
| **Module 1 — PRD** | `docs/lint-prd.md` `docs/import-check-prd.md`|
| **Module 1 — quality rubric + thresholds** | `docs/import-check-rubric.md`,`docs/lint-rubric.md``eval/rubric.json`, `eval/harness_rubric_suite.py` |
| **Module 1 — baseline + iteration log** | `docs/iteration-log.md` |
| **Module 2 — agent definitions** | `agents/appt-orchestrator.md`, `appt-implementer.md`, `appt-security-reviewer.md`, `appt-import-checker.md` |
| **Module 2 — skills (≥2)** | `skills/`  |
| **Module 2 — memory layout + notes** | `.memory/`, `docs/memory-architecture.md` |
| **Module 2 — reflection log** | `docs/calibration-log.md` |
| **Module 3 — orchestration diagram** | `docs/appt-orchestration-diagram.md` |
| **Module 3 — routing & tool-grant map** | `docs/routing-and-tool-grant-map.md`, `docs/routing-and-tool-grant-map.json` |
| **Module 3 — MCP config + schemas** | `.mcp.json`, `mcp-servers/storage/{server.py,schema.json,allow-list.json}`, `mcp-servers/retrieval/…` |
| **Module 3 — retrieval quality report + ground truth** | `docs/retrieval-validation-results.md`, `docs/proj-lessons-ground-truth.md`  |
| **Module 3 — eval harness + holdout set** | `eval/harness_deterministic.py`, `docs/holdout-task-ste.md` (HO-* holdout) |
| **Module 3 — calibration log** | `docs/calibration-log.md` |
| **Module 4 — governance policy** | `docs/governance-policy.md` |
| **Module 4 — role-to-tool access matrix** | `docs/appt-routing-and-tool-grant-map.md` |
| **Module 4 — CI/CD guardrails** | `.github/workflows/`, `scripts/check-pipeline-integrity.py` |
| **Module 4 — audit log** | `logs/storage-audit-log.jsonl`, `logs/retrieval-audit-log.jsonl`; builder `scripts/build-audit-trail.py` ,`eval/evidence/`|
| **Module 4 — failure-mode playbook** | `docs/ops-runbook.md` / `docs/failure-mode-playbook.md`  |
| **Module 4 — agent/deterministic/human matrix** | `docs/step-classification.md` |
| **Module 4 — deterministic conversion + ADR** | `scripts/run_tests_deterministic.py`, `docs/adr/ADR-001-tester-deterministic-conversion.md` |
| **ADR package** | `docs/adr/` (ADR-001 … ADR-007) |
| **Enforcement verification + red-team** | `eval/enforcement-verification.md`, `eval/red-team-prompts.md`, `eval/red-team-results.md`, `scripts/probe.py` |
| **Production integration (end-to-end run)** | `docs/run-summary.md`, `eval/evidence/run-A-*`, `eval/evidence/run-B-*` |
| **Impact, right-tool drill, stakeholder one-pager, ops runbook** | `docs/impact-report.md`, `docs/tool-evolution-drill.md`, `docs/stakeholder-one-pager.md`, `docs/ops-runbook.md` |

---

## 8. Governance & boundaries (summary)

- **Container (Layer 1):** workspace mounted read-only for non-writing roles; memory volume
  omitted unless the role's policy allows it; no outbound network egress; identity set by
  `AGENT_ROLE`.
- **MCP allow-lists (Layer 2):** every storage/retrieval operation passes an `_authorize`
  gate against a per-role allow-list; an ungranted call raises `ToolError` and logs
  `authorization_denied`. Retrieval enforces a per-role classification ceiling.
- **CI/CD:** policy test, evaluation gate, and a pipeline-integrity check are required
  status checks; a weakened gate fails the build.
- **Right-tool discipline:** stable agentic steps are converted to deterministic code with
  before/after evidence and an ADR written at decision time.

See `docs/governance-policy.md` and `eval/enforcement-verification.md` for the full policy
and the reproducible verification (`scripts/probe.py`).

## 9. Sanitization

No secrets, PII, customer data, or internal URLs are committed. `.env` and
`appointment-backend/test_mysql.py` are gitignored; the OpenRouter key is supplied at
runtime via `-e` and scoped to a single model. Audit logs under `logs/` are runtime
artifacts (gitignored); representative evidence is copied into `eval/evidence/`.

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `/mcp` shows `storage ✘ / retrieval ✘` | `.mcp.json` must use **stdio** (`"command": "python"`, `"args": ["mcp-servers/<name>/server.py"]`), not an `http` URL — the servers speak stdio. |
| `authorization_denied` on every call | `AGENT_ROLE` is unset or empty; set it (`-e AGENT_ROLE=orchestrator`). |
| `ModuleNotFoundError: flask_cors` when running backend tests | Install the app's runtime deps in the container: `pip install -r appointment-backend/requirements.txt` (bake these into the Dockerfile for full reproducibility). |
| Tester step fails: `unrecognized [mcp__coursetools__test_runner]` | Expected in this environment — the agentic tester's tool isn't present. Run the deterministic step instead: `python scripts/run_tests_deterministic.py …` (this is ADR-001). |
| Slack / Gmail MCP show `✘` | Optional integrations; not needed for the core pipeline. |

---

Repository: **[https://github.com/Varalakshmi-12/appointment-python-agentic-harness-cicd]**


<!-- =========================================================
This README (preserved for reference; not rendered on GitHub)
# Module 4.2 — LaunchCode Agentic Engineer (CI/CD)

> **Note:** This repository covers **Module 4.2 (CI/CD) only.**
> For Module 4.1 and Module 4.3, use the materials in the main course repository:
> [https://github.com/jeffheaton/LaunchCodeAgenticEngineer/tree/main/module_4](https://github.com/jeffheaton/LaunchCodeAgenticEngineer/tree/main/module_4)

Docker development environment for LaunchCode's **Agentic Programming** course, Module 4.2 (CI/CD). Extends the Module 3 environment with:

- **Slack MCP server** — lets Claude Code prompts read and post to Slack
- **Gmail MCP server** — lets Claude Code prompts read and send email
- **Pre-configured skills** — custom slash commands available inside Claude Code
- **Pre-configured agents** — autonomous sub-agents Claude Code can invoke for specialized tasks

## Quick Start

Build and run locally:

```bash
cd module_4
docker build -t agentic_engineer_4 .
docker run -it --rm -p 8501:8501 -p 8502:8502 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e SLACK_TEAM_ID=T0123456 \
  -v "$PWD":/workspace \
  agentic_engineer_4
```

Or pull the pre-built image from DockerHub:

```bash
docker run -it --rm -p 8501:8501 -p 8502:8502 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e SLACK_TEAM_ID=T0123456 \
  -v "$PWD":/workspace \
  heatonresearch/agentic_engineer_4:latest
```

Full setup with Slack and Gmail (reads credentials from your shell environment):

```bash
docker run -it --rm \
  -p 8501:8501 -p 8502:8502 \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  -e SLACK_BOT_TOKEN=$SLACK_BOT_TOKEN \
  -e SLACK_TEAM_ID=$SLACK_TEAM_ID \
  -v "$PWD":/workspace \
  -v "$HOME/.gmail-mcp":/root/.gmail-mcp \
  heatonresearch/agentic_engineer_4:latest
```

Place `credentials.json` (from Google Cloud Console) in `$PWD` before running. The Gmail MCP will trigger OAuth on first use and persist the token in `~/.gmail-mcp/`.

## Build

```bash
docker build -t agentic_engineer_4 .
```

Force a complete rebuild (no cached layers):

```bash
docker build --no-cache -t agentic_engineer_4 .
```

## Run

### With a local workspace (recommended)

```bash
# macOS / Linux
docker run -it --rm -p 8501:8501 -p 8502:8502 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e SLACK_TEAM_ID=T0123456 \
  -v "$PWD":/workspace \
  agentic_engineer_4

# Windows (PowerShell)
docker run -it --rm -p 8501:8501 -p 8502:8502 `
  -e SLACK_BOT_TOKEN=xoxb-your-token `
  -e SLACK_TEAM_ID=T0123456 `
  -v "${PWD}:/workspace" `
  agentic_engineer_4
```

Files created or edited inside `/workspace` are saved to your local folder and persist after the container exits.

### Without a local workspace

```bash
docker run -it --rm -p 8501:8501 agentic_engineer_4
```

Any files created inside the container will be lost when it exits.

---

## MCP Servers

MCP (Model Context Protocol) servers extend Claude Code so that prompts can take real-world actions — posting to Slack, reading email, etc. — without writing any extra code. Both servers are pre-installed as global npm packages and pre-configured in `/root/.claude/settings.json` inside the image.

### Slack MCP Server

**Package:** `@modelcontextprotocol/server-slack`

**Required environment variables** (pass with `-e` at `docker run`):

| Variable          | Description                                           |
| ----------------- | ----------------------------------------------------- |
| `SLACK_BOT_TOKEN` | Bot User OAuth Token from your Slack App (`xoxb-…`)   |
| `SLACK_TEAM_ID`   | Your Slack workspace ID (found in workspace settings) |

**Getting a Slack Bot Token:**

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and create a new app.
2. Under **OAuth & Permissions**, add Bot Token Scopes: `channels:read`, `chat:write`, `channels:history`, `users:read`.
3. Install the app to your workspace and copy the **Bot User OAuth Token**.
4. Copy your workspace's **Team ID** from the workspace URL or settings.

**What it enables:** Claude Code prompts can list channels, read message history, post messages, and look up users in your Slack workspace.

### Gmail MCP Server

**Package:** `@gongrzhe/server-gmail-autoauth-mcp`

**Setup (OAuth):**

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and create a project.
2. Enable the **Gmail API**.
3. Create OAuth 2.0 credentials (Desktop App type) and download `credentials.json`.
4. Place `credentials.json` in your workspace directory (mounted at `/workspace`).
5. On first use, the MCP server will open an OAuth flow and save a token. To persist the token across container restarts, mount the credentials directory:

```bash
docker run -it --rm -p 8501:8501 \
  -v "$PWD":/workspace \
  -v "$HOME/.gmail-mcp":/root/.gmail-mcp \
  agentic_engineer_4
```

**What it enables:** Claude Code prompts can read, search, and send Gmail messages on behalf of the authenticated user.

---

## Skills

Skills are custom slash commands invoked by typing `/skill-name` inside a Claude Code session. Claude Code supports two ways to define skills, and this image uses both.

### Pre-installed Skills

| Skill                 | Description                                                 |
| --------------------- | ----------------------------------------------------------- |
| `/send-slack-message` | Send a message to a Slack channel via the Slack MCP server  |
| `/check-gmail`        | Retrieve and summarize recent unread Gmail messages         |
| `/send-email`         | Draft and send an email via the Gmail MCP server            |
| `/summarize-session`  | Generate a bullet-point summary of the current work session |
| `/rebuild-and-deploy` | Rebuild the Docker image and push it to DockerHub           |

---

### SKILL.md files

Each skill lives in its own Markdown file at `.claude/skills/<skill-name>/SKILL.md`. Inside the container these are placed at `/root/.claude/skills/`.

```
skills/
  send-slack-message/SKILL.md
  check-gmail/SKILL.md
  send-email/SKILL.md
  summarize-session/SKILL.md
```

**When to use this method:**

- The skill prompt is more than a sentence or two.
- The skill has multiple steps, conditional logic, or examples that benefit from formatting.
- You want each skill in its own file for easier editing and version control.
- You are building skills that will be shared or maintained over time.

To add a skill, create a new directory and SKILL.md file:

```bash
mkdir -p skills/my-skill
cat > skills/my-skill/SKILL.md << 'EOF'
Description of what this skill does.

Steps:
1. First step Claude should take.
2. Second step.
3. Confirm result to the user.
EOF
```

Then rebuild the image so the file is copied into `/root/.claude/skills/`:

```bash
docker build -t agentic_engineer_4 .
```

**Adding a skill at runtime (no rebuild required):**

You can also add a skill directly inside a running container without rebuilding the image. The full path inside the container is:

```
/root/.claude/skills/<skill-name>/SKILL.md
```

For example:

```bash
mkdir -p /root/.claude/skills/my-skill
nano /root/.claude/skills/my-skill/SKILL.md
```

Note: since the container is run with `--rm`, any skills added this way will be lost when the container exits. To persist them, add them to the `skills/` directory in this repo and rebuild.

---

## Agents

Agents are autonomous sub-agents that Claude Code can spin up to handle specialized tasks. Unlike skills (which are slash commands you invoke), agents are specialists that Claude Code invokes automatically when the task matches, or that you can request explicitly in a prompt.

Agents are defined as Markdown files with YAML frontmatter and stored in `.claude/agents/` (inside the container: `/root/.claude/agents/`). Source files live in `agents/` in this repo and are copied in at image build time.

### Pre-installed Agents

| Agent           | Trigger description                                                                           |
| --------------- | --------------------------------------------------------------------------------------------- |
| `code-reviewer` | Reviews recent git changes for quality, security, and maintainability without modifying files |

### Running an Agent

**Explicitly — ask Claude Code to use it:**

```
Review my recent changes using the code-reviewer agent.
```

**Automatically** — Claude Code will invoke the agent on its own when the task matches the agent's description. For example, after you ask Claude to write a new feature, it may proactively run the code-reviewer agent.

### How the code-reviewer Agent Works

When invoked, `code-reviewer`:

1. Runs `git diff` to find recent changes.
2. Reads each modified file.
3. Classifies every issue as **Critical**, **Warning**, or **Suggestion**.
4. Provides a concrete fix example for every Critical and Warning item.

It checks for:

- Code clarity and naming conventions
- Duplicated logic
- Error handling and input validation
- Exposed secrets or API keys
- Test coverage for new behavior
- Performance implications

The agent never edits or creates files — it only reports.

### Adding a New Agent

1. Create a Markdown file in `agents/` with a YAML frontmatter block:

```markdown
---
name: my-agent
description: >
  One or two sentences describing when Claude Code should invoke this agent.
tools: Read, Grep, Glob, Bash
model: inherit
permissionMode: default
---

Your agent prompt goes here.
```

2. Rebuild the image:

```bash
docker build -t agentic_engineer_4 .
```

**Adding an agent at runtime (no rebuild required):**

```bash
mkdir -p /root/.claude/agents
nano /root/.claude/agents/my-agent.md
```

Note: agents added this way are lost when the container exits (since it runs with `--rm`). Add them to `agents/` in this repo and rebuild to persist them.

### Agent File Format

| Field            | Description                                                         |
| ---------------- | ------------------------------------------------------------------- |
| `name`           | Identifier used to reference the agent                              |
| `description`    | Tells Claude Code when to invoke the agent (be specific)            |
| `tools`          | Comma-separated list of tools the agent may use                     |
| `model`          | Model to use (`inherit` uses the same model as the parent session)  |
| `permissionMode` | `default` respects normal permission prompts; `allowAll` skips them |

---

## Running Subagent Containers

`scripts/run-agent.sh` (macOS/Linux) and `scripts/run-agent.ps1` (Windows) launch a subagent container enforcing the governance policy for the given role. Pass the role name as the first argument; any additional arguments are forwarded to the container.

**macOS / Linux:**

```bash
# Read-only workspace, no memory mount (reviewer, tester, project-manager)
./scripts/run-agent.sh reviewer

# Read-write workspace, memory mounted (implementer, orchestrator)
./scripts/run-agent.sh implementer

# Pass a command to run inside the container
./scripts/run-agent.sh tester python3 -m pytest eval/ -v
```

**Windows (PowerShell):**

```powershell
# Read-only workspace, no memory mount
.\scripts\run-agent.ps1 reviewer

# Read-write workspace, memory mounted
.\scripts\run-agent.ps1 implementer

# Pass a command to run inside the container
.\scripts\run-agent.ps1 tester python3 -m pytest eval/ -v
```

Override the default image (`launchcode-agentic:module4`) with the `AGENT_IMAGE` environment variable:

```bash
AGENT_IMAGE=heatonresearch/agentic_engineer_4:latest ./scripts/run-agent.sh implementer
```

```powershell
$env:AGENT_IMAGE = 'heatonresearch/agentic_engineer_4:latest'
.\scripts\run-agent.ps1 implementer
```

---

## Gmail API Credentials (Python SDK)

In addition to the MCP server, the Python `google-api-python-client` library is available for direct API use in your code.

Place `credentials.json` (from Google Cloud Console) in your workspace directory. On first run it triggers OAuth and saves `token.json`. Reference it in code as:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
```

Keep both files out of source control:

```
# .gitignore
credentials.json
token.json
```

---

## Running Streamlit Apps

From inside the container:

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

---

## Running Unit Tests

The test suite runs inside the Docker container, which has all dependencies pre-installed. Build the image first if you haven't already:

```bash
docker build -t agentic_engineer_4 .
```

### Run all eval tests

```bash
docker run --rm \
  -v "$PWD":/workspace \
  agentic_engineer_4 \
  python3 -m pytest eval/ -v
```

### Run specific test suites

```bash
# Deterministic router and handoff-validator unit tests (fast, no external deps)
docker run --rm -v "$PWD":/workspace agentic_engineer_4 \
  python3 -m pytest eval/test_deterministic_router.py eval/test_deterministic_step.py -v

# Full deterministic suite including CLI subprocess and directory-structure checks
docker run --rm -v "$PWD":/workspace agentic_engineer_4 \
  python3 -m pytest eval/test_deterministic.py -v

# Governance policy / allow-list / skill-scope enforcement tests
docker run --rm -v "$PWD":/workspace agentic_engineer_4 \
  python3 -m pytest eval/test_policy.py -v

# Rubric suite placeholders
docker run --rm -v "$PWD":/workspace agentic_engineer_4 \
  python3 -m pytest eval/test_rubric_suite.py -v
```

### What each suite checks

| Suite | What it tests |
| --- | --- |
| `test_deterministic_router.py` | `scripts/route_task_deterministic.py` path-to-role routing logic |
| `test_deterministic_step.py` | `scripts/validate_handoff_deterministic.py` field validation logic |
| `test_deterministic.py` | CLI invocation of the validator, directory structure, governance-policy content |
| `test_policy.py` | Storage allow-list, retrieval allow-list, skill-scope files, and container permissions all agree with `docs/governance-policy.md` |
| `test_rubric_suite.py` | Rubric/judge placeholders — confirms ADR and CI design docs contain required content |

### Notes

- `eval/test_policy.py` reads `.skills/*.md` for skill-scope enforcement. The `.skills/` directory is currently empty — add per-role skill scope files there as you build out the governance lesson content.
- Tests that check directory structure (`.agents`, `.skills`, `docs/adr`, etc.) expect those directories to exist in the bind-mounted workspace. They are created automatically when the container runs without a bind-mount.
- `scripts/run-reviewer.py` is a safe sample that does **not** call a live LLM. It writes a deterministic advisory review so the CI workflow can be exercised without API spend.
- Runtime logs belong under `logs/` and are gitignored.
- Configure branch protection so `Policy Test Suite`, `Evaluation Harness`, and `Pipeline Integrity Check` are required status checks before merge.

---

## Build & Deploy to DockerHub

This section covers the full workflow for building the image and publishing it to DockerHub so students can pull it without building locally.

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- A DockerHub account (free at [hub.docker.com](https://hub.docker.com))
- Logged in to DockerHub on your machine:

```bash
docker login
```

### Step 1 — Build and tag for DockerHub

Build the image and tag it with your DockerHub username and repository name. Replace `heatonresearch` with your DockerHub username if different.

```bash
cd module_4
docker build -t heatonresearch/agentic_engineer_4:latest .
```

To tag a specific version number alongside `latest` (recommended so students can pin to a known-good version):

```bash
docker build \
  -t heatonresearch/agentic_engineer_4:latest \
  -t heatonresearch/agentic_engineer_4:3.0 .
```

Force a full rebuild ignoring all cached layers:

```bash
docker build --no-cache \
  -t heatonresearch/agentic_engineer_4:latest \
  -t heatonresearch/agentic_engineer_4:3.0 .
```

### Step 2 — Push to DockerHub

```bash
docker push heatonresearch/agentic_engineer_4:latest
docker push heatonresearch/agentic_engineer_4:3.0
```

Both tags must be pushed separately. The `latest` tag is what students get by default when they don't specify a version.

### Step 3 — Verify the image is public

Visit `https://hub.docker.com/r/heatonresearch/agentic_engineer_4` and confirm the repository visibility is set to **Public** so students can pull without logging in.

### Pulling the image (students)

Once published, students can run the image directly without cloning the repo or building anything:

```bash
docker run -it --rm -p 8501:8501 -p 8502:8502 \
  -e SLACK_BOT_TOKEN=xoxb-your-token \
  -e SLACK_TEAM_ID=T0123456 \
  -v "$PWD":/workspace \
  heatonresearch/agentic_engineer_4:latest
```
========================================================= -->