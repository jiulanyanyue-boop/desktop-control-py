from __future__ import annotations

import asyncio
from pathlib import Path


class FakeDesktopBackend:
    """用于 MCP 服务单元测试的简化桌面后端。"""

    def get_screen_size(self) -> dict:
        return {"width": 1920, "height": 1080}

    def get_cursor_position(self) -> dict:
        return {"x": 10, "y": 20}

    def get_active_window(self) -> dict:
        return {"title": "Notepad", "handle": 1}

    def list_windows(self, title: str | None = None, exact: bool = False, visible_only: bool = True) -> list[dict]:
        return [{"title": "Notepad", "handle": 1}]

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict:
        return {"title": title, "handle": 1}

    def move_window(self, title: str, x: int, y: int, exact: bool = False) -> dict:
        return {"title": title, "x": x, "y": y}

    def resize_window(self, title: str, width: int, height: int, exact: bool = False) -> dict:
        return {"title": title, "width": width, "height": height}

    def move_mouse(self, x: int, y: int) -> dict:
        return {"x": x, "y": y}

    def click_mouse(self, button: str = "left") -> dict:
        return {"button": button}

    def double_click_mouse(self, button: str = "left") -> dict:
        return {"button": button}

    def drag_mouse(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict:
        return {"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y, "button": button}

    def scroll_mouse(self, amount: int) -> dict:
        return {"amount": amount}

    def type_text(self, text: str) -> dict:
        return {"text": text}

    def press_key(self, key: str) -> dict:
        return {"key": key}

    def hold_key(self, key: str, state: str, duration_ms: int | None = None) -> dict:
        return {"key": key, "state": state, "duration_ms": duration_ms}

    def hotkey(self, keys: list[str]) -> dict:
        return {"keys": keys}

    def get_clipboard(self) -> dict:
        return {"text": "clipboard"}

    def set_clipboard(self, text: str) -> dict:
        return {"text": text}

    def clear_clipboard(self) -> dict:
        return {"cleared": True}

    def clipboard_has_text(self) -> dict:
        return {"has_text": True}

    def capture_screen(self, **_: object) -> dict:
        return {
            "mime_type": "image/png",
            "width": 10,
            "height": 10,
            "base64_data": "ZmFrZQ==",
        }


def _settings(tmp_path: Path):
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


def test_server_registers_required_tool_names(tmp_path: Path) -> None:
    from desktop_control_py.server import create_server

    server = create_server(settings=_settings(tmp_path), backend=FakeDesktopBackend())

    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert {
        "screen_capture",
        "mouse_move",
        "keyboard_hotkey",
        "window_focus",
        "clipboard_get",
        "action_type",
        "action_capture_screen",
        "browser_capture",
        "browser_click",
    }.issubset(tool_names)

    assert {
        "desktop_observe",
        "element_find",
        "element_describe",
        "human_click",
        "human_type",
        "human_scroll",
        "human_hotkey",
        "browser_focus",
        "browser_copy_page_text",
        "boss_recover_login",
        "boss_capture_visible_job",
    }.isdisjoint(tool_names)


def test_server_screen_size_tool_returns_standard_envelope(tmp_path: Path) -> None:
    from desktop_control_py.server import create_server

    server = create_server(settings=_settings(tmp_path), backend=FakeDesktopBackend())

    result = asyncio.run(server.call_tool("screen_size", {}))

    assert result["ok"] is True
    assert result["data"] == {"width": 1920, "height": 1080}
    assert "duration_ms" in result
    assert result["warnings"] == []
