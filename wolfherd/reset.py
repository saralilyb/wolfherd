"""Reset shared Wolfram Global` state through the live MCP endpoint."""

from __future__ import annotations

import os
import sys

RESET_CODE = 'ClearAll["Global`*"]; Names["Global`*"]'


def _render(result) -> str:
    return "\n".join(
        getattr(block, "text", str(block)) for block in result.content
    )


async def _main(url: str) -> int:
    try:
        import anyio  # noqa: F401
        from mcp import ClientSession
        from mcp.client.streamable_http import streamablehttp_client
    except ImportError:
        print(
            "wolfherd reset needs the Python MCP SDK. Install mcp, or run "
            "the compatibility script with uv: bin/wolfherd-reset.",
            file=sys.stderr,
        )
        return 1

    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = (await session.list_tools()).tools
            evaluator = next((t for t in tools if "Evaluator" in t.name), None)
            if evaluator is None:
                print(
                    "no Wolfram Language evaluator tool found",
                    file=sys.stderr,
                )
                return 1
            schema = evaluator.inputSchema or {}
            required = schema.get("required", [])
            props = schema.get("properties", {})
            arg = required[0] if required else next(iter(props), "code")
            result = await session.call_tool(evaluator.name, {arg: RESET_CODE})
            print(_render(result))
            return 0


def reset(url: str) -> int:
    try:
        import anyio
    except ImportError:
        print(
            "wolfherd reset needs anyio and mcp. Run bin/wolfherd-reset "
            "to let uv supply those dependencies.",
            file=sys.stderr,
        )
        return 1
    return anyio.run(_main, url)
