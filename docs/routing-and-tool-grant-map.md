# Routing and Tool Grant Map

Derived from the enforced allow-lists: `mcp-servers/storage/allow-list.json` and
`mcp-servers/retrieval/retrieval-grants.json`. This table is the human-readable view
of those files; if they change, this table changes with them.

| Role | Storage operations | Retrieval | Notes |
|---|---|---|---|
| orchestrator | write_entry, read_entry, list_entries, update_entry, delete_entry, audit_read | retrieve, ceiling confidential | Coordinates and audits the run; only role with update/delete/audit. |
| implementer | write_entry | denied | Write-only: records lessons, does not read or retrieve them. |
| planner | — | retrieve, ceiling internal | Consumes prior lessons; no storage access. |
| security-reviewer | — | retrieve, ceiling internal | Advisory; reaches knowledge through retrieval only. |
| reviewer | read_entry, list_entries | retrieve, ceiling internal | Advisory. |
| code-reviewer | — | retrieve, ceiling internal | Advisory. |
| quality_reviewer | — | retrieve, ceiling internal | Advisory. |
| dependency-auditor | read_entry, list_entries | retrieve, ceiling internal | Reads lessons and the stored audit trail. |
| tester | read_entry, list_entries | retrieve, ceiling internal | Grants remain in the allow-list though the step now runs as deterministic code (ADR-001); it exercises none of them. |
| project-manager | read_entry, list_entries | denied | Owns draft-pr-description; reads summaries but performs no retrieval. |

## Converted steps

- tester: converted from agent to deterministic code (scripts/run_tests_deterministic.py, ADR-001).
  The allow-list still carries its grants for traceability; the deterministic step uses no MCP access —
  it runs the project's test suite and reports pass/fail/error.