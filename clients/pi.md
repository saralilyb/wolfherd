# pi — UNVERIFIED

pi (0.80.x) configures tools through its *extension* system (`pi install`,
`~/.pi/agent/settings.json` → `skills`/`packages`), not through an
`mcp_servers` map like Claude Code or Hermes. There is no Wolfram MCP wired
into pi today, so pi is not currently consuming a Wolfram license seat — it was
never part of the contention.

If you later want pi to reach the shared kernel, confirm pi's MCP mechanism
first (`pi --help`, the website MCP docs), then use whichever applies:

- Native HTTP, if pi grows a url-based server config:

      url: http://127.0.0.1:8765/mcp

- stdio shim, if pi only spawns command-based servers — bridge HTTP back to
  stdio with mcp-proxy in client mode (this spawns no kernel; it just relays to
  the shared one):

      command: uvx          # or an absolute path if uvx is not on PATH
      args:
        - --from
        - mcp-proxy==0.12.0
        - mcp-proxy
        - --transport
        - streamablehttp
        - http://127.0.0.1:8765/mcp

Do not point pi at the old `/Applications/Wolfram.app/.../wolfram` stdio
launcher — that spawns a fresh kernel and reintroduces the seat contention this
repo exists to remove.
