"""提供可安装包内的环境检查流程。"""

from __future__ import annotations

import platform
import sys
from importlib import import_module
from pathlib import Path

from .config import load_settings

REQUIRED_MODULES = [
    "mcp",
    "mss",
    "PIL",
    "pydantic",
    "win32api",
    "win32clipboard",
]


def run_environment_check(config_path: Path | None = None) -> int:
    """检查当前 Python 环境、配置加载和核心依赖是否可用。"""

    print("desktop-control-py environment check")
    print(f"python: {sys.executable}")
    print(f"version: {sys.version.split()[0]}")
    print(f"platform: {platform.platform()}")

    try:
        settings = load_settings(config_path=config_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] config could not be loaded: {exc}")
        print("Next setup command: uv sync --extra dev")
        return 1

    print(f"project: {settings.project_root}")
    print(f"config: {settings.config_path}")
    print(f"runtime: {settings.runtime_dir}")

    failures: list[str] = []
    for module_name in REQUIRED_MODULES:
        try:
            import_module(module_name)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{module_name}: {exc}")
        else:
            print(f"[OK] {module_name}")

    if failures:
        print("[FAIL] missing or broken modules:")
        for item in failures:
            print(f"  - {item}")
        print("Next setup command: uv sync --extra dev")
        return 1

    print("[PASS] environment looks ready")
    return 0
