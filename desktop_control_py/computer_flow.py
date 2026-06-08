"""封装 Computer Use 风格的观察和 observe-act-observe 桌面动作流。"""

from __future__ import annotations

from typing import Any

from .artifacts import ScreenshotArtifactStore
from .backends.protocol import DesktopBackend
from .engine import ActionEngine
from .errors import DesktopControlError
from .models import ActionResult, AppSettings
from .safety import SafetyPolicy


class ComputerFlow:
    """承载通用桌面 Computer Use 风格观察和闭环动作。"""

    def __init__(
        self,
        settings: AppSettings,
        backend: DesktopBackend,
        engine: ActionEngine,
        safety: SafetyPolicy,
    ) -> None:
        """绑定观察、动作、安全策略和截图 artifact 依赖。"""

        self._settings = settings
        self._backend = backend
        self._engine = engine
        self._safety = safety
        self._artifact_store = ScreenshotArtifactStore(settings.runtime_dir / "screenshots")

    def observe(
        self,
        include_windows: bool = True,
        max_windows: int = 20,
        visible_only: bool = True,
        include_clipboard_state: bool = True,
        include_screenshot: bool = True,
        save_screenshot: bool = True,
        return_screenshot_data: bool = True,
    ) -> ActionResult:
        """执行只读桌面观察，并可保存可引用截图 artifact。"""

        window_limit = max(0, min(max_windows, 100))

        def observe_action() -> dict:
            """组合桌面上下文、坐标契约和可选截图 artifact。"""

            return self._observe_context(
                include_windows=include_windows,
                max_windows=window_limit,
                visible_only=visible_only,
                include_clipboard_state=include_clipboard_state,
                include_screenshot=include_screenshot,
                save_screenshot=save_screenshot,
                return_screenshot_data=return_screenshot_data,
                artifact_label="observe",
            )

        return self._engine.execute(
            "computer_observe",
            action=observe_action,
            retryable=True,
            metadata={
                "include_windows": include_windows,
                "max_windows": window_limit,
                "visible_only": visible_only,
                "include_clipboard_state": include_clipboard_state,
                "include_screenshot": include_screenshot,
                "save_screenshot": save_screenshot,
                "return_screenshot_data": return_screenshot_data,
            },
        )

    def step(
        self,
        action: str,
        x: int | None = None,
        y: int | None = None,
        button: str = "left",
        text: str | None = None,
        keys: list[str] | None = None,
        pre_focus_title: str | None = None,
        observe_before: bool = True,
        observe_after: bool = True,
        include_windows: bool = True,
        max_windows: int = 20,
        visible_only: bool = True,
        include_clipboard_state: bool = True,
        include_screenshot: bool = True,
        save_screenshot: bool = True,
        return_screenshot_data: bool = True,
    ) -> ActionResult:
        """执行带前后观察的通用桌面动作。"""

        normalized_action = action.strip().lower()
        window_limit = max(0, min(max_windows, 100))

        def step_action() -> dict:
            """按配置执行前观察、动作和后观察，并返回单个审计结果。"""

            payload: dict[str, Any] = {"strategy_used": "observe_act_observe"}
            if observe_before:
                payload["before_observation"] = self._observe_context(
                    include_windows=include_windows,
                    max_windows=window_limit,
                    visible_only=visible_only,
                    include_clipboard_state=include_clipboard_state,
                    include_screenshot=include_screenshot,
                    save_screenshot=save_screenshot,
                    return_screenshot_data=return_screenshot_data,
                    artifact_label=f"{normalized_action}-before",
                )

            payload["action"] = self._execute_action(
                action=normalized_action,
                x=x,
                y=y,
                button=button,
                text=text,
                keys=keys,
                pre_focus_title=pre_focus_title,
            )

            if observe_after:
                payload["after_observation"] = self._observe_context(
                    include_windows=include_windows,
                    max_windows=window_limit,
                    visible_only=visible_only,
                    include_clipboard_state=include_clipboard_state,
                    include_screenshot=include_screenshot,
                    save_screenshot=save_screenshot,
                    return_screenshot_data=return_screenshot_data,
                    artifact_label=f"{normalized_action}-after",
                )

            return payload

        return self._engine.execute(
            "computer_step",
            action=step_action,
            retryable=False,
            metadata={
                "action": normalized_action,
                "x": x,
                "y": y,
                "button": button,
                "text_length": len(text) if text is not None else None,
                "keys": keys,
                "pre_focus_title": pre_focus_title,
                "observe_before": observe_before,
                "observe_after": observe_after,
                "include_screenshot": include_screenshot,
                "save_screenshot": save_screenshot,
                "return_screenshot_data": return_screenshot_data,
            },
        )

    def _observe_context(
        self,
        include_windows: bool,
        max_windows: int,
        visible_only: bool,
        include_clipboard_state: bool,
        include_screenshot: bool,
        save_screenshot: bool,
        return_screenshot_data: bool,
        artifact_label: str,
    ) -> dict[str, Any]:
        """构造观察结果，包含坐标契约、屏幕指标和可选截图 artifact。"""

        screen = self._backend.get_screen_size()
        observation: dict[str, Any] = {
            "strategy_used": "observe_only",
            "screen": screen,
            "cursor": self._backend.get_cursor_position(),
            "active_window": self._backend.get_active_window(),
            "screen_metrics": self._read_screen_metrics(screen),
            "coordinate_space": self._coordinate_space(),
        }

        if include_windows:
            windows = self._backend.list_windows(visible_only=visible_only)
            observation["windows"] = windows[:max_windows]
            observation["window_count"] = len(windows)

        if include_clipboard_state:
            observation["clipboard"] = self._backend.clipboard_has_text()

        if include_screenshot and (save_screenshot or return_screenshot_data):
            screenshot = self._backend.capture_screen()
            if save_screenshot:
                observation["screenshot_artifact"] = self._artifact_store.save(
                    screenshot=screenshot,
                    label=artifact_label,
                ).to_dict()
            if return_screenshot_data:
                observation["screenshot"] = screenshot

        return observation

    def _read_screen_metrics(self, screen: dict[str, Any]) -> dict[str, Any]:
        """读取后端屏幕指标；旧后端缺少能力时生成保守回退值。"""

        metrics_reader = getattr(self._backend, "get_screen_metrics", None)
        if callable(metrics_reader):
            return metrics_reader()

        width = int(screen.get("width") or 0)
        height = int(screen.get("height") or 0)
        return {
            "primary_screen": {"width": width, "height": height},
            "virtual_screen": {"left": 0, "top": 0, "width": width, "height": height},
            "monitors": [{"index": 1, "left": 0, "top": 0, "width": width, "height": height, "primary": True}],
            "dpi": {"system": 96, "scale": 1.0},
        }

    @staticmethod
    def _coordinate_space() -> dict[str, str]:
        """返回本项目所有坐标动作使用的公开坐标契约。"""

        return {
            "type": "screen_pixels",
            "origin": "virtual_screen_top_left",
            "units": "px",
            "click_coordinates": "absolute_screen_xy",
        }

    def _execute_action(
        self,
        action: str,
        x: int | None,
        y: int | None,
        button: str,
        text: str | None,
        keys: list[str] | None,
        pre_focus_title: str | None,
    ) -> dict[str, Any]:
        """执行 Computer step 支持的真实输入动作，并返回脱敏动作结果。"""

        focused_window = self._focus_before_action(pre_focus_title)

        if action == "click":
            return self._click_action(action=action, x=x, y=y, button=button, focused_window=focused_window)

        if action == "double_click":
            return self._double_click_action(action=action, x=x, y=y, button=button, focused_window=focused_window)

        if action == "type":
            return self._type_action(action=action, text=text, focused_window=focused_window)

        if action == "hotkey":
            return self._hotkey_action(action=action, keys=keys, focused_window=focused_window)

        raise DesktopControlError(
            code="invalid_computer_step_action",
            message=f"Unsupported computer step action: {action}",
            details={"action": action},
        )

    def _click_action(
        self,
        action: str,
        x: int | None,
        y: int | None,
        button: str,
        focused_window: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """执行单击动作并返回坐标参数。"""

        self._require_coordinates(action, x, y)
        self._backend.move_mouse(x, y)
        result = self._backend.click_mouse(button=button)
        return {
            "kind": action,
            "parameters": {"x": x, "y": y, "button": button, "pre_focus_title": self._focused_title(focused_window)},
            "result": result,
            **({"focused_window": focused_window} if focused_window else {}),
        }

    def _double_click_action(
        self,
        action: str,
        x: int | None,
        y: int | None,
        button: str,
        focused_window: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """执行双击动作并返回坐标参数。"""

        self._require_coordinates(action, x, y)
        self._backend.move_mouse(x, y)
        result = self._backend.double_click_mouse(button=button)
        return {
            "kind": action,
            "parameters": {"x": x, "y": y, "button": button, "pre_focus_title": self._focused_title(focused_window)},
            "result": result,
            **({"focused_window": focused_window} if focused_window else {}),
        }

    def _type_action(
        self,
        action: str,
        text: str | None,
        focused_window: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """执行文本输入动作，并避免在结果中回显文本。"""

        if text is None:
            raise DesktopControlError(
                code="missing_computer_step_text",
                message="Computer step action 'type' requires text.",
            )

        self._backend.type_text(text)
        return {
            "kind": action,
            "parameters": {"text_length": len(text), "pre_focus_title": self._focused_title(focused_window)},
            "result": {"typed_length": len(text)},
            **({"focused_window": focused_window} if focused_window else {}),
        }

    def _hotkey_action(
        self,
        action: str,
        keys: list[str] | None,
        focused_window: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """执行热键动作，并复用系统热键安全策略。"""

        if not keys:
            raise DesktopControlError(
                code="missing_computer_step_keys",
                message="Computer step action 'hotkey' requires keys.",
            )

        decision = self._safety.evaluate_hotkey(keys)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_hotkey",
                message=decision.message or "Hotkey blocked",
                details={"keys": keys},
            )

        result = self._backend.hotkey(keys)
        return {
            "kind": action,
            "parameters": {"keys": keys, "pre_focus_title": self._focused_title(focused_window)},
            "result": result,
            **({"focused_window": focused_window} if focused_window else {}),
        }

    def _focus_before_action(self, title: str | None) -> dict[str, Any] | None:
        """按需聚焦目标窗口，并复用危险窗口安全策略。"""

        if not title:
            return None

        decision = self._safety.evaluate_window_operation("computer_step_focus", title)
        if not decision.allowed:
            raise DesktopControlError(
                code=decision.reason_code or "blocked_window_operation",
                message=decision.message or "Window operation blocked",
                details={"title": title},
            )
        return self._backend.focus_window(
            title,
            exact=False,
            timeout_ms=self._settings.timing.window_find_timeout_ms,
        )

    @staticmethod
    def _focused_title(focused_window: dict[str, Any] | None) -> str | None:
        """从已聚焦窗口中提取标题，用于脱敏参数回显。"""

        if not focused_window:
            return None
        title = focused_window.get("title")
        return str(title) if title is not None else None

    @staticmethod
    def _require_coordinates(action: str, x: int | None, y: int | None) -> None:
        """校验坐标动作必须同时提供 x 和 y。"""

        if x is None or y is None:
            raise DesktopControlError(
                code="missing_computer_step_coordinates",
                message=f"Computer step action '{action}' requires x and y.",
                details={"action": action, "x": x, "y": y},
            )
