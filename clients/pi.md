# pi and stdio-only clients

pi was not wired to Wolfram MCP when this repo was created, so it was not part
of the original license-seat contention.

If a client cannot speak HTTP MCP natively, use a stdio shim. The shim relays to
the shared HTTP endpoint and does not spawn Wolfram:

```yaml
command: uvx
args:
  - --from
  - mcp-proxy==0.12.0
  - mcp-proxy
  - --transport
  - streamablehttp
  - http://127.0.0.1:8765/mcp
```

Generate this with:

```sh
bin/wolfherd client stdio-shim
```

Do not point any stdio-only client at the old per-agent Wolfram launcher. That
spawns a fresh controlling kernel and reintroduces the license contention this
repo exists to remove.
