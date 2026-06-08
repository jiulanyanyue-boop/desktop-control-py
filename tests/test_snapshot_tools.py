from __future__ import annotations

from pathlib import Path
from typing import Any


class SnapshotFakeBackend:
    """用于验证桌面快照只读行为的后端替身。"""

    def __init__(self) -> None:
        """初始化可观测的调用记录和桌面状态。"""

        self.calls: list[str] = []
        self.windows = [
            {"title": "Editor", "handle": 1, "process_name": "code.exe"},
            {"title": "Browser", "handle": 2, "process_name": "chrome.exe"},
            {"title": "Terminal", "handle": 3, "process_name": "pwsh.exe"},
        ]

    def get_screen_size(self) -> dict[str, int]:
        """返回固定屏幕尺寸。"""

        self.calls.append("get_screen_size")
        return {"width": 1920, "height": 1080}

    def get_cursor_position(self) -> dict[str, int]:
        """返回固定鼠标坐标。"""

        self.calls.append("get_cursor_position")
        return {"x": 100, "y": 200}

    def get_active_window(self) -> dict[str, Any]:
        """返回固定活动窗口。"""

        self.calls.append("get_active_window")
        return {"title": "Editor", "handle": 1, "process_name": "code.exe"}

    def list_windows(
        self,
        title: str | None = None,
        exact: bool = False,
        visible_only: bool = True,
    ) -> list[dict[str, Any]]:
        """返回可见窗口列表并记录 visible_only 参数。"""

        self.calls.append(f"list_windows:{visible_only}")
        return self.windows

    def clipboard_has_text(self) -> dict[str, bool]:
        """只返回剪贴板是否含文本，不读取剪贴板文本。"""

        self.calls.append("clipboard_has_text")
        return {"has_text": True}

    def capture_screen(
        self,
        region: dict[str, int] | None = None,
        format: str = "png",
        quality: int = 90,
        grayscale: bool = False,
    ) -> dict[str, Any]:
        """返回固定截图载荷。"""

        self.calls.append("capture_screen")
        return {"mime_type": "image/png", "width": 10, "height": 8, "base64_data": "ZmFrZQ=="}

    def get_screen_metrics(self) -> dict[str, Any]:
        """返回固定屏幕指标，覆盖 Computer Use 风格坐标契约。"""

        self.calls.append("get_screen_metrics")
        return {
            "primary_screen": {"width": 1920, "height": 1080},
            "virtual_screen": {"left": 0, "top": 0, "width": 1920, "height": 1080},
            "monitors": [{"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080, "primary": True}],
            "dpi": {"system": 96, "scale": 1.0},
        }

    def move_mouse(self, x: int, y: int) -> dict[str, int]:
        """禁止桌面快照移动鼠标。"""

        raise AssertionError("desktop_snapshot must not move the mouse")

    def click_mouse(self, button: str = "left") -> dict[str, str]:
        """禁止桌面快照点击鼠标。"""

        raise AssertionError("desktop_snapshot must not click the mouse")

    def type_text(self, text: str) -> dict[str, str]:
        """禁止桌面快照输入文本。"""

        raise AssertionError("desktop_snapshot must not type text")

    def get_clipboard(self) -> dict[str, str]:
        """禁止桌面快照读取剪贴板文本。"""

        raise AssertionError("desktop_snapshot must not read clipboard text")


def _settings(tmp_path: Path):
    """构造使用临时 runtime 的测试配置。"""

    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/app.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def test_desktop_snapshot_observes_context_without_input_side_effects(tmp_path: Path) -> None:
    """验证默认桌面快照只读取上下文，不截图也不执行输入动作。"""

    from desktop_control_py.service import DesktopService

    backend = SnapshotFakeBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.desktop_snapshot(max_windows=2)

    assert result.ok is True
    assert result.data == {
        "screen": {"width": 1920, "height": 1080},
        "cursor": {"x": 100, "y": 200},
        "active_window": {"title": "Editor", "handle": 1, "process_name": "code.exe"},
        "windows": [
            {"title": "Editor", "handle": 1, "process_name": "code.exe"},
            {"title": "Browser", "handle": 2, "process_name": "chrome.exe"},
        ],
        "window_count": 3,
        "clipboard": {"has_text": True},
    }
    assert backend.calls == [
        "get_screen_size",
        "get_cursor_position",
        "get_active_window",
        "list_windows:True",
        "clipboard_has_text",
    ]


def test_desktop_snapshot_can_include_screenshot_when_explicit(tmp_path: Path) -> None:
    """验证显式请求时桌面快照才会携带截图载荷。"""

    from desktop_control_py.service import DesktopService

    backend = SnapshotFakeBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.desktop_snapshot(include_windows=False, include_clipboard_state=False, include_screenshot=True)

    assert result.ok is True
    assert result.data["screenshot"] == {
        "mime_type": "image/png",
        "width": 10,
        "height": 8,
        "base64_data": "ZmFrZQ==",
    }
    assert "windows" not in result.data
    assert "clipboard" not in result.data
    assert backend.calls == [
        "get_screen_size",
        "get_cursor_position",
        "get_active_window",
        "capture_screen",
    ]


def test_computer_observe_saves_screenshot_artifact_with_coordinate_contract(tmp_path: Path) -> None:
    """验证 Computer Use 风格观察会保存截图文件，并返回稳定坐标说明。"""

    from desktop_control_py.service import DesktopService

    backend = SnapshotFakeBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.computer_observe(max_windows=1, return_screenshot_data=False)

    artifact = result.data["screenshot_artifact"]
    artifact_path = Path(artifact["path"])

    assert result.ok is True
    assert result.data["strategy_used"] == "observe_only"
    assert result.data["coordinate_space"] == {
        "type": "screen_pixels",
        "origin": "virtual_screen_top_left",
        "units": "px",
        "click_coordinates": "absolute_screen_xy",
    }
    assert result.data["screen_metrics"]["virtual_screen"]["width"] == 1920
    assert result.data["window_count"] == 3
    assert len(result.data["windows"]) == 1
    assert "screenshot" not in result.data
    assert artifact["mime_type"] == "image/png"
    assert artifact["width"] == 10
    assert artifact["height"] == 8
    assert artifact_path.exists()
    assert artifact_path.read_bytes() == b"fake"
    assert backend.calls == [
        "get_screen_size",
        "get_cursor_position",
        "get_active_window",
        "get_screen_metrics",
        "list_windows:True",
        "clipboard_has_text",
        "capture_screen",
    ]
