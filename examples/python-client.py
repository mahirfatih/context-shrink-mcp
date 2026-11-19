"""Minimal MCP client for Context Shrink (requires ``mcp>=2.0``).

Starts the server over stdio, lists its tools and calls one of them. Run it with
the same interpreter that has ``mcp`` installed:

    python examples/python-client.py [path/to/context-shrink.py]
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

DEFAULT_SERVER = Path(__file__).resolve().parents[1] / "context-shrink.py"


async def main(server_file: str) -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[server_file],
        # Optional: force the dependency-free counter so the numbers are stable.
        env={"CONTEXT_SHRINK_TOKENIZER": "heuristic"},
    )

    async with Client(server) as client:
        tools = await client.list_tools()
        print("tools:", [tool.name for tool in tools.tools])

        result = await client.call_tool(
            "estimate_context",
            {
                "messages": [{"role": "user", "content": "x" * 40}],
                "max_context_tokens": 4,
            },
        )
        payload = json.loads(result.content[0].text)
        print("estimate_context ->", payload)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_SERVER)
    asyncio.run(main(target))
