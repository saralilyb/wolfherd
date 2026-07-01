"""Serve one shared Wolfram MCP backend through mcp-proxy."""

from __future__ import annotations

from pathlib import Path
import os
import shutil
import subprocess
import sys

from .config import (
    WolfherdConfig,
    discover_wsl_interop,
    is_loopback,
    load_config,
    needs_wsl_interop,
)

START_EXPR = (
    'PacletSymbol["Wolfram/AgentTools",'
    '"Wolfram`AgentTools`StartMCPServer"][]'
)


def find_uvx() -> str:
    """Find uvx without assuming launch supervisors inherit a shell PATH."""

    env_uvx = os.environ.get("WOLFHERD_UVX")
    if env_uvx:
        return env_uvx
    found = shutil.which("uvx")
    if found:
        return found
    return str(Path.home() / ".local" / "bin" / "uvx")


def _env_args(config: WolfherdConfig) -> list[str]:
    pairs = {
        "MCP_SERVER_NAME": "Wolfram",
        "WOLFRAM_BASE": config.paths.wolfram_base,
        "WOLFRAM_USERBASE": config.paths.wolfram_userbase,
        "WOLFRAM_LOCALBASE": config.paths.wolfram_localbase,
    }
    if needs_wsl_interop(config.paths.wolfram_bin):
        pairs["WSL_INTEROP"] = discover_wsl_interop()
    out: list[str] = []
    for key, value in pairs.items():
        if value:
            out.extend(["-e", key, value])
    return out


def build_command(config: WolfherdConfig) -> list[str]:
    """Build the mcp-proxy command line without executing it."""

    command = [
        find_uvx(),
        "--from",
        f"mcp-proxy=={config.mcp_proxy_version}",
        "mcp-proxy",
        "--host",
        config.host,
        "--port",
        str(config.port),
    ]
    command.extend(_env_args(config))
    command.extend(
        [
            "--",
            config.paths.wolfram_bin,
            "-run",
            f"{config.init}{START_EXPR}",
            "-noinit",
            "-noprompt",
        ]
    )
    return command


def ensure_safe_bind(config: WolfherdConfig) -> None:
    """Refuse unauthenticated arbitrary-code endpoints on routable hosts."""

    if is_loopback(config.host) or config.allow_remote:
        return
    print(
        f"wolfherd: refusing to bind non-loopback host {config.host!r}.",
        file=sys.stderr,
    )
    print(
        "  The evaluator is arbitrary local code execution with no auth.",
        file=sys.stderr,
    )
    print(
        "  Set WOLFHERD_ALLOW_REMOTE=1 only behind your own auth/ACL.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def ensure_wsl_interop(config: WolfherdConfig) -> None:
    """Fail early when WSL cannot launch the configured Windows binary."""

    if not needs_wsl_interop(config.paths.wolfram_bin):
        return
    if os.environ.get("WSL_INTEROP"):
        return
    interop = discover_wsl_interop()
    if interop:
        os.environ["WSL_INTEROP"] = interop
        return
    print(
        "wolfherd: WSL_INTEROP is required to launch a Windows Wolfram "
        "binary from WSL.",
        file=sys.stderr,
    )
    print(
        "  Prefer running wolfherd on the Windows host, or launch from a "
        "WSL session with WSL_INTEROP set.",
        file=sys.stderr,
    )
    raise SystemExit(1)


def serve(config: WolfherdConfig | None = None) -> int:
    """Run mcp-proxy in the foreground."""

    cfg = config or load_config()
    ensure_safe_bind(cfg)
    ensure_wsl_interop(cfg)
    command = build_command(cfg)
    if os.name == "posix":
        os.execvp(command[0], command)
    return subprocess.call(command)
