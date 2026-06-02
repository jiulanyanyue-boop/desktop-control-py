from __future__ import annotations


def test_default_browser_title_hint_is_generic() -> None:
    """验证公开默认浏览器匹配提示不再包含特定站点场景词。"""

    from desktop_control_py.browser_flow import DEFAULT_BROWSER_TITLE_HINT

    assert DEFAULT_BROWSER_TITLE_HINT == "Chrome|Edge|Browser"
    assert "".join(["B", "OSS"]) not in DEFAULT_BROWSER_TITLE_HINT.upper()


def test_desktop_backend_protocol_accepts_fake_backend() -> None:
    """验证服务层依赖的是显式 typed backend protocol。"""

    from desktop_control_py.backends.protocol import DesktopBackend

    class FakeBackend:
        """实现 DesktopBackend 所需属性的假后端。"""

        def get_screen_size(self) -> dict:
            """返回屏幕尺寸。"""

            return {}

        def get_cursor_position(self) -> dict:
            """返回鼠标坐标。"""

            return {}

        def move_mouse(self, x: int, y: int) -> dict:
            """移动鼠标。"""

            return {}

        def click_mouse(self, button: str = "left") -> dict:
            """点击鼠标。"""

            return {}

        def double_click_mouse(self, button: str = "left") -> dict:
            """双击鼠标。"""

            return {}

        def drag_mouse(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict:
            """拖拽鼠标。"""

            return {}

        def scroll_mouse(self, amount: int) -> dict:
            """滚动鼠标。"""

            return {}

        def type_text(self, text: str) -> dict:
            """输入文本。"""

            return {}

        def press_key(self, key: str) -> dict:
            """按键。"""

            return {}

        def hold_key(self, key: str, state: str, duration_ms: int | None = None) -> dict:
            """按住或释放按键。"""

            return {}

        def hotkey(self, keys: list[str]) -> dict:
            """执行热键。"""

            return {}

        def list_windows(self, title: str | None = None, exact: bool = False, visible_only: bool = True) -> list[dict]:
            """列出窗口。"""

            return []

        def get_active_window(self) -> dict:
            """返回活动窗口。"""

            return {}

        def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict:
            """聚焦窗口。"""

            return {}

        def move_window(self, title: str, x: int, y: int, exact: bool = False) -> dict:
            """移动窗口。"""

            return {}

        def resize_window(self, title: str, width: int, height: int, exact: bool = False) -> dict:
            """调整窗口。"""

            return {}

        def get_clipboard(self) -> dict:
            """读取剪贴板。"""

            return {}

        def set_clipboard(self, text: str) -> dict:
            """写入剪贴板。"""

            return {}

        def clear_clipboard(self) -> dict:
            """清空剪贴板。"""

            return {}

        def clipboard_has_text(self) -> dict:
            """判断剪贴板文本。"""

            return {}

        def capture_screen(
            self,
            region: dict[str, int] | None = None,
            format: str = "png",
            quality: int = 90,
            grayscale: bool = False,
        ) -> dict:
            """截取屏幕。"""

            return {}

    assert isinstance(FakeBackend(), DesktopBackend)
