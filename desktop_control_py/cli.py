"""提供 desktop-control-py 的公开命令行入口。"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from .checks import run_environment_check
from .config import load_settings
from .server import create_server
from .smoke import run_smoke_test


def _build_parser() -> argparse.ArgumentParser:
    """构造 CLI 解析器，并保留无参数即 serve 的旧行为。"""

    parser = argparse.ArgumentParser(
        prog="desktop-control-py",
        description="Windows-only desktop control MCP command line interface.",
    )
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the MCP server.")
    serve_parser.add_argument("--transport", choices=["stdio"], default="stdio", help="MCP transport to use.")
    serve_parser.add_argument("--config", type=Path, default=None, help="Optional TOML config override.")

    check_parser = subparsers.add_parser("check-env", help="Validate the active Python environment.")
    check_parser.add_argument("--config", type=Path, default=None, help="Optional TOML config override.")

    smoke_parser = subparsers.add_parser("smoke-test", help="Run the real-machine desktop smoke test.")
    smoke_parser.add_argument("--config", type=Path, default=None, help="Optional TOML config override.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """解析命令行参数，并分发到 serve、check-env 或 smoke-test。"""

    parser = _build_parser()
    normalized_argv = list(argv) if argv is not None else None
    if normalized_argv == []:
        normalized_argv = ["serve"]

    args = parser.parse_args(normalized_argv)
    command = args.command or "serve"

    if command == "check-env":
        return run_environment_check(config_path=args.config)

    if command == "smoke-test":
        return run_smoke_test(config_path=args.config)

    settings = load_settings(config_path=args.config)
    server = create_server(settings=settings)
    server.run(transport=args.transport)
    return 0
