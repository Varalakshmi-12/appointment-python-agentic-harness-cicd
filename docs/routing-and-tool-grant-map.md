# Routing and Tool Grant Map

| Role | Route condition | Storage operations | Retrieval | Notes |
|---|---|---|---|---|
| orchestrator | Parent workflow coordination | write_entry, read_entry, list_entries, update_entry, delete_entry, audit_read | retrieve, ceiling confidential | Coordinates and audits the run. |
| implementer | Code and implementation tasks | write_entry, read_entry, list_entries, update_entry | retrieve, ceiling internal | No delete access. |
| reviewer | Code review tasks | read_entry, list_entries | retrieve, ceiling internal | Advisory only. |

| project-manager | PR description and summaries | read_entry, list_entries | denied | Owns draft-pr-description. |

## Converted steps

- tester: converted from agent to deterministic code (scripts/run_tests_deterministic.py, ADR-001).
  No MCP access required; runs the project's test suite and reports pass/fail/error.