"""Client configuration snippets for wolfherd."""

from __future__ import annotations

import json


def render_hermes(url: str, name: str = "wolfram") -> str:
    """Render a Hermes config fragment."""

    return (
        "mcp_servers:\n"
        f"  {name}:\n"
        f"    url: {url}\n"
        "    enabled: true\n"
    )


def render_claude(url: str, name: str = "Wolfram") -> str:
    """Render a Claude Code/Desktop mcpServers entry."""

    return (
        f'{json.dumps(name)}: {{\n'
        '  "type": "http",\n'
        f'  "url": {json.dumps(url)}\n'
        '}\n'
    )


def render_stdio_shim(url: str, version: str = "0.12.0") -> str:
    """Render a stdio MCP shim that relays to the shared HTTP endpoint."""

    return (
        "command: uvx\n"
        "args:\n"
        "  - --from\n"
        f"  - mcp-proxy=={version}\n"
        "  - mcp-proxy\n"
        "  - --transport\n"
        "  - streamablehttp\n"
        f"  - {url}\n"
    )


def render_client(
    client: str,
    url: str,
    name: str | None = None,
    version: str = "0.12.0",
) -> str:
    if client == "hermes":
        return render_hermes(url, name or "wolfram")
    if client == "claude":
        return render_claude(url, name or "Wolfram")
    if client == "stdio-shim":
        return render_stdio_shim(url, version)
    raise ValueError(f"unknown client: {client}")
