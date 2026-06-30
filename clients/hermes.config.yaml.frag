# Hermes — ~/.hermes/config.yaml, under the existing "mcp_servers:" map.
# REPLACE the current command/args/env "Wolfram:" block with this url form.
# Hermes connects to streamable-HTTP MCP servers natively (cli-config example
# uses `url: https://mcp.notion.com/mcp`), so no stdio shim is needed.
#
# If Hermes ever fails to connect on /mcp, fall back to the SSE endpoint
# (url: http://127.0.0.1:8765/sse) — mcp-proxy serves both.

mcp_servers:
  Wolfram:
    url: http://127.0.0.1:8765/mcp
    enabled: true
