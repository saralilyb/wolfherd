# wolfherd

One shared Wolfram kernel, herded for a pack of agents.

A Wolfram Desktop license allows a fixed number of controlling kernels at once
(`$MaxLicenseProcesses`, often 2). Each AI agent's Wolfram MCP server
(`StartMCPServer`) is a full controlling kernel that it holds for the whole
session. Two agents can consume every seat, and the desktop app then hits
"License Limit Reached".

wolfherd runs one Wolfram MCP backend behind a local HTTP MCP proxy and points
every agent at it. All agents share one controlling process; the desktop GUI
keeps the remaining license capacity.

```text
        platform supervisor
   launchd | systemd --user | Windows Scheduled Task
                    |
                    v
      mcp-proxy  --spawns & supervises-->  ONE wolfram kernel
      127.0.0.1:8765                        (StartMCPServer, stdio)
      streamable-HTTP /mcp                  = 1 license seat
            ^   ^
            |   +-------- agent B (Hermes, Claude, stdio shim)
            +------------ agent A (Hermes, Claude, stdio shim)
```

## Status

The current implementation is the simple, robust mode:

```yaml
license_mode: existing_desktop_single_kernel
state_model: global
kernel_pool: 1
```

`mcp-proxy` is stateful by default: one stdio backend is shared across all
client sessions and JSON-RPC ids are multiplexed. The Wolfram kernel is
single-threaded, so concurrent tool calls serialize naturally.

Namespace-leased state is planned as the next broker layer. Today, `Global`` is
shared across every agent. That is deliberate for v0: one reset clears everyone.

## Security

The exposed `WolframLanguageEvaluator` runs arbitrary Wolfram Language with
local file access and no authentication. On loopback (`127.0.0.1`) that is
reasonable: only local processes reach it. On any routable interface it is an
unauthenticated remote shell.

- Keep `WOLFHERD_HOST=127.0.0.1` unless you have an auth layer.
- `wolfherd serve` refuses non-loopback hosts unless `WOLFHERD_ALLOW_REMOTE=1`.
- Use a stdio shim or an authenticated reverse proxy for cross-boundary clients.
- Treat cloud-backed calls (`WolframAlpha`, `Entity`, `FreeformPrompt`) as
  egressing to Wolfram as the licensed user. See `docs/egress.md`.

## Requirements

- Wolfram Desktop or Wolfram Engine with the `Wolfram/AgentTools` paclet.
- `uvx` from Astral's uv. wolfherd uses it to fetch a pinned `mcp-proxy`.
- Python 3.11+ for the portable CLI.

## Quick start

```sh
bin/wolfherd doctor
bin/wolfherd install
bin/wolfherd status
```

Compatibility wrappers still exist:

```sh
bin/wolfherd-install
bin/wolfherd-restart
bin/wolfherd-uninstall
bin/wolfherd-reset
```

The platform supervisor is selected automatically:

- macOS: LaunchAgent in `~/Library/LaunchAgents`.
- Linux/WSL: user unit in `~/.config/systemd/user`.
- Windows: user Scheduled Task, not LocalSystem.

Use `--dry-run` to inspect what would be installed:

```sh
bin/wolfherd install --platform macos --dry-run
bin/wolfherd install --platform linux --dry-run
bin/wolfherd install --platform windows --dry-run
```

See `docs/platforms.md` for platform defaults and caveats.

## Verify

```sh
bin/wolfherd status
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8765/mcp
```

Plain `GET /mcp` often returns 406; that still means the endpoint is up.

To test command-line Wolfram activation, run:

```sh
bin/wolfherd doctor --wolfram-smoke
```

That intentionally starts Wolfram briefly. If it reports a licensing problem,
fix the host's command-line Wolfram activation before installing wolfherd.

## Configure agents

Print client fragments instead of copying stale examples:

```sh
bin/wolfherd client hermes
bin/wolfherd client claude
bin/wolfherd client stdio-shim
```

Hermes usually wants the existing lowercase key:

```yaml
mcp_servers:
  wolfram:
    url: http://127.0.0.1:8765/mcp
    enabled: true
```

Claude examples keep `Wolfram` so existing permission rules continue to match.

## Kernel hygiene

A kernel that runs for weeks keeps every `Out[]`; memory can creep. Either
restart periodically, or cap history with an init expression that emits nothing
to stdout:

```sh
WOLFHERD_INIT='$HistoryLength = 50;'
```

Never let init code print. A stray byte on stdout corrupts the MCP JSON-RPC
stream.

Useful commands:

```sh
bin/wolfherd reset      # ClearAll["Global`*"] through the live endpoint
bin/wolfherd restart    # restart the supervised kernel/proxy
bin/wolfherd doctor     # inspect paths, endpoint, and optional activation
```

## License modes

wolfherd names the licensing assumption explicitly because the same service
surface can be backed by different entitlements:

- `existing_desktop_single_kernel` — default; use an installed Wolfram Desktop
  or Engine command-line kernel and enforce one controlling process.
- `free_engine_development` — future container/appliance mode for personal,
  development, testing, or demo work under Wolfram Engine Community Edition.
- `production_engine` — future appliance mode backed by a production/network
  Wolfram Engine entitlement.

Only the first mode is implemented here. Docker/Compose support is intentionally
out of scope for this pass. See `docs/license-modes.md`.

## Layout

```text
bin/wolfherd             portable CLI dispatcher
bin/wolfherd-serve       compatibility wrapper for wolfherd serve
bin/wolfherd-reset       uv-backed reset helper with MCP dependencies
wolfherd/                Python CLI and platform implementation
launchd/                 macOS LaunchAgent template
clients/                 static examples; prefer wolfherd client ...
docs/                    platform, licensing, and egress notes
tests/                   stdlib unittest coverage
```

## License

ISC. See `LICENSE`. Not affiliated with Wolfram Research; "Wolfram" and
"Wolfram Language" are their trademarks.
