"""实现系统级快捷键和危险窗口操作的软保护策略。"""

from __future__ import annotations

from .models import AppSettings, SafetyDecision


def normalize_hotkey(keys: list[str]) -> str:
    """把热键列表规范化为稳定的比较字符串。"""

    return "+".join(sorted(key.strip().lower() for key in keys if key.strip()))


class SafetyPolicy:
    """根据配置决定当前动作是否应该被放行。"""

    SYSTEM_KEYS = {"win", "lwin", "rwin"}

    def __init__(self, settings: AppSettings):
        """保存当前运行配置，供后续风险判断使用。"""

        self._settings = settings
        self._allowlisted_hotkeys = {
            normalize_hotkey(item.split("+")) for item in settings.safety.allowed_system_hotkeys
        }
        self._dangerous_titles = [item.lower() for item in settings.safety.dangerous_window_titles]

    def evaluate_hotkey(self, keys: list[str]) -> SafetyDecision:
        """判断一个组合键是否命中系统级快捷键保护规则。"""

        normalized = normalize_hotkey(keys)
        lowered_keys = {key.strip().lower() for key in keys}
        is_system_combo = bool(lowered_keys & self.SYSTEM_KEYS) or normalized == normalize_hotkey(["alt", "f4"])
        if not self._settings.safety.block_system_hotkeys or not is_system_combo:
            return SafetyDecision(allowed=True)
        if normalized in self._allowlisted_hotkeys:
            return SafetyDecision(allowed=True)
        return SafetyDecision(
            allowed=False,
            reason_code="blocked_system_hotkey",
            message=f"Hotkey '{normalized}' is blocked by safety policy.",
        )

    def evaluate_window_operation(self, operation: str, title: str | None) -> SafetyDecision:
        """判断窗口类动作是否命中危险窗口标题保护规则。"""

        if not self._settings.safety.block_dangerous_window_ops:
            return SafetyDecision(allowed=True)
        safe_title = (title or "").strip().lower()
        if not safe_title:
            return SafetyDecision(allowed=True)
        if any(item and item in safe_title for item in self._dangerous_titles):
            return SafetyDecision(
                allowed=False,
                reason_code="blocked_dangerous_window",
                message=f"Window operation '{operation}' is blocked for target '{title}'.",
            )
        return SafetyDecision(allowed=True)
