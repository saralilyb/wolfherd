"""Platform-specific installation supervisors for wolfherd."""

from __future__ import annotations

from pathlib import Path
import os
import shlex
import subprocess
import sys
import time

from .config import detect_platform, repo_root

LABEL = "wolfherd"


def _bin() -> Path:
    return repo_root() / "bin" / "wolfherd"


def _run(command: list[str], dry_run: bool = False) -> None:
    if dry_run:
        print(" ".join(shlex.quote(part) for part in command))
        return
    subprocess.run(command, check=True)


def _write(path: Path, content: str, dry_run: bool = False) -> None:
    if dry_run:
        print(f"--- {path}")
        print(content)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


# Standard macOS locations for the daemon PATH. launchd starts the job with a
# clean environment, so the plist must carry its own PATH -- but a *fixed* one,
# not a snapshot of the installer's interactive PATH. Snapshotting used to bake
# transient per-tool dirs (pnpm, bun, ...) into the daemon and leave them stale
# when those tools moved or were removed. The job only needs uvx (added
# explicitly below); wolfram is invoked by absolute path on macOS.
_STD_MACOS_PATH = (
    "/opt/homebrew/bin",
    "/opt/homebrew/sbin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
    "/usr/sbin",
    "/sbin",
)


def _daemon_path(uvx_dir: str) -> str:
    dirs = [uvx_dir, *(d for d in _STD_MACOS_PATH if d != uvx_dir)]
    return ":".join(dirs)


def _launchd_content() -> str:
    template = repo_root() / "launchd" / "wolfherd.plist.in"
    uvx = os.environ.get("WOLFHERD_UVX") or shlex.quote(
        str(Path.home() / ".local" / "bin" / "uvx")
    )
    uvx_dir = str(Path(uvx.strip("'\"")).parent)
    return (
        template.read_text()
        .replace("@SERVE@", str(repo_root() / "bin" / "wolfherd-serve"))
        .replace("@PATH@", _daemon_path(uvx_dir))
        .replace("@HOME@", str(Path.home()))
        .replace("@LOGDIR@", str(Path.home() / "Library" / "Logs"))
    )


