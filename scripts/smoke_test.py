"""兼容旧脚本入口：执行真实 Windows 桌面冒烟验证。"""

from __future__ import annotations

from pathlib import Path
import sys

from desktop_control_py.smoke import run_smoke_test


def main() -> int:
    """转发到可安装包内的 smoke-test 实现。"""

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    return run_smoke_test(config_path=config_path)


if __name__ == "__main__":
    raise SystemExit(main())
