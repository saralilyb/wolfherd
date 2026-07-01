"""Runtime configuration and platform defaults for wolfherd."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import platform as platform_mod
import shutil
import sys

LOOPBACK_HOSTS = {"127.0.0.1", "::1", "localhost"}


@dataclass(frozen=True)
class WolframPaths:
    """Paths passed to the Wolfram MCP stdio backend."""

    wolfram_bin: str
    wolfram_base: str | None = None
    wolfram_userbase: str | None = None
    wolfram_localbase: str | None = None


@dataclass(frozen=True)
class WolfherdConfig:
    """Complete runtime config for the shared MCP proxy."""

    host: str
    port: int
    paths: WolframPaths
    mcp_proxy_version: str
    license_mode: str
    state_model: str
    init: str
    allow_remote: bool

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/mcp"


def detect_platform() -> str:
    """Return wolfherd's normalized platform name."""

    if sys.platform == "darwin":
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return "linux"


def is_wsl() -> bool:
    """Best-effort WSL detection."""

    if sys.platform.startswith("win"):
        return False
    release = platform_mod.release().lower()
    version = platform_mod.version().lower()
    return "microsoft" in release or "microsoft" in version or "wsl" in release


def needs_wsl_interop(command: str) -> bool:
    """Return true when WSL must launch a Windows executable."""

    lowered = command.lower()
    return is_wsl() and (
        lowered.endswith(".exe") or lowered.startswith("/mnt/")
    )


def discover_wsl_interop() -> str | None:
    """Return a usable WSL interop socket if one is visible."""

    current = os.environ.get("WSL_INTEROP")
    if current:
        return current

    root = Path("/run/WSL")
    if not root.exists():
        return None

    sockets = [path for path in root.glob("*_interop") if path.is_socket()]
    if not sockets:
        return None
    sockets.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return str(sockets[0])


def _wsl_windows_user() -> str | None:
    """Find the most likely Windows user for WSL-hosted installs."""

    candidates = [
        os.environ.get("WOLFHERD_WINDOWS_USER"),
        os.environ.get("USERNAME"),
        os.environ.get("USER"),
    ]
    users_root = Path("/mnt/c/Users")
    for candidate in candidates:
        if not candidate:
            continue
        appdata = users_root / candidate / "AppData" / "Roaming"
        if appdata.exists():
            return candidate
    return None


def _wsl_wolfram_paths(version: str) -> WolframPaths | None:
    """Prefer the Windows Wolfram install when running inside WSL."""

    exe = Path(
        "/mnt/c/Program Files/Wolfram Research/Wolfram"
    ) / version / "wolfram.exe"
    if not exe.exists():
        return None

    windows_user = _wsl_windows_user()
    appdata = None
    if windows_user:
        appdata = rf"C:\Users\{windows_user}\AppData\Roaming"

    return WolframPaths(
        wolfram_bin=str(exe),
        wolfram_base=r"C:\ProgramData\Wolfram",
        wolfram_userbase=(appdata + r"\Wolfram") if appdata else None,
        wolfram_localbase=(
            appdata + r"\Wolfram\Objects" if appdata else None
        ),
    )


def is_loopback(host: str) -> bool:
    return host in LOOPBACK_HOSTS


def _path_home(*parts: str) -> str:
    return str(Path.home().joinpath(*parts))


def defaults_for_platform(name: str | None = None) -> WolframPaths:
    """Return conservative Wolfram defaults for a platform.

    Environment variables still override these in load_config(). Linux defaults
    avoid hardcoding base dirs because distro/package layouts vary; operators
    can set WOLFRAM_BASE, WOLFRAM_USERBASE, and WOLFRAM_LOCALBASE explicitly.
    """

    platform_name = name or detect_platform()
    version = os.environ.get("WOLFHERD_WOLFRAM_VERSION", "15.0")

    if platform_name == "macos":
        return WolframPaths(
            wolfram_bin="/Applications/Wolfram.app/Contents/MacOS/wolfram",
            wolfram_base="/Library/Wolfram",
            wolfram_userbase=_path_home("Library", "Wolfram"),
            wolfram_localbase=_path_home("Library", "Wolfram", "Objects"),
        )

    if platform_name == "windows":
        program_files = os.environ.get("ProgramFiles", r"C:\Program Files")
        appdata = os.environ.get(
            "APPDATA",
            str(Path.home() / "AppData" / "Roaming"),
        )
        return WolframPaths(
            wolfram_bin=(
                program_files
                + rf"\Wolfram Research\Wolfram\{version}\wolfram.exe"
            ),
            wolfram_base=r"C:\ProgramData\Wolfram",
            wolfram_userbase=appdata + r"\Wolfram",
            wolfram_localbase=appdata + r"\Wolfram\Objects",
        )

    if is_wsl():
        wsl_paths = _wsl_wolfram_paths(version)
        if wsl_paths:
            return wsl_paths

    wolfram_bin = shutil.which("wolfram")
    if not wolfram_bin:
        wolfram_bin = (
            f"/opt/Wolfram/WolframEngine/{version}/Executables/wolfram"
        )
    return WolframPaths(wolfram_bin=wolfram_bin)


def load_config(platform_name: str | None = None) -> WolfherdConfig:
    """Load config from platform defaults plus WOLFHERD_* variables."""

    defaults = defaults_for_platform(platform_name)
    paths = WolframPaths(
        wolfram_bin=os.environ.get("WOLFRAM_BIN", defaults.wolfram_bin),
        wolfram_base=os.environ.get("WOLFRAM_BASE", defaults.wolfram_base),
        wolfram_userbase=os.environ.get(
            "WOLFRAM_USERBASE",
            defaults.wolfram_userbase,
        ),
        wolfram_localbase=os.environ.get(
            "WOLFRAM_LOCALBASE",
            defaults.wolfram_localbase,
        ),
    )
    return WolfherdConfig(
        host=os.environ.get("WOLFHERD_HOST", "127.0.0.1"),
        port=int(os.environ.get("WOLFHERD_PORT", "8765")),
        paths=paths,
        mcp_proxy_version=os.environ.get("MCP_PROXY_VERSION", "0.12.0"),
        license_mode=os.environ.get(
            "WOLFHERD_LICENSE_MODE",
            "existing_desktop_single_kernel",
        ),
        state_model=os.environ.get("WOLFHERD_STATE_MODEL", "global"),
        init=os.environ.get("WOLFHERD_INIT", ""),
        allow_remote=os.environ.get("WOLFHERD_ALLOW_REMOTE", "") == "1",
    )


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