def _launchctl(args: list[str]) -> subprocess.CompletedProcess[bytes]:
    """Run a launchctl subcommand, swallowing output for state probes."""

    return subprocess.run(
        ["launchctl", *args],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _service_loaded(target: str) -> bool:
    return _launchctl(["print", target]).returncode == 0


def _wait_until_unloaded(
    target: str, tries: int = 50, delay: float = 0.1
) -> bool:
    """Block until launchd forgets the service so bootstrap won't race it.

    launchctl bootout returns before teardown completes; bootstrapping while
    the domain still lists the label fails with EIO (error 5). Poll until
    print can no longer find the target. Returns False if it never clears.
    """

    for _ in range(tries):
        if not _service_loaded(target):
            return True
        time.sleep(delay)
    return False


def install_macos(dry_run: bool = False) -> None:
    dest = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    domain = f"gui/{os.getuid()}"
    target = f"{domain}/{LABEL}"
    _write(dest, _launchd_content(), dry_run=dry_run)
    if not dry_run and _service_loaded(target):
        _launchctl(["bootout", target])
        if not _wait_until_unloaded(target):
            print(
                f"wolfherd: {target} did not unload in time; "
                "bootstrap may fail. Retry, or run 'wolfherd restart'.",
                file=sys.stderr,
            )
    _run(["launchctl", "bootstrap", domain, str(dest)], dry_run=dry_run)
    print(f"wolfherd loaded; endpoint http://127.0.0.1:8765/mcp")


def _systemd_content() -> str:
    wolfherd = _bin()
    path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
    return f"""[Unit]
Description=wolfherd shared Wolfram MCP proxy
After=network-online.target

[Service]
Type=simple
Environment=PATH={path}
ExecStart={wolfherd} serve
Restart=on-failure
RestartSec=10

[Install]
WantedBy=default.target
"""


def install_linux(dry_run: bool = False) -> None:
    dest = Path.home() / ".config" / "systemd" / "user" / f"{LABEL}.service"
    _write(dest, _systemd_content(), dry_run=dry_run)
    _run(["systemctl", "--user", "daemon-reload"], dry_run=dry_run)
    _run(
        ["systemctl", "--user", "enable", "--now", f"{LABEL}.service"],
        dry_run=dry_run,
    )
    print(f"wolfherd loaded; endpoint http://127.0.0.1:8765/mcp")


def _windows_install_script() -> str:
    root = str(repo_root())
    python = sys.executable
    return f"""$ErrorActionPreference = 'Stop'
$TaskName = 'wolfherd'
$Python = '{python}'
$Repo = '{root}'
$Args = '-m wolfherd.cli serve'
$Action = New-ScheduledTaskAction `
  -Execute $Python `
  -Argument $Args `
  -WorkingDirectory $Repo
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet `
  -RestartCount 3 `
  -RestartInterval (New-TimeSpan -Minutes 1) `
  -ExecutionTimeLimit (New-TimeSpan -Days 0)
Register-ScheduledTask `
  -TaskName $TaskName `
  -Action $Action `
  -Trigger $Trigger `
  -Settings $Settings `
  -Description 'Shared Wolfram MCP proxy for local agents' `
  -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Write-Host 'wolfherd task registered; endpoint http://127.0.0.1:8765/mcp'
"""


def install_windows(dry_run: bool = False) -> None:
    script = _windows_install_script()
    if not sys.platform.startswith("win") or dry_run:
        print(script)
        if not sys.platform.startswith("win"):
            print(
                "Run this from a Windows checkout with the Windows Python "
                "that should supervise wolfherd.",
                file=sys.stderr,
            )
        return
    command = [
        "powershell.exe",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        script,
    ]
    _run(command)


def install(platform_name: str | None = None, dry_run: bool = False) -> None:
    target = platform_name or detect_platform()
    if target == "macos":
        install_macos(dry_run=dry_run)
        return
    if target == "linux":
        install_linux(dry_run=dry_run)
        return
    if target == "windows":
        install_windows(dry_run=dry_run)
        return
    raise SystemExit(f"unsupported platform: {target}")


def restart(platform_name: str | None = None, dry_run: bool = False) -> None:
    target = platform_name or detect_platform()
    if target == "macos":
        _run(
            ["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{LABEL}"],
            dry_run,
        )
    elif target == "linux":
        _run(["systemctl", "--user", "restart", f"{LABEL}.service"], dry_run)
    elif target == "windows":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            (
                f"Stop-ScheduledTask -TaskName {LABEL!r} -ErrorAction "
                f"SilentlyContinue; Start-ScheduledTask -TaskName {LABEL!r}"
            ),
        ]
        _run(command, dry_run)
    else:
        raise SystemExit(f"unsupported platform: {target}")
    print(f"restarted {LABEL}")


def uninstall(platform_name: str | None = None, dry_run: bool = False) -> None:
    target = platform_name or detect_platform()
    if target == "macos":
        dest = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
        if not dry_run:
            subprocess.run(
                ["launchctl", "bootout", f"gui/{os.getuid()}/{LABEL}"],
                check=False,
                stderr=subprocess.DEVNULL,
            )
            dest.unlink(missing_ok=True)
        else:
            print(f"launchctl bootout gui/{os.getuid()}/{LABEL}")
            print(f"rm -f {shlex.quote(str(dest))}")
    elif target == "linux":
        service = (
            Path.home()
            / ".config"
            / "systemd"
            / "user"
            / f"{LABEL}.service"
        )
        _run(
            ["systemctl", "--user", "disable", "--now", f"{LABEL}.service"],
            dry_run,
        )
        if dry_run:
            print(f"rm -f {shlex.quote(str(service))}")
        else:
            service.unlink(missing_ok=True)
            _run(["systemctl", "--user", "daemon-reload"], dry_run)
    elif target == "windows":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            f"Unregister-ScheduledTask -TaskName {LABEL!r} -Confirm:$false",
        ]
        _run(command, dry_run)
    else:
        raise SystemExit(f"unsupported platform: {target}")
    print(f"uninstalled {LABEL}")
