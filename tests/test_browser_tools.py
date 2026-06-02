from __future__ import annotations

from pathlib import Path


class FakeDesktopBackend:
    """用于浏览器截图坐标流测试的 Win32 后端替身。"""

    def __init__(self) -> None:
        self.actions: list[tuple] = []
        self.active_title = "Example Dashboard - Google Chrome"
        self.windows = [
            {
                "title": "Example Dashboard - Google Chrome",
                "handle": 100,
                "class_name": "Chrome_WidgetWin_1",
                "process_name": "chrome.exe",
                "rect": {"left": 10, "top": 20, "right": 1210, "bottom": 920, "width": 1200, "height": 900},
            },
            {
                "title": "Codex",
                "handle": 200,
                "class_name": "ApplicationFrameWindow",
                "process_name": "Codex.exe",
                "rect": {"left": 0, "top": 0, "right": 1200, "bottom": 900, "width": 1200, "height": 900},
            },
        ]

    def list_windows(self, title: str | None = None, exact: bool = False, visible_only: bool = True) -> list[dict]:
        if not title:
            return self.windows
        if exact:
            return [item for item in self.windows if item["title"] == title]
        return [item for item in self.windows if title.lower() in item["title"].lower()]

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict:
        matches = self.list_windows(title, exact=exact)
        if not matches:
            raise RuntimeError("window not found")
        window = matches[0]
        self.active_title = window["title"]
        self.actions.append(("focus", window["title"]))
        return window

    def capture_screen(self, **kwargs: object) -> dict:
        self.actions.append(("capture", kwargs.get("region")))
        return {"mime_type": "image/png", "width": 12, "height": 8, "base64_data": "ZmFrZQ=="}

    def get_cursor_position(self) -> dict:
        return {"x": 11, "y": 22}

    def move_mouse(self, x: int, y: int) -> dict:
        self.actions.append(("move", x, y))
        return {"x": x, "y": y}

    def click_mouse(self, button: str = "left") -> dict:
        self.actions.append(("click", button))
        return {"button": button}

    def hotkey(self, keys: list[str]) -> dict:
        raise AssertionError(f"browser flow must not call hotkey: {keys}")

    def get_clipboard(self) -> dict:
        raise AssertionError("browser flow must not read clipboard")

    def set_clipboard(self, text: str) -> dict:
        raise AssertionError("browser flow must not write clipboard")


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


def test_browser_capture_only_focuses_and_screenshots(tmp_path: Path) -> None:
    from desktop_control_py.service import DesktopService

    backend = FakeDesktopBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.browser_capture()

    assert result.ok is True
    assert result.data["window"]["title"] == "Example Dashboard - Google Chrome"
    assert result.data["screenshot"]["width"] == 12
    assert result.data["cursor"] == {"x": 11, "y": 22}
    assert result.data["selection_used"] is False
    assert backend.actions == [
        ("focus", "Example Dashboard - Google Chrome"),
        ("capture", {"left": 10, "top": 20, "width": 1200, "height": 900}),
    ]


def test_browser_click_takes_screenshot_before_click(tmp_path: Path) -> None:
    from desktop_control_py.service import DesktopService

    backend = FakeDesktopBackend()
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.browser_click(x=300, y=420, button="left")

    assert result.ok is True
    assert result.data["before_screenshot"]["width"] == 12
    assert result.data["after_screenshot"]["width"] == 12
    assert result.data["selection_used"] is False
    assert backend.actions == [
        ("focus", "Example Dashboard - Google Chrome"),
        ("capture", {"left": 10, "top": 20, "width": 1200, "height": 900}),
        ("move", 300, 420),
        ("click", "left"),
        ("capture", {"left": 10, "top": 20, "width": 1200, "height": 900}),
    ]


def test_browser_window_matching_ignores_electron_chrome_widget(tmp_path: Path) -> None:
    from desktop_control_py.service import DesktopService

    backend = FakeDesktopBackend()
    backend.windows = [
        {
            "title": "SPlayer - 桌面歌词",
            "handle": 300,
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "SPlayer.exe",
            "rect": {"left": 0, "top": 0, "right": 900, "bottom": 700, "width": 900, "height": 700},
        },
        {
            "title": "Example Dashboard - Google Chrome",
            "handle": 100,
            "class_name": "Chrome_WidgetWin_1",
            "process_name": "chrome.exe",
            "rect": {"left": 10, "top": 20, "right": 1210, "bottom": 920, "width": 1200, "height": 900},
        },
    ]
    service = DesktopService(settings=_settings(tmp_path), backend=backend)

    result = service.browser_capture()

    assert result.ok is True
    assert result.data["window"]["process_name"] == "chrome.exe"
    assert backend.actions[0] == ("focus", "Example Dashboard - Google Chrome")


def test_server_registers_browser_screenshot_tools_without_semantic_tools(tmp_path: Path) -> None:
    import asyncio

    from desktop_control_py.server import create_server

    server = create_server(settings=_settings(tmp_path), backend=FakeDesktopBackend())
    tools = asyncio.run(server.list_tools())
    tool_names = {tool.name for tool in tools}

    assert {"browser_capture", "browser_click"}.issubset(tool_names)
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
