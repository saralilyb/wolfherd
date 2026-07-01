# Platform supervisors

wolfherd has one client-facing surface and several install backends. The MCP
endpoint should behave the same everywhere:

```text
http://127.0.0.1:8765/mcp
```

## macOS: launchd

Use this on a Mac where Wolfram Desktop or Wolfram Engine is activated for the
interactive user.

```sh
bin/wolfherd install --platform macos
bin/wolfherd restart --platform macos
bin/wolfherd uninstall --platform macos
```

Defaults:

```text
supervisor: ~/Library/LaunchAgents/wolfherd.plist
wolfram:    /Applications/Wolfram.app/Contents/MacOS/wolfram
base:       /Library/Wolfram
userbase:   ~/Library/Wolfram
localbase:  ~/Library/Wolfram/Objects
logs:       ~/Library/Logs/wolfherd.log and .err.log
```

## Linux and WSL: systemd user service

Use this for a normal Linux workstation, or for WSL when it is acceptable that
wolfherd stops with the distro.

```sh
bin/wolfherd install --platform linux
systemctl --user status wolfherd.service
journalctl --user -u wolfherd.service -f
```

The Linux path defaults avoid hardcoding Wolfram base directories because
package layouts vary. Set these explicitly when needed:

```sh
export WOLFRAM_BIN=/opt/Wolfram/WolframEngine/15.0/Executables/wolfram
export WOLFRAM_BASE=...
export WOLFRAM_USERBASE=...
export WOLFRAM_LOCALBASE=...
```

For WSL on a Windows host, this is not the recommended durable Minerva shape:
WSL restarts stop the service. Prefer the Windows user Scheduled Task if
Windows Claude Desktop and WSL Hermes should share the same singleton kernel.
If you do intentionally launch a Windows `wolfram.exe` from WSL, wolfherd
prefers a visible Windows Wolfram install under `/mnt/c/Program Files/...` and
will try to discover a usable `/run/WSL/*_interop` socket at service start. If
none is visible, set `WSL_INTEROP` before starting the service; otherwise WSL
cannot exec the Windows binary and will fail with `Invalid argument` before
Wolfram starts.

## Windows: user Scheduled Task

Use this on the Windows host when Wolfram Desktop is activated for the user and
Windows clients such as Claude Desktop should share the same kernel.

```powershell
python -m wolfherd.cli install --platform windows
python -m wolfherd.cli restart --platform windows
python -m wolfherd.cli uninstall --platform windows
```

The task runs as the interactive user. Do not run wolfherd as LocalSystem by
default: Wolfram Desktop licensing and paclet/userbase state are user-profile
shaped, and LocalSystem will not naturally see the same activation state.

Defaults:

```text
supervisor: Windows Scheduled Task named wolfherd
wolfram:    C:\Program Files\Wolfram Research\Wolfram\15.0\wolfram.exe
base:       C:\ProgramData\Wolfram
userbase:   %APPDATA%\Wolfram
localbase:  %APPDATA%\Wolfram\Objects
```

If you run `bin/wolfherd install --platform windows --dry-run` from WSL, it
prints a PowerShell script for a Windows checkout. The actual supervisor should
be installed by Windows Python from the Windows-side repo path that will stay
available after WSL restarts.

## WSL Hermes to Windows wolfherd

Do not bind wolfherd to `0.0.0.0` just so WSL can reach it. The evaluator is
arbitrary local code execution.

Preferred bridges:

1. A stdio shim launched by the client that relays to Windows loopback without
   spawning Wolfram.
2. An authenticated reverse proxy bound to a WSL-reachable interface.
3. A private-network ACL plus `WOLFHERD_ALLOW_REMOTE=1`, only when you accept
   the remote-code-execution boundary.

Generate the stdio shim config with:

```sh
bin/wolfherd client stdio-shim --url http://127.0.0.1:8765/mcp
```

When the client is inside WSL and the broker is on Windows, replace the URL with
a Windows-reachable loopback/host address proven on that machine.

If Hermes directly launches a Windows `.exe` stdio server from WSL, add
`WSL_INTEROP: ${WSL_INTEROP}` to that server's `env` block. Hermes filters stdio
subprocess environments; without an explicit `WSL_INTEROP`, WSL reports
`Invalid argument` or the MCP client reports `Connection closed` even when the
Windows executable and license are healthy. wolfherd's own `serve` path tries to
discover a usable `/run/WSL/*_interop` socket automatically for WSL services,
but direct Hermes stdio MCP configs still need the explicit env value.
