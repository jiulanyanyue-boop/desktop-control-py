"""封装 high-level action_* 工作流。"""

from __future__ import annotations

import math
from typing import Any, Protocol

from .backends.protocol import DesktopBackend
from .engine import ActionEngine
from .errors import DesktopControlError
from .models import ActionResult, AppSettings
from .safety import SafetyPolicy


class WindowFocusController(Protocol):
    """描述 action 工作流需要调用的窗口聚焦能力。"""

    def window_focus(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """聚焦目标窗口，并返回统一动作结果。"""


class ActionFlow:
    """承载高阶 action_* 工具的编排逻辑。"""

    def __init__(
        self,
        settings: AppSettings,
        backend: DesktopBackend,
        engine: ActionEngine,
        safety: SafetyPolicy,
        window_controller: WindowFocusController,
    ) -> None:
        """绑定动作流依赖，避免服务层继续承载复合动作细节。"""

        self._settings = settings
        self._backend = backend
        self._engine = engine
        self._safety = safety
        self._window_controller = window_controller

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """提供聚焦窗口的高阶包装，便于上层统一作为 action 前缀使用。"""

        return self._window_controller.window_focus(title=title, exact=exact, timeout_ms=timeout_ms)

    def wait_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> ActionResult:
        """等待窗口出现，本质上是可重试的窗口查找逻辑。"""

        timeout = timeout_ms or self._settings.timing.window_find_timeout_ms

        def wait_action() -> dict[str, Any]:
            """读取窗口列表并返回第一个匹配项。"""

            windows = self._backend.list_windows(title=title, exact=exact, visible_only=True)
            if not windows:
                raise RuntimeError(f"Window '{title}' not found yet.")
            return windows[0]

        original_attempts = self._settings.timing.safe_retry_attempts
        original_interval = self._settings.timing.safe_retry_interval_ms
        computed_attempts = max(1, math.ceil(timeout / max(original_interval or 1, 1)))
        self._settings.timing.safe_retry_attempts = computed_attempts
        try:
            return self._engine.execute(
                "action_wait_window",
                action=wait_action,
                retryable=True,
                metadata={"title": title, "exact": exact, "timeout_ms": timeout},
            )
        finally:
            self._settings.timing.safe_retry_attempts = original_attempts
            self._settings.timing.safe_retry_interval_ms = original_interval

    def click(self, x: int, y: int, button: str = "left", pre_focus_title: str | None = None) -> ActionResult:
        """先可选聚焦窗口，再移动并点击目标坐标。"""

        def action() -> dict[str, Any]:
            """执行聚焦、移动和点击。"""

            if pre_focus_title:
                self._window_controller.window_focus(pre_focus_title)
            self._backend.move_mouse(x, y)
            return self._backend.click_mouse(button=button)

        return self._engine.execute(
            "action_click",
            action=action,
            retryable=False,
            metadata={"x": x, "y": y, "button": button, "pre_focus_title": pre_focus_title},
        )

    def double_click(self, x: int, y: int, button: str = "left", pre_focus_title: str | None = None) -> ActionResult:
        """先可选聚焦窗口，再移动并双击目标坐标。"""

        def action() -> dict[str, Any]:
            """执行聚焦、移动和双击。"""

            if pre_focus_title:
                self._window_controller.window_focus(pre_focus_title)
            self._backend.move_mouse(x, y)
            return self._backend.double_click_mouse(button=button)

        return self._engine.execute(
            "action_double_click",
            action=action,
            retryable=False,
            metadata={"x": x, "y": y, "button": button, "pre_focus_title": pre_focus_title},
        )

    def type_text(self, text: str, pre_focus_title: str | None = None) -> ActionResult:
        """先可选聚焦窗口，再输入文本。"""

        def action() -> dict[str, Any]:
            """执行聚焦和文本输入。"""

            if pre_focus_title:
                self._window_controller.window_focus(pre_focus_title)
            return self._backend.type_text(text)

        return self._engine.execute(
            "action_type",
            action=action,
            retryable=False,
            metadata={"length": len(text), "pre_focus_title": pre_focus_title},
        )

    def hotkey(self, keys: list[str], pre_focus_title: str | None = None) -> ActionResult:
        """先可选聚焦窗口，再执行热键。"""

        def action() -> dict[str, Any]:
            """执行聚焦、安全检查和热键。"""

            if pre_focus_title:
                self._window_controller.window_focus(pre_focus_title)
            decision = self._safety.evaluate_hotkey(keys)
            if not decision.allowed:
                raise DesktopControlError(
                    code=decision.reason_code or "blocked_hotkey",
                    message=decision.message or "Hotkey blocked",
                    details={"keys": keys},
                )
            return self._backend.hotkey(keys)

        return self._engine.execute(
            "action_hotkey",
            action=action,
            retryable=False,
            metadata={"keys": keys, "pre_focus_title": pre_focus_title},
        )

    def capture_screen(
        self,
        pre_focus_title: str | None = None,
        region: dict[str, int] | None = None,
        format: str | None = None,
        quality: int | None = None,
        grayscale: bool | None = None,
    ) -> ActionResult:
        """先可选聚焦窗口，再执行截图。"""

        def action() -> dict[str, Any]:
            """执行聚焦和截图。"""

            if pre_focus_title:
                self._window_controller.window_focus(pre_focus_title)
            return self._backend.capture_screen(
                region=region,
                format=format or self._settings.screenshot.default_format,
                quality=quality or self._settings.screenshot.default_quality,
                grayscale=self._settings.screenshot.grayscale if grayscale is None else grayscale,
            )

        return self._engine.execute(
            "action_capture_screen",
            action=action,
            retryable=True,
            metadata={"pre_focus_title": pre_focus_title, "region": region},
        )
