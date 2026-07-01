"""Diagnostic checks for wolfherd installations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import shutil
import subprocess
import sys

from .config import (
    WolfherdConfig,
    detect_platform,
    discover_wsl_interop,
    is_wsl,
    load_config,
    needs_wsl_interop,
)
from .serve import build_command, find_uvx
from .status import check_endpoint


@dataclass(frozen=True)
class Check:
    name: str
    ok: bool
    detail: str

    def render(self) -> str:
        marker = "ok" if self.ok else "fail"
        return f"[{marker}] {self.name}: {self.detail}"


def _exists_or_on_path(command: str) -> bool:
    if Path(command).exists():
        return True
    return shutil.which(command) is not None


def _wolfram_smoke(config: WolfherdConfig, timeout: int) -> Check:
    command = [
        config.paths.wolfram_bin,
        "-run",
        "Print[2+2]; Exit[]",
        "-noinit",
        "-noprompt",
    ]
    env = None
    if needs_wsl_interop(config.paths.wolfram_bin):
        interop = discover_wsl_interop()
        if not interop:
            return Check("wolfram smoke", False, "WSL_INTEROP not available")
        env = os.environ.copy()
        env["WSL_INTEROP"] = interop
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except FileNotFoundError:
        return Check("wolfram smoke", False, "Wolfram binary not found")
    except subprocess.TimeoutExpired:
        return Check("wolfram smoke", False, f"timed out after {timeout}s")

    output = (result.stdout + result.stderr).strip().replace("\r", "")
    if result.returncode == 0 and "4" in output:
        return Check("wolfram smoke", True, "2+2 evaluated successfully")
    if not output:
        output = f"exit code {result.returncode} with no output"
    return Check("wolfram smoke", False, output[:500])


def run_checks(smoke: bool = False) -> list[Check]:
    config = load_config()
    checks: list[Check] = []
    platform_name = detect_platform()
    checks.append(Check("platform", True, platform_name))
    checks.append(Check("wsl", True, "yes" if is_wsl() else "no"))
    checks.append(Check("license mode", True, config.license_mode))
    checks.append(Check("state model", True, config.state_model))

    uvx = find_uvx()
    checks.append(Check("uvx", _exists_or_on_path(uvx), uvx))
    wolfram = config.paths.wolfram_bin
    checks.append(Check("wolfram binary", _exists_or_on_path(wolfram), wolfram))
    if needs_wsl_interop(wolfram):
        interop = discover_wsl_interop()
        checks.append(
            Check(
                "wsl interop",
                bool(interop),
                interop or "missing; Windows .exe launch will fail",
            )
        )

    endpoint = check_endpoint(config.url)
    checks.append(Check("endpoint", True, endpoint.detail))

    if smoke:
        checks.append(_wolfram_smoke(config, timeout=25))

    command = build_command(config)
    checks.append(Check("serve command", True, " ".join(command)))
    return checks


def render_doctor(smoke: bool = False) -> str:
    lines = [check.render() for check in run_checks(smoke=smoke)]
    if not smoke:
        lines.append(
            "[info] wolfram smoke skipped; use --wolfram-smoke to start a "
            "kernel and test activation"
        )
    return "\n".join(lines) + "\n"


def doctor(smoke: bool = False) -> int:
    checks = run_checks(smoke=smoke)
    for check in checks:
        print(check.render())
    if not smoke:
        print(
            "[info] wolfram smoke skipped; use --wolfram-smoke to start a "
            "kernel and test activation"
        )
    return 0 if all(check.ok for check in checks) else 1
