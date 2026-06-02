"""按责任域注册 MCP 工具。"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from mcp.server.fastmcp import FastMCP

from .browser_flow import DEFAULT_BROWSER_TITLE_HINT
from .service import DesktopService

ToolDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]


class BaseToolRegistrar:
    """提供结构化工具装饰器的注册器基类。"""

    def __init__(self, server: FastMCP, service: DesktopService) -> None:
        """绑定 FastMCP server 和服务门面。"""

        self._server = server
        self._service = service

    def _structured_tool(self) -> ToolDecorator:
        """返回启用 structured_output 的 FastMCP tool 装饰器。"""

        return self._server.tool(structured_output=True)


class AtomicToolRegistrar(BaseToolRegistrar):
    """注册桌面原子能力工具。"""

    def register(self) -> None:
        """注册屏幕、鼠标、键盘、窗口和剪贴板工具。"""

        structured_tool = self._structured_tool
        service = self._service

        @structured_tool()
        def screen_capture(
            region: dict[str, int] | None = None,
            format: str | None = None,
            quality: int | None = None,
            grayscale: bool | None = None,
        ) -> dict[str, Any]:
            """Capture the current screen and return base64 image content plus metadata."""

            return service.screen_capture(
                region=region,
                format=format,
                quality=quality,
                grayscale=grayscale,
            ).model_dump()

        @structured_tool()
        def screen_size() -> dict[str, Any]:
            """Return the current screen size."""

            return service.screen_size().model_dump()

        @structured_tool()
        def cursor_position() -> dict[str, Any]:
            """Return the current mouse cursor position."""

            return service.cursor_position().model_dump()

        @structured_tool()
        def mouse_move(x: int, y: int) -> dict[str, Any]:
            """Move the mouse pointer to the specified coordinates."""

            return service.mouse_move(x=x, y=y).model_dump()

        @structured_tool()
        def mouse_click(button: str = "left") -> dict[str, Any]:
            """Click the mouse at the current cursor position."""

            return service.mouse_click(button=button).model_dump()

        @structured_tool()
        def mouse_double_click(button: str = "left") -> dict[str, Any]:
            """Double click the mouse at the current cursor position."""

            return service.mouse_double_click(button=button).model_dump()

        @structured_tool()
        def mouse_drag(from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict[str, Any]:
            """Drag the mouse from one coordinate to another."""

            return service.mouse_drag(from_x=from_x, from_y=from_y, to_x=to_x, to_y=to_y, button=button).model_dump()

        @structured_tool()
        def mouse_scroll(amount: int) -> dict[str, Any]:
            """Scroll the mouse wheel by the specified amount."""

            return service.mouse_scroll(amount=amount).model_dump()

        @structured_tool()
        def keyboard_type(text: str) -> dict[str, Any]:
            """Type text into the active window."""

            return service.keyboard_type(text=text).model_dump()

        @structured_tool()
        def keyboard_press(key: str) -> dict[str, Any]:
            """Press a single keyboard key."""

            return service.keyboard_press(key=key).model_dump()

        @structured_tool()
        def keyboard_hold(key: str, state: str, duration_ms: int | None = None) -> dict[str, Any]:
            """Hold or release a key, optionally for a fixed duration."""

            return service.keyboard_hold(key=key, state=state, duration_ms=duration_ms).model_dump()

        @structured_tool()
        def keyboard_hotkey(keys: list[str]) -> dict[str, Any]:
            """Press a keyboard hotkey combination."""

            return service.keyboard_hotkey(keys=keys).model_dump()

        @structured_tool()
        def window_list(title: str | None = None, exact: bool = False, visible_only: bool = True) -> dict[str, Any]:
            """List top-level windows, optionally filtered by title."""

            return service.window_list(title=title, exact=exact, visible_only=visible_only).model_dump()

        @structured_tool()
        def window_active() -> dict[str, Any]:
            """Return metadata for the active window."""

            return service.window_active().model_dump()

        @structured_tool()
        def window_focus(title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
            """Focus the target window."""

            return service.window_focus(title=title, exact=exact, timeout_ms=timeout_ms).model_dump()

        @structured_tool()
        def window_move(title: str, x: int, y: int, exact: bool = False) -> dict[str, Any]:
            """Move the target window."""

            return service.window_move(title=title, x=x, y=y, exact=exact).model_dump()

        @structured_tool()
        def window_resize(title: str, width: int, height: int, exact: bool = False) -> dict[str, Any]:
            """Resize the target window."""

            return service.window_resize(title=title, width=width, height=height, exact=exact).model_dump()

        @structured_tool()
        def clipboard_get() -> dict[str, Any]:
            """Read text from the clipboard."""

            return service.clipboard_get().model_dump()

        @structured_tool()
        def clipboard_set(text: str) -> dict[str, Any]:
            """Write text to the clipboard."""

            return service.clipboard_set(text=text).model_dump()

        @structured_tool()
        def clipboard_clear() -> dict[str, Any]:
            """Clear text from the clipboard."""

            return service.clipboard_clear().model_dump()

        @structured_tool()
        def clipboard_has_text() -> dict[str, Any]:
            """Return whether the clipboard currently contains text."""

            return service.clipboard_has_text().model_dump()


class ActionToolRegistrar(BaseToolRegistrar):
    """注册 high-level action_* 工具。"""

    def register(self) -> None:
        """注册可选窗口聚焦后的复合动作工具。"""

        structured_tool = self._structured_tool
        service = self._service

        @structured_tool()
        def action_focus_window(title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
            """High-level focus action for a target window."""

            return service.action_focus_window(title=title, exact=exact, timeout_ms=timeout_ms).model_dump()

        @structured_tool()
        def action_wait_window(title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
            """High-level wait action that resolves once a window becomes visible."""

            return service.action_wait_window(title=title, exact=exact, timeout_ms=timeout_ms).model_dump()

        @structured_tool()
        def action_click(
            x: int,
            y: int,
            button: str = "left",
            pre_focus_title: str | None = None,
        ) -> dict[str, Any]:
            """Optionally focus a window, then move and click."""

            return service.action_click(x=x, y=y, button=button, pre_focus_title=pre_focus_title).model_dump()

        @structured_tool()
        def action_double_click(
            x: int,
            y: int,
            button: str = "left",
            pre_focus_title: str | None = None,
        ) -> dict[str, Any]:
            """Optionally focus a window, then move and double click."""

            return service.action_double_click(x=x, y=y, button=button, pre_focus_title=pre_focus_title).model_dump()

        @structured_tool()
        def action_type(text: str, pre_focus_title: str | None = None) -> dict[str, Any]:
            """Optionally focus a window, then type text."""

            return service.action_type(text=text, pre_focus_title=pre_focus_title).model_dump()

        @structured_tool()
        def action_hotkey(keys: list[str], pre_focus_title: str | None = None) -> dict[str, Any]:
            """Optionally focus a window, then press a hotkey."""

            return service.action_hotkey(keys=keys, pre_focus_title=pre_focus_title).model_dump()

        @structured_tool()
        def action_capture_screen(
            pre_focus_title: str | None = None,
            region: dict[str, int] | None = None,
            format: str | None = None,
            quality: int | None = None,
            grayscale: bool | None = None,
        ) -> dict[str, Any]:
            """Optionally focus a window, then capture the screen."""

            return service.action_capture_screen(
                pre_focus_title=pre_focus_title,
                region=region,
                format=format,
                quality=quality,
                grayscale=grayscale,
            ).model_dump()


class BrowserToolRegistrar(BaseToolRegistrar):
    """注册 screenshot-first 浏览器工具。"""

    def register(self) -> None:
        """注册 browser_capture 和 browser_click。"""

        structured_tool = self._structured_tool
        service = self._service

        @structured_tool()
        def browser_capture(
            title_hint: str = DEFAULT_BROWSER_TITLE_HINT,
            include_cursor: bool = True,
        ) -> dict[str, Any]:
            """Focus a real browser window and capture its screenshot without text or clipboard access."""

            return service.browser_capture(title_hint=title_hint, include_cursor=include_cursor).model_dump()

        @structured_tool()
        def browser_click(
            x: int,
            y: int,
            title_hint: str = DEFAULT_BROWSER_TITLE_HINT,
            button: str = "left",
            after_screenshot: bool = True,
        ) -> dict[str, Any]:
            """Focus a real browser, screenshot before clicking coordinates, then optionally screenshot after."""

            return service.browser_click(
                x=x,
                y=y,
                title_hint=title_hint,
                button=button,
                after_screenshot=after_screenshot,
            ).model_dump()
