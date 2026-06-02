"""定义服务层依赖的 typed desktop backend protocol。"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class DesktopBackend(Protocol):
    """描述 DesktopService 所需的后端能力集合。"""

    def get_screen_size(self) -> dict[str, Any]:
        """返回当前屏幕尺寸。"""

    def get_cursor_position(self) -> dict[str, Any]:
        """返回当前鼠标坐标。"""

    def move_mouse(self, x: int, y: int) -> dict[str, Any]:
        """移动鼠标到指定坐标。"""

    def click_mouse(self, button: str = "left") -> dict[str, Any]:
        """点击当前鼠标位置。"""

    def double_click_mouse(self, button: str = "left") -> dict[str, Any]:
        """双击当前鼠标位置。"""

    def drag_mouse(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict[str, Any]:
        """拖拽鼠标。"""

    def scroll_mouse(self, amount: int) -> dict[str, Any]:
        """滚动鼠标滚轮。"""

    def type_text(self, text: str) -> dict[str, Any]:
        """输入文本。"""

    def press_key(self, key: str) -> dict[str, Any]:
        """按下一次按键。"""

    def hold_key(self, key: str, state: str, duration_ms: int | None = None) -> dict[str, Any]:
        """按住或释放按键。"""

    def hotkey(self, keys: list[str]) -> dict[str, Any]:
        """执行组合键。"""

    def list_windows(self, title: str | None = None, exact: bool = False, visible_only: bool = True) -> list[dict[str, Any]]:
        """列出顶层窗口。"""

    def get_active_window(self) -> dict[str, Any]:
        """返回当前活动窗口。"""

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
        """聚焦目标窗口。"""

    def move_window(self, title: str, x: int, y: int, exact: bool = False) -> dict[str, Any]:
        """移动目标窗口。"""

    def resize_window(self, title: str, width: int, height: int, exact: bool = False) -> dict[str, Any]:
        """调整目标窗口尺寸。"""

    def get_clipboard(self) -> dict[str, Any]:
        """读取剪贴板文本。"""

    def set_clipboard(self, text: str) -> dict[str, Any]:
        """写入剪贴板文本。"""

    def clear_clipboard(self) -> dict[str, Any]:
        """清空剪贴板文本。"""

    def clipboard_has_text(self) -> dict[str, Any]:
        """判断剪贴板是否包含文本。"""

    def capture_screen(
        self,
        region: dict[str, int] | None = None,
        format: str = "png",
        quality: int = 90,
        grayscale: bool = False,
    ) -> dict[str, Any]:
        """截取屏幕并返回图片载荷。"""
