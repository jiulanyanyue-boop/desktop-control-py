from __future__ import annotations

from pathlib import Path
from typing import Any


class ComputerStepFakeBackend:
    """用于验证 Computer Use 风格闭环工具的后端替身。"""

    def __init__(self) -> None:
        """初始化动作记录和固定桌面状态。"""

        self.calls: list[tuple[Any, ...]] = []

    def get_screen_size(self) -> dict[str, int]:
        """返回固定主屏尺寸。"""

        self.calls.append(("screen_size",))
        return {"width": 1920, "height": 1080}

    def get_cursor_position(self) -> dict[str, int]:
        """返回固定鼠标位置。"""

        self.calls.append(("cursor",))
        return {"x": 10, "y": 20}

    def get_active_window(self) -> dict[str, Any]:
        """返回固定活动窗口。"""

        self.calls.append(("active_window",))
        return {"title": "Editor", "handle": 1, "process_name": "code.exe"}

    def get_screen_metrics(self) -> dict[str, Any]:
        """返回固定虚拟屏指标。"""

        self.calls.append(("screen_metrics",))
        return {
            "primary_screen": {"width": 1920, "height": 1080},
            "virtual_screen": {"left": 0, "top": 0, "width": 1920, "height": 1080},
            "monitors": [{"index": 1, "left": 0, "top": 0, "width": 1920, "height": 1080, "primary": True}],
            "dpi": {"system": 96, "scale": 1.0},
        }

    def list_windows(
        self,
        title: str | None = None,
        exact: bool = False,
        visible_only: bool = True,
    ) -> list[dict[str, Any]]:
        """返回固定窗口列表。"""

        self.calls.append(("windows", visible_only))
        return [{"title": "Editor", "handle": 1, "process_name": "code.exe"}]

    def clipboard_has_text(self) -> dict[str, bool]:
        """返回剪贴板是否含文本，不读取文本内容。"""

        self.calls.append(("clipboard_state",))
        return {"has_text": False}

    def capture_screen(
        self,
        region: dict[str, int] | None = None,
        format: str = "png",
        quality: int = 90,
        grayscale: bool = False,
    ) -> dict[str, Any]:
        """返回固定截图载荷。"""

        self.calls.append(("capture", region, format, quality, grayscale))
        return {"mime_type": "image/png", "width": 12, "height": 9, "base64_data": "ZmFrZQ=="}

    def move_mouse(self, x: int, y: int) -> dict[str, int]:
        """记录鼠标移动。"""

        self.calls.append(("move", x, y))
        return {"x": x, "y": y}

    def click_mouse(self, button: str = "left") -> dict[str, str]:
        """记录鼠标点击。"""

        self.calls.append(("click", button))
        return {"button": button}

    def double_click_mouse(self, button: str = "left") -> dict[str, str]:
        """记录鼠标双击。"""

        self.calls.append(("double_click", button))
        return {"button": button}

    def type_text(self, text: str) -> dict[str, int]:
        """记录文本输入，并只返回长度以避免回显敏感文本。"""

        self.calls.append(("type", text))
        return {"typed_length": len(text)}

    def hotkey(self, keys: list[str]) -> dict[str, list[str]]:
        """记录组合键。"""

        self.calls.append(("hotkey", tuple(keys)))
        return {"keys": keys}

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
        """记录窗口聚焦。"""

        self.calls.append(("focus", title, exact, timeout_ms))
        return {"title": title, "handle": 1, "process_name": "code.exe"}


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


def test_computer_step_click_wraps_action_with_before_and_after_observations(tmp_path: Path) -> None:
    """验证点击动作会被前后观察包裹，形成可审计的 observe-act-observe 闭环。"""

    from desktop_control_py.service import DesktopService

    backend = ComputerStepFakeBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.computer_step(
        action="click",
        x=300,
        y=420,
        button="left",
        return_screenshot_data=False,
    )

    before_artifact = Path(result.data["before_observation"]["screenshot_artifact"]["path"])
    after_artifact = Path(result.data["after_observation"]["screenshot_artifact"]["path"])

    assert result.ok is True
    assert result.data["strategy_used"] == "observe_act_observe"
    assert result.data["action"] == {
        "kind": "click",
        "parameters": {"x": 300, "y": 420, "button": "left", "pre_focus_title": None},
        "result": {"button": "left"},
    }
    assert result.data["before_observation"]["coordinate_space"]["click_coordinates"] == "absolute_screen_xy"
    assert result.data["after_observation"]["coordinate_space"]["click_coordinates"] == "absolute_screen_xy"
    assert before_artifact.exists()
    assert after_artifact.exists()
    assert backend.calls == [
        ("screen_size",),
        ("cursor",),
        ("active_window",),
        ("screen_metrics",),
        ("windows", True),
        ("clipboard_state",),
        ("capture", None, "png", 90, False),
        ("move", 300, 420),
        ("click", "left"),
        ("screen_size",),
        ("cursor",),
        ("active_window",),
        ("screen_metrics",),
        ("windows", True),
        ("clipboard_state",),
        ("capture", None, "png", 90, False),
    ]


def test_computer_step_type_does_not_echo_typed_text_in_result(tmp_path: Path) -> None:
    """验证文本输入闭环只暴露长度，不在结果中回显可能敏感的输入文本。"""

    from desktop_control_py.service import DesktopService

    backend = ComputerStepFakeBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.computer_step(
        action="type",
        text="secret-token",
        observe_before=False,
        observe_after=False,
    )

    assert result.ok is True
    assert result.data["action"] == {
        "kind": "type",
        "parameters": {"text_length": 12, "pre_focus_title": None},
        "result": {"typed_length": 12},
    }
    assert "before_observation" not in result.data
    assert "after_observation" not in result.data
    assert backend.calls == [("type", "secret-token")]
