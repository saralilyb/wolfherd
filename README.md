# wolfherd

One shared Wolfram kernel, herded for a pack of agents.

A Wolfram Desktop license allows a fixed number of controlling kernels at once
(`$MaxLicenseProcesses`, often 2). Each AI agent's Wolfram MCP server
(`StartMCPServer`) is a full controlling kernel that it holds for the whole
session — so two agents can consume every seat and the desktop app then hits
"License Limit Reached". wolfherd runs **one** kernel behind a local HTTP proxy
and points every agent at it, so all the agents share a single seat and the GUI
keeps the rest.

```
        launchd (RunAtLoad + KeepAlive)
                    |
                    v
      mcp-proxy  --spawns & supervises-->  ONE wolfram kernel
      127.0.0.1:8765                        (StartMCPServer, stdio)
      streamable-HTTP /mcp                  = 1 license seat
            ^   ^
            |   +-------- agent B (e.g. Hermes:      url: .../mcp)
            +------------ agent A (e.g. Claude Code: type: http)
```

## Why it works

`mcp-proxy` runs **stateful by default** (`--no-stateless`): one stdio backend
is shared across all client sessions, multiplexed by JSON-RPC id. The kernel is
single-threaded, so concurrent tool calls serialize naturally, and `Global``
state is shared across every agent.

Shared state is the deliberate trade. Keep it sane:

- **Scope scratch work:** wrap throwaway variables in `Module[{x, y}, ...]` so
  they never reach `Global`` and never collide.
- **Inspect before stomping:** `Names["Global`*"]` lists what is live.
- **Reset everyone:** `bin/wolfherd-reset` runs `ClearAll["Global`*"]` against
  the live kernel out-of-band (no agent needed). One reset, all agents clean.

## Security

The exposed `WolframLanguageEvaluator` runs **arbitrary Wolfram Language with
local file access and no authentication**. On loopback (`127.0.0.1`) that is
fine — only local processes reach it. On any routable interface it is an
unauthenticated remote shell.

- Keep `WOLFHERD_HOST=127.0.0.1` (the default).
- `bin/wolfherd-serve` refuses to bind a non-loopback host unless you set
  `WOLFHERD_ALLOW_REMOTE=1` — and you should only do that behind your own
  authenticating reverse proxy or a private-network ACL (e.g. a VPN with
  device-level access control).
- Treat anything sent to cloud-backed calls (`WolframAlpha`, `Entity`,
  `FreeformPrompt`) as egressing to Wolfram, authenticated as the licensed
  user. See `docs/egress.md`.

## Requirements

- Wolfram Desktop (or Wolfram Engine) with the `Wolfram/AgentTools` paclet.
- `uvx` (from Astral's uv). mcp-proxy is pinned in `bin/wolfherd-serve` and
  fetched on first run.
- macOS (the supervisor is a launchd LaunchAgent).

## Install

```sh
bin/wolfherd-install      # render LaunchAgent into ~/Library, bootstrap it
```

Verify:

```sh
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/mcp   # 406 = up
tail -f ~/Library/Logs/wolfherd.err.log
```

Editing `bin/wolfherd-serve`? `bin/wolfherd-restart` to pick it up.
`bin/wolfherd-uninstall` to remove.

### Kernel hygiene

The default `-run` is byte-identical to the stock per-agent stdio config, so
the JSON-RPC handshake is known-good. A kernel that runs for weeks keeps every
`Out[]`, so memory creeps slowly. Two options: `bin/wolfherd-restart`
periodically (cheap, also clears `Global``), or set `WOLFHERD_INIT` to cap
history — but verify it emits nothing to stdout first, since a stray byte there
corrupts the JSON-RPC stream:

```sh
WOLFHERD_INIT='$HistoryLength = 50;'
```

## Migrate the agents

Point each agent at the shared endpoint and delete its old stdio launcher.
Keep the server key named `Wolfram` everywhere so existing permission rules
still match.

- **Claude Code** — replace the `Wolfram` block in `~/.claude.json` with
  `clients/claude.json.frag`, then restart Claude Code.
- **Hermes** — replace the `Wolfram:` block under `mcp_servers:` in
  `~/.hermes/config.yaml` with `clients/hermes.config.yaml.frag`.
- **pi** and others — see `clients/pi.md`. Any stdio-only client can reach the
  shared kernel through a one-line mcp-proxy client shim instead of spawning
  its own.

After migrating, `ps aux | grep WolframKernel` should show one launchd-owned
kernel and nothing parented to an agent.

## Limits

- **Shared state** — a `ClearAll` from one agent wipes the slate for all. Don't
  reset mid-computation in another agent.
- **Serialized calls** — two agents calling at once queue behind the one
  kernel. Fine for light use.
- **Node-locked** — a node-locked Desktop license ties the kernel to one
  machine, so the endpoint binds to loopback there. Reaching it from another
  host needs the remote opt-in above plus your own auth.

## Layout

```
bin/wolfherd-serve       wrapper launchd runs (proxy + shared kernel)
bin/wolfherd-reset       ClearAll["Global`*"] against the live endpoint
bin/wolfherd-install     render + bootstrap the LaunchAgent
bin/wolfherd-uninstall   bootout + unlink
bin/wolfherd-restart     kickstart -k after edits
launchd/wolfherd.plist.in  LaunchAgent template
clients/                 per-agent config fragments
docs/egress.md           controlling the kernel's network egress
```

## License

ISC. See `LICENSE`. Not affiliated with Wolfram Research; "Wolfram" and
"Wolfram Language" are their trademarks.
