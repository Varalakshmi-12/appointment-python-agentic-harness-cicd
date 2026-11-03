
"""Probe an MCP server's _authorize gate directly, with AGENT_ROLE set.

Demonstrates least-privilege enforcement without the MCP Inspector: it imports
the server module (which reads CALLING_ROLE from AGENT_ROLE at import) and calls
the server's own _authorize() for one operation. A denied call raises, exactly as
it would for a real tool call, and the server writes the same audit record.

Usage:
    AGENT_ROLE=<role> python3 scripts/probe.py <path/to/server.py> <operation>

Examples:
    AGENT_ROLE=implementer python3 scripts/probe.py mcp-servers/storage/server.py delete_entry
    AGENT_ROLE=implementer python3 scripts/probe.py mcp-servers/storage/server.py write_entry
"""
import sys
import importlib.util


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: AGENT_ROLE=<role> python3 scripts/probe.py <server.py> <operation>")
        return 2
    server_path, operation = sys.argv[1], sys.argv[2]
    spec = importlib.util.spec_from_file_location("srv_under_test", server_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        module._authorize(operation)
        print(f"ALLOWED: {operation}")
        return 0
    except Exception as exc:  # the server raises ToolError on an unauthorized op
        print(f"DENIED: {operation} -> {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())