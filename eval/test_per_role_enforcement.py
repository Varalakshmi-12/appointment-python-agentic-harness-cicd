"""Per-role enforcement test (Governance is testable).

Least-privilege holds in a LIVE, shared-container session because the storage
server authorizes on the per-call `calling_role`, not the container's single
AGENT_ROLE. The container is run as `orchestrator` (as in a real session); a
policy-bypass attempt — the Implementer reaching for `delete_entry` or
`read_entry` — is shown FAILING anyway, because the allow-list is enforced
against the real calling role.

Run: python -m pytest eval/test_per_role_enforcement.py -q
Prepared by: Varalakshmi
"""
import os
import sys
import tempfile

import pytest

# The container runs as orchestrator, exactly as in a real orchestrated session.
os.environ["AGENT_ROLE"] = "orchestrator"
_TMP = tempfile.mkdtemp()
os.environ["STORAGE_AUDIT_LOG"] = os.path.join(_TMP, "audit.jsonl")
os.environ["STORAGE_STORE"] = os.path.join(_TMP, "store.json")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "mcp-servers", "storage"))
import server  # noqa: E402
from server import ToolError  # noqa: E402


def test_implementer_can_write():
    assert server.write_entry(title="t", content="c", calling_role="implementer")["ok"]


def test_implementer_cannot_delete_even_in_orchestrator_container():
    r = server.write_entry(title="t", content="c", calling_role="implementer")
    with pytest.raises(ToolError):
        server.delete_entry(entry_id=r["entry_id"], calling_role="implementer")


def test_implementer_cannot_read():
    r = server.write_entry(title="t", content="c", calling_role="implementer")
    with pytest.raises(ToolError):
        server.read_entry(entry_id=r["entry_id"], calling_role="implementer")


def test_orchestrator_can_delete():
    r = server.write_entry(title="t", content="c", calling_role="orchestrator")
    assert server.delete_entry(entry_id=r["entry_id"], calling_role="orchestrator")["ok"]


def test_audit_records_real_role_not_unknown():
    server.write_entry(title="t", content="c", calling_role="implementer")
    lines = open(os.environ["STORAGE_AUDIT_LOG"]).read().splitlines()
    assert any('"calling_role": "implementer"' in ln for ln in lines)
    assert not any('"calling_role": "unknown"' in ln for ln in lines)