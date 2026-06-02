"""封装 screenshot-first 浏览器坐标流。"""

from __future__ import annotations

from typing import Any

from .backends.protocol import DesktopBackend
from .engine import ActionEngine
from .errors import DesktopControlError
from .models import ActionResult, AppSettings

DEFAULT_BROWSER_TITLE_HINT = "Chrome|Edge|Browser"
"""公开浏览器默认匹配提示，保持通用浏览器叙事。"""


class BrowserFlow:
    """承载浏览器截图和坐标点击的安全工作流。"""

    def __init__(self, settings: AppSettings, backend: DesktopBackend, engine: ActionEngine) -> None:
        """绑定浏览器流依赖；本类不读取 DOM、UIA、页面文本或剪贴板。"""

        self._settings = settings
        self._backend = backend
        self._engine = engine

    def capture(self, title_hint: str = DEFAULT_BROWSER_TITLE_HINT, include_cursor: bool = True) -> ActionResult:
        """聚焦真实浏览器并截图；不读取页面文本、不触碰剪贴板、不点击。"""

        def action() -> dict[str, Any]:
            """执行浏览器聚焦和窗口截图。"""

            window = self._focus_browser_window(title_hint)
            capture = self._capture_browser_window(window=window, include_cursor=include_cursor)
            capture["selection_used"] = False
            return capture

        return self._engine.execute(
            "browser_capture",
            action=action,
            retryable=True,
            metadata={"title_hint": title_hint, "include_cursor": include_cursor},
        )

    def click(
        self,
        x: int,
        y: int,
        title_hint: str = DEFAULT_BROWSER_TITLE_HINT,
        button: str = "left",
        after_screenshot: bool = True,
    ) -> ActionResult:
        """浏览器坐标点击：点击前必须截图，点击后默认再截图。"""

        def action() -> dict[str, Any]:
            """执行截图、坐标点击和可选点击后截图。"""

            window = self._focus_browser_window(title_hint)
            before = self._capture_browser_window(window=window, include_cursor=True)
            self._backend.move_mouse(x, y)
            click_result = self._backend.click_mouse(button=button)
            after = self._capture_browser_window(window=window, include_cursor=True) if after_screenshot else None
            return {
                "window": window,
                "click": {"x": x, "y": y, "button": button, "result": click_result},
                "coordinate_space": before["coordinate_space"],
                "before_screenshot": before["screenshot"],
                "after_screenshot": after["screenshot"] if after else None,
                "selection_used": False,
                "strategy_used": "screenshot_coordinate_click",
            }

        return self._engine.execute(
            "browser_click",
            action=action,
            retryable=False,
            metadata={"title_hint": title_hint, "x": x, "y": y, "button": button},
        )

    def _focus_browser_window(self, title_hint: str) -> dict[str, Any]:
        """按标题提示找到真实浏览器窗口并聚焦，避免仅凭 Chrome_WidgetWin_1 误判 Electron。"""

        window = self._find_browser_window(title_hint)
        try:
            focused = self._backend.focus_window(
                window["title"],
                exact=True,
                timeout_ms=self._settings.timing.window_find_timeout_ms,
            )
        except Exception as exc:  # noqa: BLE001
            raise DesktopControlError(
                code="browser_focus_failed",
                message=f"Could not focus browser window '{window.get('title', '')}'.",
                details={"title_hint": title_hint, "window": window, "error": str(exc)},
            ) from exc
        return {**window, **focused, "rect": focused.get("rect") or window.get("rect")}

    def _capture_browser_window(self, window: dict[str, Any], include_cursor: bool) -> dict[str, Any]:
        """截取浏览器窗口区域，并声明截图与点击都使用屏幕像素坐标系。"""

        region = self._window_region(window)
        screenshot = self._backend.capture_screen(
            region=region,
            format=self._settings.screenshot.default_format,
            quality=self._settings.screenshot.default_quality,
            grayscale=self._settings.screenshot.grayscale,
        )
        return {
            "window": window,
            "screenshot": screenshot,
            "coordinate_space": {
                "type": "screen_pixels",
                "origin": "virtual_screen_top_left",
                "units": "px",
                "screenshot_region": region,
                "click_coordinates": "absolute_screen_xy",
            },
            "cursor": self._backend.get_cursor_position() if include_cursor else None,
        }

    def _find_browser_window(self, title_hint: str) -> dict[str, Any]:
        """按标题或真实进程名匹配浏览器；class_name 只参与加分，不作为准入条件。"""

        tokens = [item.strip().lower() for item in title_hint.split("|") if item.strip()]
        browser_processes = {"chrome.exe", "msedge.exe", "firefox.exe", "brave.exe", "opera.exe"}
        browser_title_markers = {
            "chrome",
            "google chrome",
            "edge",
            "microsoft edge",
            "browser",
            "firefox",
            "brave",
            "opera",
        }
        windows = self._backend.list_windows(title=None, exact=False, visible_only=True)
        candidates: list[tuple[int, dict[str, Any]]] = []
        for window in windows:
            title = (window.get("title") or "").lower()
            class_name = (window.get("class_name") or "").lower()
            process_name = (window.get("process_name") or "").lower()
            token_title_match = not tokens or any(token in title for token in tokens)
            token_process_match = any(token in process_name for token in tokens)
            process_browser = process_name in browser_processes
            title_browser = any(marker in title for marker in browser_title_markers)
            if not (token_title_match or token_process_match):
                continue
            if not (process_browser or title_browser):
                continue
            score = 0
            if process_browser:
                score += 50
            if title_browser:
                score += 10
            if "chrome_widgetwin" in class_name or "mozillawindowclass" in class_name:
                score += 1
            candidates.append((score, window))
        if candidates:
            return sorted(candidates, key=lambda item: item[0], reverse=True)[0][1]
        raise DesktopControlError(
            code="browser_window_not_found",
            message=f"No browser window matched '{title_hint}'.",
            details={"title_hint": title_hint, "window_count": len(windows)},
        )

    @staticmethod
    def _window_region(window: dict[str, Any]) -> dict[str, int] | None:
        """把窗口矩形转换成 mss 截图区域；缺失或无效时回退全屏截图。"""

        rect = window.get("rect") or {}
        width = int(rect.get("width") or 0)
        height = int(rect.get("height") or 0)
        if width <= 0 or height <= 0:
            return None
        return {
            "left": int(rect.get("left", 0)),
            "top": int(rect.get("top", 0)),
            "width": width,
            "height": height,
        }
