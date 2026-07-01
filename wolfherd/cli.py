"""Command-line interface for wolfherd."""

from __future__ import annotations

import argparse
import sys

from .clients import render_client
from .config import load_config
from .doctor import doctor
from .reset import reset
from .serve import serve
from .status import check_endpoint
from .supervisors import install, restart, uninstall

PLATFORMS = ("macos", "linux", "windows")
CLIENTS = ("hermes", "claude", "stdio-shim")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wolfherd",
        description="Run one shared Wolfram MCP kernel for local agents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("serve", help="run the shared MCP proxy in the foreground")

    install_p = sub.add_parser(
        "install",
        help="install the platform supervisor",
    )
    install_p.add_argument("--platform", choices=PLATFORMS)
    install_p.add_argument("--dry-run", action="store_true")

    uninstall_p = sub.add_parser("uninstall", help="remove the supervisor")
    uninstall_p.add_argument("--platform", choices=PLATFORMS)
    uninstall_p.add_argument("--dry-run", action="store_true")

    restart_p = sub.add_parser("restart", help="restart the supervised proxy")
    restart_p.add_argument("--platform", choices=PLATFORMS)
    restart_p.add_argument("--dry-run", action="store_true")

    status_p = sub.add_parser("status", help="check the HTTP MCP endpoint")
    status_p.add_argument("--json", action="store_true")
    status_p.add_argument("--url")

    doctor_p = sub.add_parser("doctor", help="diagnose the local setup")
    doctor_p.add_argument(
        "--wolfram-smoke",
        action="store_true",
        help="start Wolfram briefly to test command-line activation",
    )

    client_p = sub.add_parser("client", help="print client config snippets")
    client_p.add_argument("client", choices=CLIENTS)
    client_p.add_argument("--url")
    client_p.add_argument("--name")
    client_p.add_argument("--mcp-proxy-version", default="0.12.0")

    reset_p = sub.add_parser("reset", help='run ClearAll["Global`*"]')
    reset_p.add_argument("--url")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    config = load_config()

    if args.command == "serve":
        return serve(config)
    if args.command == "install":
        install(args.platform, dry_run=args.dry_run)
        return 0
    if args.command == "uninstall":
        uninstall(args.platform, dry_run=args.dry_run)
        return 0
    if args.command == "restart":
        restart(args.platform, dry_run=args.dry_run)
        return 0
    if args.command == "status":
        status = check_endpoint(args.url or config.url)
        print(status.as_json() if args.json else status.detail)
        return 0 if status.ok else 1
    if args.command == "doctor":
        return doctor(smoke=args.wolfram_smoke)
    if args.command == "client":
        print(
            render_client(
                args.client,
                args.url or config.url,
                args.name,
                args.mcp_proxy_version,
            ),
            end="",
        )
        return 0
    if args.command == "reset":
        return reset(args.url or config.url)

    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
