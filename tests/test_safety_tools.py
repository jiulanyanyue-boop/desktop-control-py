from __future__ import annotations

from pathlib import Path

import pytest


class NoBackendCalls:
    """任何访问都失败的后端替身，用于证明安全预检不触碰桌面后端。"""

    def __getattr__(self, name: str) -> object:
        """拦截所有后端能力访问。"""

        raise AssertionError(f"safety_check must not call backend method: {name}")


def _settings(tmp_path: Path):
    """构造带系统热键 allowlist 和危险窗口标题的测试配置。"""

    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[safety]",
                "block_system_hotkeys = true",
                "block_dangerous_window_ops = true",
                'dangerous_window_titles = ["Task Manager", "Registry Editor"]',
                'allowed_system_hotkeys = ["ctrl+shift+esc"]',
                "",
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/app.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def test_safety_check_blocks_risky_hotkey_without_backend_calls(tmp_path: Path) -> None:
    """验证安全预检能拦截默认禁止的系统热键，且不会调用后端。"""

    from desktop_control_py.service import DesktopService

    service = DesktopService(settings=_settings(tmp_path), backend=NoBackendCalls())

    result = service.safety_check(kind="hotkey", keys=["alt", "f4"])

    assert result.ok is True
    assert result.data == {
        "kind": "hotkey",
        "allowed": False,
        "reason_code": "blocked_system_hotkey",
        "message": "Hotkey 'alt+f4' is blocked by safety policy.",
        "normalized_hotkey": "alt+f4",
        "policy_scope": "system_hotkey",
    }


def test_safety_check_allows_allowlisted_hotkey(tmp_path: Path) -> None:
    """验证 allowlist 中的系统热键能通过安全预检。"""

    from desktop_control_py.service import DesktopService

    service = DesktopService(settings=_settings(tmp_path), backend=NoBackendCalls())

    result = service.safety_check(kind="hotkey", keys=["shift", "ctrl", "esc"])

    assert result.ok is True
    assert result.data["allowed"] is True
    assert result.data["reason_code"] is None
    assert result.data["normalized_hotkey"] == "ctrl+esc+shift"


def test_safety_check_blocks_dangerous_window_operation(tmp_path: Path) -> None:
    """验证危险窗口标题上的窗口操作会被预检拦截。"""

    from desktop_control_py.service import DesktopService

    service = DesktopService(settings=_settings(tmp_path), backend=NoBackendCalls())

    result = service.safety_check(kind="window_operation", operation="window_focus", title="Task Manager")

    assert result.ok is True
    assert result.data["allowed"] is False
    assert result.data["reason_code"] == "blocked_dangerous_window"
    assert result.data["policy_scope"] == "dangerous_window"


def test_safety_check_rejects_invalid_kind(tmp_path: Path) -> None:
    """验证未知预检类型会返回稳定领域错误。"""

    from desktop_control_py.errors import DesktopControlError
    from desktop_control_py.service import DesktopService

    service = DesktopService(settings=_settings(tmp_path), backend=NoBackendCalls())

    with pytest.raises(DesktopControlError) as exc_info:
        service.safety_check(kind="clipboard")

    assert exc_info.value.code == "invalid_safety_check_kind"
