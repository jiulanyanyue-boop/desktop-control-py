from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_batch_launchers_do_not_pin_personal_machine_paths() -> None:
    """验证公开启动器不再硬编码个人机器 Python、uv 或 Codex cache 路径。"""

    forbidden_fragments = [
        "".join(["D:", "\\", "Develop", "\\", "python_3.11.9"]),
        "".join(["C:", "\\", "Users", "\\", "13", "056", "\\", ".co", "dex"]),
        "UV_PROJECT_" + "ENVIRONMENT=",
        "UV_" + "CACHE_DIR=",
    ]

    for launcher_name in ["启动桌面控制MCP.bat", "检查桌面控制环境.bat", "运行桌面控制冒烟测试.bat"]:
        content = (PROJECT_ROOT / launcher_name).read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in content


def test_batch_launchers_expose_override_and_path_fallbacks() -> None:
    """验证公开启动器提供 env override、uv fallback 和 python fallback。"""

    for launcher_name in ["启动桌面控制MCP.bat", "检查桌面控制环境.bat", "运行桌面控制冒烟测试.bat"]:
        content = (PROJECT_ROOT / launcher_name).read_text(encoding="utf-8")

        assert "DESKTOP_CONTROL_PY_PYTHON" in content
        assert "DESKTOP_CONTROL_PY_UV" in content
        assert "where uv" in content
        assert "where python" in content
