"""兼容旧脚本入口：检查本地 Python MCP 运行环境。"""

from __future__ import annotations

from pathlib import Path
import sys

from desktop_control_py.checks import run_environment_check


def main() -> int:
    """转发到可安装包内的环境检查实现。"""

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    return run_environment_check(config_path=config_path)


if __name__ == "__main__":
    raise SystemExit(main())
