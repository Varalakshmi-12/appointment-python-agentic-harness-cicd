"""
Retrieval MCP server (stdio).

Thin transport wrapper. All ranking lives in retrieval_index.py (real TF-IDF
vector search + FTS5 keyword fallback over the lessons corpus) and all
governance in governance.py (per-role classification ceiling, withheld-audit,
citation shaping). This file only exposes the `retrieve` tool over stdio and
passes the caller's role through.

The replaced placeholder
------------------------
The earlier version of this server ranked with a word-count stub
(`score = sum(1 for term in query_terms if term in text)`) over three dummy
docs and carried a `# Replace with sqlite-vec / embedding search` TODO. That
stub is gone: ranking is now cosine similarity over a TF-IDF index built from
the eight real lesson files, verified by retrieval_eval.py (precision@1 = 6/6).

An embedding model was the first choice; its download is blocked by the
environment proxy (HuggingFace 403), so the ranker is TF-IDF, which is fully
offline and deterministic.

MCP API note
------------
Written for mcp >= 2.x, which registers handlers through the Server
constructor (on_list_tools / on_call_tool) rather than the older
@app.list_tools() decorators.

Prepared by: Varalakshmi
"""

from __future__ import annotations

import json
import os

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from governance import retrieve_with_governance
from retrieval_index import RetrievalIndex

AUDIT_PATH = os.environ.get(
    "RETRIEVAL_AUDIT_LOG",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "retrieval-audit.log"),
)

_INDEX = RetrievalIndex()  # built once at start-up

_RETRIEVE_TOOL = types.Tool(
    name="retrieve",
    description=(
        "Search the lessons corpus for prior-incident knowledge. "
        "Returns ranked citations (source_document, chunk_index, similarity, "
        "retrieval_method, classification). Enforces the caller's classification "
        "ceiling; documents above it are withheld and audited."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Natural-language query."},
            "calling_role": {
                "type": "string",
                "description": "The agent role making the call (ceiling enforced per role).",
            },
            "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10},
        },
        "required": ["query", "calling_role"],
    },
)


async def on_list_tools(ctx, params) -> types.ListToolsResult:
    return types.ListToolsResult(tools=[_RETRIEVE_TOOL])


# ---- RETRIEVE HANDLER: the only logic a pre-existing server needs ----------
async def on_call_tool(ctx, params) -> types.CallToolResult:
    if params.name != "retrieve":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"unknown tool: {params.name}")],
            is_error=True,
        )

    arguments = params.arguments or {}
    query = arguments["query"]
    calling_role = arguments["calling_role"]
    limit = int(arguments.get("limit", 5))

    try:
        citations = retrieve_with_governance(
            _INDEX, query, calling_role, AUDIT_PATH, limit=limit
        )
    except PermissionError as exc:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=str(exc))],
            is_error=True,
        )

    payload = {"query": query, "calling_role": calling_role, "citations": citations}
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=json.dumps(payload, indent=2))]
    )


app = Server("retrieval", on_list_tools=on_list_tools, on_call_tool=on_call_tool)


async def _main() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    import asyncio

    asyncio.run(_main())