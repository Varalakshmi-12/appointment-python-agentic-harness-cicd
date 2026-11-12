"""Storage MCP server with per-call role-based allow-list enforcement.

Each tool accepts `calling_role` as an argument — the subagent passes its own
role — falling back to the AGENT_ROLE environment variable, then "unknown".
This is what makes per-role least-privilege hold in a LIVE session: the
orchestrator and its subagents share one container (one AGENT_ROLE), so
authorizing on the environment value alone cannot tell them apart. Taking
`calling_role` per call — exactly as the retrieval server already does — lets
the allow-list reject, e.g., an implementer attempting `delete_entry` even
though the container itself runs as `orchestrator`.

Audit records carry `operation`, `calling_role`, `classification`,
`project_id`, `entry_id`, and `timestamp` — the schema
eval/harness_deterministic.py reads (check_no_unknown_caller,
check_forbidden_operations, check_write_classifications).

Prepared by: Varalakshmi
"""

import datetime
import json
import os
import uuid
from pathlib import Path
from typing import Any

try:
    from fastmcp import FastMCP
    from fastmcp.exceptions import ToolError
except Exception:  # pragma: no cover - lets tests run without FastMCP installed
    class ToolError(Exception):
        pass

    class FastMCP:
        def __init__(self, name: str):
            self.name = name

        def tool(self, func=None):
            def decorate(fn):
                return fn
            return decorate(func) if func else decorate

        def run(self):
            print(f"FastMCP not installed; {self.name} functions are importable only.")

mcp = FastMCP("storage")

ALLOW_LIST_PATH = Path(__file__).parent / "allow-list.json"
ALLOW_LIST = json.loads(ALLOW_LIST_PATH.read_text(encoding="utf-8"))
AUDIT_LOG_PATH = Path(os.environ.get("STORAGE_AUDIT_LOG", "logs/storage-audit-log.jsonl"))
AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
STORE_PATH = Path(os.environ.get("STORAGE_STORE", "logs/storage-store.json"))
STORE_PATH.parent.mkdir(parents=True, exist_ok=True)

ALLOWED_CLASSIFICATIONS = {"public", "internal", "confidential", "secret"}


def _effective_role(calling_role: str | None) -> str:
    """Role to authorize and attribute: the per-call argument if provided,
    else the container's AGENT_ROLE, else 'unknown'. Normalized so
    'security_reviewer' and 'security-reviewer' resolve the same."""
    role = calling_role or os.environ.get("AGENT_ROLE", "") or "unknown"
    return role.strip().replace("_", "-").lower() or "unknown"


def _load_store() -> dict[str, Any]:
    if STORE_PATH.exists():
        return json.loads(STORE_PATH.read_text(encoding="utf-8"))
    return {}


def _save_store(data: dict[str, Any]) -> None:
    STORE_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _record(operation: str, outcome: str, role: str, *, classification: str | None = None,
            project_id: str | None = None, entry_id: str | None = None) -> dict[str, Any]:
    """Append one JSON-Lines audit record in the harness-expected schema."""
    record = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "operation": operation,
        "calling_role": role,
        "project_id": project_id,
        "entry_id": entry_id,
        "classification": classification,
        "outcome": outcome,
        "policy_reference": "docs/governance-policy.md",
    }
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")
    return record


def _authorize(operation: str, role: str, *, classification: str | None = None,
               project_id: str | None = None, entry_id: str | None = None) -> None:
    """Deny and audit if the calling role is not on the operation's allow-list."""
    if role not in ALLOW_LIST.get(operation, []):
        _record(operation, "authorization_denied", role, classification=classification,
                project_id=project_id, entry_id=entry_id)
        raise ToolError(
            f"authorization_denied: role '{role}' may not call "
            f"'{operation}'. See docs/governance-policy.md."
        )


@mcp.tool
def write_entry(title: str, content: str = "", classification: str = "internal",
                entry_type: str = "lesson", project_id: str = "proj-lessons",
                entry_id: str | None = None, calling_role: str | None = None) -> dict:
    """Create a project-storage entry. Pass `calling_role` = your agent role so
    least-privilege is enforced per subagent, not per container."""
    role = _effective_role(calling_role)
    entry_id = entry_id or str(uuid.uuid4())
    _authorize("write_entry", role, classification=classification,
               project_id=project_id, entry_id=entry_id)
    data = _load_store()
    data[entry_id] = {
        "project_id": project_id, "entry_type": entry_type, "title": title,
        "content": content, "classification": classification,
    }
    _save_store(data)
    _record("write_entry", "success", role, classification=classification,
            project_id=project_id, entry_id=entry_id)
    return {"ok": True, "entry_id": entry_id}


@mcp.tool
def read_entry(entry_id: str, project_id: str = "proj-lessons",
               calling_role: str | None = None) -> dict:
    role = _effective_role(calling_role)
    _authorize("read_entry", role, project_id=project_id, entry_id=entry_id)
    data = _load_store()
    _record("read_entry", "success", role, project_id=project_id, entry_id=entry_id)
    return {"entry_id": entry_id, "entry": data.get(entry_id)}


@mcp.tool
def list_entries(project_id: str = "proj-lessons", calling_role: str | None = None) -> dict:
    role = _effective_role(calling_role)
    _authorize("list_entries", role, project_id=project_id)
    data = _load_store()
    _record("list_entries", "success", role, project_id=project_id)
    return {"entry_ids": sorted(data)}


@mcp.tool
def update_entry(entry_id: str, title: str, content: str,
                 classification: str = "internal", entry_type: str = "lesson",
                 project_id: str = "proj-lessons", calling_role: str | None = None) -> dict:
    role = _effective_role(calling_role)
    _authorize("update_entry", role, classification=classification,
               project_id=project_id, entry_id=entry_id)
    data = _load_store()
    data[entry_id] = {
        "project_id": project_id, "entry_type": entry_type, "title": title,
        "content": content, "classification": classification,
    }
    _save_store(data)
    _record("update_entry", "success", role, classification=classification,
            project_id=project_id, entry_id=entry_id)
    return {"ok": True, "entry_id": entry_id}


@mcp.tool
def delete_entry(entry_id: str, project_id: str = "proj-lessons",
                 calling_role: str | None = None) -> dict:
    role = _effective_role(calling_role)
    _authorize("delete_entry", role, project_id=project_id, entry_id=entry_id)
    data = _load_store()
    existed = entry_id in data
    classification = data.get(entry_id, {}).get("classification")
    data.pop(entry_id, None)
    _save_store(data)
    _record("delete_entry", "success", role, classification=classification,
            project_id=project_id, entry_id=entry_id)
    return {"ok": True, "deleted": existed}


@mcp.tool
def audit_read(limit: int = 50, calling_role: str | None = None) -> dict:
    role = _effective_role(calling_role)
    _authorize("audit_read", role)
    if not AUDIT_LOG_PATH.exists():
        return {"entries": []}
    lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").splitlines()[-limit:]
    return {"entries": [json.loads(line) for line in lines if line.strip()]}


if __name__ == "__main__":
    mcp.run()