import os
import subprocess
import unittest
from unittest.mock import patch

from wolfherd import supervisors
from wolfherd.clients import render_claude, render_hermes, render_stdio_shim
from wolfherd.config import (
    defaults_for_platform,
    is_loopback,
    needs_wsl_interop,
)
from wolfherd.serve import build_command
from wolfherd.config import WolfherdConfig, WolframPaths


class ClientRenderingTests(unittest.TestCase):
    def test_hermes_defaults_to_lowercase_server_key(self):
        text = render_hermes("http://127.0.0.1:8765/mcp")
        self.assertIn("  wolfram:", text)
        self.assertIn("url: http://127.0.0.1:8765/mcp", text)

    def test_claude_defaults_to_capitalized_server_key(self):
        text = render_claude("http://127.0.0.1:8765/mcp")
        self.assertIn('"Wolfram"', text)
        self.assertIn('"type": "http"', text)

    def test_stdio_shim_does_not_spawn_wolfram(self):
        text = render_stdio_shim("http://127.0.0.1:8765/mcp")
        self.assertIn("mcp-proxy==0.12.0", text)
        self.assertNotIn("wolfram.exe", text)
        self.assertNotIn("StartMCPServer", text)


class ConfigTests(unittest.TestCase):
    def test_loopback_guard_values(self):
        self.assertTrue(is_loopback("127.0.0.1"))
        self.assertTrue(is_loopback("localhost"))
        self.assertFalse(is_loopback("0.0.0.0"))

    def test_windows_defaults_use_user_profile_paths(self):
        paths = defaults_for_platform("windows")
        self.assertIn("Wolfram Research", paths.wolfram_bin)
        self.assertIn("ProgramData", paths.wolfram_base)
        self.assertIn("Wolfram", paths.wolfram_userbase)

    def test_wsl_interop_detection_is_false_for_linux_paths(self):
        self.assertFalse(needs_wsl_interop("/usr/bin/wolfram"))


class ServeCommandTests(unittest.TestCase):
    def test_build_command_uses_one_stdio_backend(self):
        cfg = WolfherdConfig(
            host="127.0.0.1",
            port=8765,
            paths=WolframPaths(
                wolfram_bin="/Applications/Wolfram.app/Contents/MacOS/wolfram",
                wolfram_base="/Library/Wolfram",
                wolfram_userbase="/Users/sara/Library/Wolfram",
                wolfram_localbase="/Users/sara/Library/Wolfram/Objects",
            ),
            mcp_proxy_version="0.12.0",
            license_mode="existing_desktop_single_kernel",
            state_model="global",
            init="",
            allow_remote=False,
        )
        command = build_command(cfg)
        self.assertEqual(command.count("--"), 1)
        self.assertIn("mcp-proxy==0.12.0", command)
        self.assertIn("MCP_SERVER_NAME", command)
        self.assertIn("Wolfram", command)
        self.assertIn("-run", command)

    def test_build_command_passes_wsl_interop_for_windows_exe(self):
        cfg = WolfherdConfig(
            host="127.0.0.1",
            port=8765,
            paths=WolframPaths(wolfram_bin="/mnt/c/Wolfram/wolfram.exe"),
            mcp_proxy_version="0.12.0",
            license_mode="existing_desktop_single_kernel",
            state_model="global",
            init="",
            allow_remote=False,
        )
        with patch.dict(
            os.environ,
            {"WSL_INTEROP": "/run/WSL/test_interop"},
        ):
            command = build_command(cfg)
        if needs_wsl_interop(cfg.paths.wolfram_bin):
            self.assertIn("WSL_INTEROP", command)
            self.assertIn("/run/WSL/test_interop", command)


class _FakeLaunchd:
    """Model launchd's async bootout: print keeps reporting the label loaded
    for a few polls after bootout, before it finally disappears."""

    def __init__(self, polls_until_clear=2):
        self.loaded = True
        self.calls = []
        self._pending = None
        self._polls_until_clear = polls_until_clear
        self.bootstrap_saw_loaded = None

    def run(self, cmd, *args, **kwargs):
        sub = cmd[1]
        self.calls.append(sub)
        if sub == "print":
            if self._pending is not None and self._pending > 0:
                self._pending -= 1
                if self._pending == 0:
                    self.loaded = False
            return subprocess.CompletedProcess(cmd, 0 if self.loaded else 1)
        if sub == "bootout":
            self._pending = self._polls_until_clear
            return subprocess.CompletedProcess(cmd, 0)
        if sub == "bootstrap":
            self.bootstrap_saw_loaded = self.loaded
            # launchd rejects a bootstrap that races teardown with EIO.
            return subprocess.CompletedProcess(cmd, 5 if self.loaded else 0)
        return subprocess.CompletedProcess(cmd, 0)


class SupervisorInstallTests(unittest.TestCase):
    def test_install_macos_waits_for_teardown_before_bootstrap(self):
        fake = _FakeLaunchd(polls_until_clear=2)
        with patch.object(supervisors, "_write"), patch.object(
            supervisors.time, "sleep"
        ), patch.object(supervisors.subprocess, "run", fake.run):
            supervisors.install_macos(dry_run=False)

        # bootstrap must run, and never while the label was still loaded.
        self.assertIs(fake.bootstrap_saw_loaded, False)
        self.assertIn("bootout", fake.calls)
        self.assertIn("bootstrap", fake.calls)
        self.assertLess(
            fake.calls.index("bootout"), fake.calls.index("bootstrap")
        )
        # at least one poll happened between bootout and bootstrap.
        between = fake.calls[
            fake.calls.index("bootout") + 1 : fake.calls.index("bootstrap")
        ]
        self.assertIn("print", between)

    def test_install_macos_skips_bootout_when_not_loaded(self):
        fake = _FakeLaunchd()
        fake.loaded = False
        with patch.object(supervisors, "_write"), patch.object(
            supervisors.time, "sleep"
        ), patch.object(supervisors.subprocess, "run", fake.run):
            supervisors.install_macos(dry_run=False)

        self.assertNotIn("bootout", fake.calls)
        self.assertIn("bootstrap", fake.calls)

    def test_wait_until_unloaded_returns_false_on_timeout(self):
        with patch.object(
            supervisors, "_service_loaded", return_value=True
        ), patch.object(supervisors.time, "sleep") as sleep:
            result = supervisors._wait_until_unloaded("t", tries=3, delay=0.01)
        self.assertFalse(result)
        self.assertEqual(sleep.call_count, 3)


if __name__ == "__main__":
    unittest.main()
