"""聚合安全策略、动作引擎与桌面后端，向 MCP 层暴露统一能力。"""

from __future__ import annotations

from .action_flow import ActionFlow
from .backends.protocol import DesktopBackend
from .browser_flow import DEFAULT_BROWSER_TITLE_HINT, BrowserFlow
from .engine import ActionEngine
from .errors import DesktopControlError
from .logging_utils import AuditLogReader
from .models import ActionResult, AppSettings
from .safety import SafetyPolicy, normalize_hotkey


class DesktopService:
    """以同步方式封装桌面原子工具，并委托复合 action/browser 工作流。"""

    def __init__(
        self,
        settings: AppSettings,
        backend: DesktopBackend,
        engine: ActionEngine | None = None,
    ) -> None:
        """绑定配置、后端、动作引擎、安全策略和复合工作流。"""

        self._settings = settings
        self._backend = backend
        self._engine = engine or ActionEngine(settings)
        self._safety = SafetyPolicy(settings)
        self._actions = ActionFlow(
            settings=settings,
            backend=backend,
            engine=self._engine,
            safety=self._safety,
            window_controller=self,
        )
        self._browser = BrowserFlow(settings=settings, backend=backend, engine=self._engine)

    def screen_capture(
        self,
        region: dict[str, int] | None = None,
        format: str | None = None,
        quality: int | None = None,
        grayscale: bool | None = None,
    ) -> ActionResult:
        """执行截图原子动作，并返回 base64 与元数据。"""

        options = {
            "region": region,
            "format": format or self._settings.screenshot.default_format,
            "quality": quality or self._settings.screenshot.default_quality,
            "grayscale": self._settings.screenshot.grayscale if grayscale is None else grayscale,
        }
        return self._engine.execute(
            "screen_capture",
            action=lambda: self._backend.capture_screen(**options),
            retryable=True,
            metadata={"options": options},
        )

    def screen_size(self) -> ActionResult:
        """返回当前主屏幕尺寸。"""

        return self._engine.execute("screen_size", action=self._backend.get_screen_size, retryable=True)

    def cursor_position(self) -> ActionResult:
        """返回当前鼠标坐标。"""

        return self._engine.execute("cursor_position", action=self._backend.get_cursor_position, retryable=True)

    def mouse_move(self, x: int, y: int) -> ActionResult:
        """移动鼠标到指定屏幕坐标。"""

        return self._engine.execute(
            "mouse_move",
            action=lambda: self._backend.move_mouse(x, y),
            retryable=False,
            metadata={"x": x, "y": y},
        )

    def mouse_click(self, button: str = "left") -> ActionResult:
        """在当前鼠标位置执行一次点击。"""

        return self._engine.execute(
            "mouse_click",
            action=lambda: self._backend.click_mouse(button=button),
            retryable=False,
            metadata={"button": button},
        )

    def mouse_double_click(self, button: str = "left") -> ActionResult:
        """在当前鼠标位置执行一次双击。"""

        return self._engine.execute(
            "mouse_double_click",
            action=lambda: self._backend.double_click_mouse(button=button),
            retryable=False,
            metadata={"button": button},
        )

    def mouse_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> ActionResult:
        """执行鼠标拖拽动作。"""

        return self._engine.execute(
            "mouse_drag",
            action=lambda: self._backend.drag_mouse(from_x, from_y, to_x, to_y, button=button),
            retryable=False,
            metadata={"from_x": from_x, "from_y": from_y, "to_x": to_x, "to_y": to_y, "button": button},
        )

    def mouse_scroll(self, amount: int) -> ActionResult:
        """滚动鼠标滚轮。"""

        return self._engine.execute(
            "mouse_scroll",
            action=lambda: self._backend.scroll_mouse(amount),
            retryable=False,
            metadata={"amount": amount},
        )

    def keyboard_type(self, text: str) -> ActionResult:
        """向当前焦点窗口输入一段文本。"""

        return self._engine.execute(
            "keyboard_type",
            action=lambda: self._backend.type_text(text),
            retryable=False,
            metadata={"length": len(text)},
        )

    def keyboard_press(self, key: str) -> ActionResult:
        """按下一次单个按键。"""

        return self._engine.execute(
            "keyboard_press",
            action=lambda: self._backend.press_key(key),
            retryable=False,
            metadata={"key": key},
        )

    def keyboard_hold(self, key: str, state: str, duration_ms: int | None = None) -> ActionResult:
        """执行按键按下或释放动作。"""

        return self._engine.execute(
            "keyboard_hold",
            action=lambda: self._backend.hold_key(key, state, duration_ms=duration_ms),
            retryable=False,
            metadata={"key": key, "state": state, "duration_ms": duration_ms},
        )

    def keyboard_hotkey(self, keys: list[str]) -> ActionResult:
        """执行组合键，同时经过系统热键软保护。"""

        decision = self._safety.evaluate_hotkey(keys)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_hotkey",
                message=decision.message or "Hotkey blocked",
                details={"keys": keys},
            )
        return self._engine.execute(
            "keyboard_hotkey",
            action=lambda: self._backend.hotkey(keys),
            retryable=False,
            metadata={"keys": keys},
        )

    def window_list(self, title: str | None = None, exact: bool = False, visible_only: bool = True) -> ActionResult:
        """列出可见或指定标题的顶层窗口。"""

        return self._engine.execute(
            "window_list",
            action=lambda: self._backend.list_windows(title=title, exact=exact, visible_only=visible_only),
            retryable=True,
            metadata={"title": title, "exact": exact, "visible_only": visible_only},
        )

    def window_active(self) -> ActionResult:
        """读取当前活动窗口信息。"""

        return self._engine.execute("window_active", action=self._backend.get_active_window, retryable=True)

    def window_focus(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """聚焦目标窗口，并检查危险窗口软保护。"""

        decision = self._safety.evaluate_window_operation("window_focus", title)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_window_operation",
                message=decision.message or "Window operation blocked",
                details={"title": title},
            )
        return self._engine.execute(
            "window_focus",
            action=lambda: self._backend.focus_window(title, exact=exact, timeout_ms=timeout_ms),
            retryable=True,
            metadata={"title": title, "exact": exact, "timeout_ms": timeout_ms},
        )

    def window_move(self, title: str, x: int, y: int, exact: bool = False) -> ActionResult:
        """移动目标窗口位置。"""

        decision = self._safety.evaluate_window_operation("window_move", title)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_window_operation",
                message=decision.message or "Window operation blocked",
                details={"title": title},
            )
        return self._engine.execute(
            "window_move",
            action=lambda: self._backend.move_window(title, x, y, exact=exact),
            retryable=False,
            metadata={"title": title, "x": x, "y": y, "exact": exact},
        )

    def window_resize(self, title: str, width: int, height: int, exact: bool = False) -> ActionResult:
        """调整目标窗口尺寸。"""

        decision = self._safety.evaluate_window_operation("window_resize", title)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_window_operation",
                message=decision.message or "Window operation blocked",
                details={"title": title},
            )
        return self._engine.execute(
            "window_resize",
            action=lambda: self._backend.resize_window(title, width, height, exact=exact),
            retryable=False,
            metadata={"title": title, "width": width, "height": height, "exact": exact},
        )

    def clipboard_get(self) -> ActionResult:
        """读取文本剪贴板内容。"""

        return self._engine.execute("clipboard_get", action=self._backend.get_clipboard, retryable=True)

    def clipboard_set(self, text: str) -> ActionResult:
        """设置文本剪贴板内容。"""

        return self._engine.execute(
            "clipboard_set",
            action=lambda: self._backend.set_clipboard(text),
            retryable=False,
            metadata={"length": len(text)},
        )

    def clipboard_clear(self) -> ActionResult:
        """清空文本剪贴板。"""

        return self._engine.execute("clipboard_clear", action=self._backend.clear_clipboard, retryable=False)

    def clipboard_has_text(self) -> ActionResult:
        """判断剪贴板当前是否含有文本。"""

        return self._engine.execute("clipboard_has_text", action=self._backend.clipboard_has_text, retryable=True)

    def desktop_snapshot(
        self,
        include_windows: bool = True,
        max_windows: int = 20,
        visible_only: bool = True,
        include_clipboard_state: bool = True,
        include_screenshot: bool = False,
    ) -> ActionResult:
        """一次性读取当前桌面上下文，供 agent 在行动前观察环境。"""

        window_limit = max(0, min(max_windows, 100))

        def observe_desktop() -> dict:
            """组合只读后端调用，生成不会触发输入副作用的桌面快照。"""

            snapshot = {
                "screen": self._backend.get_screen_size(),
                "cursor": self._backend.get_cursor_position(),
                "active_window": self._backend.get_active_window(),
            }

            if include_windows:
                windows = self._backend.list_windows(visible_only=visible_only)
                snapshot["windows"] = windows[:window_limit]
                snapshot["window_count"] = len(windows)

            if include_clipboard_state:
                snapshot["clipboard"] = self._backend.clipboard_has_text()

            if include_screenshot:
                snapshot["screenshot"] = self._backend.capture_screen()

            return snapshot

        return self._engine.execute(
            "desktop_snapshot",
            action=observe_desktop,
            retryable=True,
            metadata={
                "include_windows": include_windows,
                "max_windows": window_limit,
                "visible_only": visible_only,
                "include_clipboard_state": include_clipboard_state,
                "include_screenshot": include_screenshot,
            },
        )

    def safety_check(
        self,
        kind: str,
        keys: list[str] | None = None,
        operation: str | None = None,
        title: str | None = None,
    ) -> ActionResult:
        """在真实输入前执行无副作用安全预检。"""

        normalized_kind = kind.strip().lower()

        def check_policy() -> dict:
            """根据预检类型调用对应安全策略，不访问桌面后端。"""

            if normalized_kind == "hotkey":
                if not keys:
                    raise DesktopControlError(
                        code="missing_safety_check_keys",
                        message="Safety check kind 'hotkey' requires keys.",
                    )
                decision = self._safety.evaluate_hotkey(keys)
                return {
                    "kind": normalized_kind,
                    "allowed": decision.allowed,
                    "reason_code": decision.reason_code,
                    "message": decision.message,
                    "normalized_hotkey": normalize_hotkey(keys),
                    "policy_scope": "system_hotkey",
                }

            if normalized_kind == "window_operation":
                operation_name = operation or "window_operation"
                decision = self._safety.evaluate_window_operation(operation_name, title)
                return {
                    "kind": normalized_kind,
                    "allowed": decision.allowed,
                    "reason_code": decision.reason_code,
                    "message": decision.message,
                    "operation": operation_name,
                    "title": title,
                    "policy_scope": "dangerous_window",
                }

            raise DesktopControlError(
                code="invalid_safety_check_kind",
                message=f"Unsupported safety check kind: {kind}",
                details={"kind": kind},
            )

        return self._engine.execute(
            "safety_check",
            action=check_policy,
            retryable=False,
            metadata={"kind": normalized_kind, "keys": keys, "operation": operation, "title": title},
        )

    def audit_recent(
        self,
        limit: int = 20,
        action_name: str | None = None,
        ok: bool | None = None,
    ) -> ActionResult:
        """读取最近结构化审计记录，帮助用户检查 MCP 动作历史。"""

        normalized_limit = max(0, min(limit, 100))

        def read_audit() -> dict:
            """从 session JSONL 中读取最近动作，不访问桌面后端。"""

            read_result = AuditLogReader(self._settings.logging.session_file).read_recent(
                limit=normalized_limit,
                action_name=action_name,
                ok=ok,
            )
            return {
                "records": read_result.records,
                "read_warnings": read_result.warnings,
                "limit": normalized_limit,
                "action_name": action_name,
                "ok": ok,
            }

        return self._engine.execute(
            "audit_recent",
            action=read_audit,
            retryable=False,
            metadata={"limit": normalized_limit, "action_name": action_name, "ok": ok},
        )

    def action_focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """委托 ActionFlow 聚焦目标窗口。"""

        return self._actions.focus_window(title=title, exact=exact, timeout_ms=timeout_ms)

    def action_wait_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """委托 ActionFlow 等待目标窗口出现。"""

        return self._actions.wait_window(title=title, exact=exact, timeout_ms=timeout_ms)

    def action_click(self, x: int, y: int, button: str = "left", pre_focus_title: str | None = None) -> ActionResult:
        """委托 ActionFlow 执行可选聚焦后的点击。"""

        return self._actions.click(x=x, y=y, button=button, pre_focus_title=pre_focus_title)

    def action_double_click(
        self,
        x: int,
        y: int,
        button: str = "left",
        pre_focus_title: str | None = None,
    ) -> ActionResult:
        """委托 ActionFlow 执行可选聚焦后的双击。"""

        return self._actions.double_click(x=x, y=y, button=button, pre_focus_title=pre_focus_title)

    def action_type(self, text: str, pre_focus_title: str | None = None) -> ActionResult:
        """委托 ActionFlow 执行可选聚焦后的文本输入。"""

        return self._actions.type_text(text=text, pre_focus_title=pre_focus_title)

    def action_hotkey(self, keys: list[str], pre_focus_title: str | None = None) -> ActionResult:
        """委托 ActionFlow 执行可选聚焦后的热键。"""

        return self._actions.hotkey(keys=keys, pre_focus_title=pre_focus_title)

    def action_capture_screen(
        self,
        pre_focus_title: str | None = None,
        region: dict[str, int] | None = None,
        format: str | None = None,
        quality: int | None = None,
        grayscale: bool | None = None,
    ) -> ActionResult:
        """委托 ActionFlow 执行可选聚焦后的截图。"""

        return self._actions.capture_screen(
            pre_focus_title=pre_focus_title,
            region=region,
            format=format,
            quality=quality,
            grayscale=grayscale,
        )

    def browser_capture(
        self,
        title_hint: str = DEFAULT_BROWSER_TITLE_HINT,
        include_cursor: bool = True,
    ) -> ActionResult:
        """委托 BrowserFlow 执行浏览器截图。"""

        return self._browser.capture(title_hint=title_hint, include_cursor=include_cursor)

    def browser_click(
        self,
        x: int,
        y: int,
        title_hint: str = DEFAULT_BROWSER_TITLE_HINT,
        button: str = "left",
        after_screenshot: bool = True,
    ) -> ActionResult:
        """委托 BrowserFlow 执行浏览器截图坐标点击。"""

        return self._browser.click(
            x=x,
            y=y,
            title_hint=title_hint,
            button=button,
            after_screenshot=after_screenshot,
        )
