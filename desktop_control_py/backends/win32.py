"""基于 Win32 API、mss 和 Pillow 的本机桌面控制后端。"""

from __future__ import annotations

import base64
import ctypes
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import win32api
import win32clipboard
import win32con
import win32gui
from mss import mss
from PIL import Image, ImageOps

from ..errors import DesktopControlError
from ..models import AppSettings

USER32 = ctypes.windll.user32
KERNEL32 = ctypes.windll.kernel32
HWND_TOP = 0
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_SHOWWINDOW = 0x0040
ASFW_ANY = -1
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


@dataclass(slots=True)
class _MouseButtonMapping:
    """集中维护鼠标按键对应的 Win32 常量。"""

    down: int
    up: int


MOUSE_BUTTONS: dict[str, _MouseButtonMapping] = {
    "left": _MouseButtonMapping(win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
    "right": _MouseButtonMapping(win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP),
    "middle": _MouseButtonMapping(win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
}

SPECIAL_KEYS: dict[str, int] = {
    "enter": win32con.VK_RETURN,
    "tab": win32con.VK_TAB,
    "escape": win32con.VK_ESCAPE,
    "esc": win32con.VK_ESCAPE,
    "backspace": win32con.VK_BACK,
    "delete": win32con.VK_DELETE,
    "space": win32con.VK_SPACE,
    "up": win32con.VK_UP,
    "down": win32con.VK_DOWN,
    "left": win32con.VK_LEFT,
    "right": win32con.VK_RIGHT,
    "home": win32con.VK_HOME,
    "end": win32con.VK_END,
    "pageup": win32con.VK_PRIOR,
    "pagedown": win32con.VK_NEXT,
    "ctrl": win32con.VK_CONTROL,
    "shift": win32con.VK_SHIFT,
    "alt": win32con.VK_MENU,
    "win": win32con.VK_LWIN,
    "lwin": win32con.VK_LWIN,
    "rwin": win32con.VK_RWIN,
    "f1": win32con.VK_F1,
    "f2": win32con.VK_F2,
    "f3": win32con.VK_F3,
    "f4": win32con.VK_F4,
    "f5": win32con.VK_F5,
    "f6": win32con.VK_F6,
    "f7": win32con.VK_F7,
    "f8": win32con.VK_F8,
    "f9": win32con.VK_F9,
    "f10": win32con.VK_F10,
    "f11": win32con.VK_F11,
    "f12": win32con.VK_F12,
}


def match_window_title(actual: str, query: str | None, exact: bool) -> bool:
    """按 exact 或大小写不敏感子串方式匹配窗口标题。"""

    if not query:
        return True
    if exact:
        return actual == query
    return query.lower() in actual.lower()


def encode_image_payload(image: Image.Image, format: str, quality: int, grayscale: bool) -> dict[str, Any]:
    """把 PIL 图像编码成 base64 结果包。"""

    working = image
    if grayscale:
        working = ImageOps.grayscale(working)

    buffer = BytesIO()
    save_kwargs: dict[str, Any] = {}
    if format.lower() in {"jpeg", "jpg"}:
        save_kwargs["quality"] = quality
        if working.mode not in {"RGB", "L"}:
            working = working.convert("RGB")
    working.save(buffer, format=format.upper(), **save_kwargs)
    mime_type = "image/jpeg" if format.lower() in {"jpeg", "jpg"} else "image/png"
    return {
        "mime_type": mime_type,
        "width": working.width,
        "height": working.height,
        "base64_data": base64.b64encode(buffer.getvalue()).decode("utf-8"),
    }


class KEYBDINPUT(ctypes.Structure):
    """对应 Win32 SendInput 的键盘输入结构。"""

    _fields_ = [
        ("wVk", ctypes.c_ushort),
        ("wScan", ctypes.c_ushort),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class MOUSEINPUT(ctypes.Structure):
    """对应 Win32 SendInput 的鼠标输入结构。"""

    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    """封装 SendInput 支持的不同输入联合体。"""

    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    """表示一次 SendInput 调用的输入单元。"""

    _fields_ = [("type", ctypes.c_ulong), ("union", INPUT_UNION)]


class WindowsDesktopBackend:
    """通过 Win32 API 直接执行鼠标、键盘、窗口和截图操作。"""

    def __init__(self, settings: AppSettings):
        """保存运行配置，供节奏控制和默认参数读取。"""

        self._settings = settings

    def get_screen_size(self) -> dict[str, int]:
        """读取主屏幕宽高。"""

        return {
            "width": USER32.GetSystemMetrics(0),
            "height": USER32.GetSystemMetrics(1),
        }

    def get_screen_metrics(self) -> dict[str, Any]:
        """读取虚拟屏、多显示器和系统 DPI 指标，供坐标型 agent 稳定定位。"""

        with mss() as sct:
            virtual_screen = self._monitor_payload(index=0, monitor=sct.monitors[0], primary=False)
            monitors = [
                self._monitor_payload(index=index, monitor=monitor, primary=index == 1)
                for index, monitor in enumerate(sct.monitors[1:], start=1)
            ]

        dpi = self._system_dpi()
        return {
            "primary_screen": self.get_screen_size(),
            "virtual_screen": virtual_screen,
            "monitors": monitors,
            "dpi": {"system": dpi, "scale": round(dpi / 96, 3)},
        }

    def get_cursor_position(self) -> dict[str, int]:
        """读取当前鼠标坐标。"""

        point = win32gui.GetCursorPos()
        return {"x": point[0], "y": point[1]}

    def move_mouse(self, x: int, y: int) -> dict[str, int]:
        """按机械精准策略移动鼠标。"""

        current = self.get_cursor_position()
        duration = max(self._settings.timing.mouse_move_duration_ms, 0)
        if duration <= 0:
            USER32.SetCursorPos(x, y)
        else:
            steps = max(1, duration // 10)
            for step in range(1, steps + 1):
                next_x = round(current["x"] + (x - current["x"]) * step / steps)
                next_y = round(current["y"] + (y - current["y"]) * step / steps)
                USER32.SetCursorPos(next_x, next_y)
                time.sleep(duration / steps / 1000)
        self._sleep_ms(self._settings.timing.post_move_delay_ms)
        return {"x": x, "y": y}

    def click_mouse(self, button: str = "left") -> dict[str, str]:
        """在当前位置执行一次鼠标点击。"""

        mapping = self._mouse_mapping(button)
        win32api.mouse_event(mapping.down, 0, 0, 0, 0)
        win32api.mouse_event(mapping.up, 0, 0, 0, 0)
        self._sleep_ms(self._settings.timing.post_click_delay_ms)
        return {"button": button}

    def double_click_mouse(self, button: str = "left") -> dict[str, str]:
        """在当前位置执行双击。"""

        self.click_mouse(button=button)
        self._sleep_ms(self._settings.timing.key_press_delay_ms)
        self.click_mouse(button=button)
        return {"button": button}

    def drag_mouse(self, from_x: int, from_y: int, to_x: int, to_y: int, button: str = "left") -> dict[str, Any]:
        """执行拖拽动作。"""

        mapping = self._mouse_mapping(button)
        self.move_mouse(from_x, from_y)
        win32api.mouse_event(mapping.down, 0, 0, 0, 0)
        self.move_mouse(to_x, to_y)
        win32api.mouse_event(mapping.up, 0, 0, 0, 0)
        return {
            "from_x": from_x,
            "from_y": from_y,
            "to_x": to_x,
            "to_y": to_y,
            "button": button,
        }

    def scroll_mouse(self, amount: int) -> dict[str, int]:
        """滚动鼠标滚轮。"""

        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)
        return {"amount": amount}

    def type_text(self, text: str) -> dict[str, Any]:
        """按 Unicode 字符逐个注入文本。"""

        for char in text:
            self._send_unicode_character(char)
            self._sleep_ms(self._settings.timing.text_type_interval_ms)
        return {"text": text}

    def press_key(self, key: str) -> dict[str, str]:
        """按下一次单个按键。"""

        vk_code = self._virtual_key(key)
        self._key_down(vk_code)
        self._sleep_ms(self._settings.timing.key_press_delay_ms)
        self._key_up(vk_code)
        return {"key": key}

    def hold_key(self, key: str, state: str, duration_ms: int | None = None) -> dict[str, Any]:
        """执行按键按下、保持或释放。"""

        vk_code = self._virtual_key(key)
        normalized_state = state.lower()
        if normalized_state == "down":
            self._key_down(vk_code)
            if duration_ms:
                self._sleep_ms(duration_ms)
                self._key_up(vk_code)
        elif normalized_state == "up":
            self._key_up(vk_code)
        else:
            raise DesktopControlError(
                code="invalid_key_state",
                message=f"Unsupported key state: {state}",
                details={"state": state},
            )
        return {"key": key, "state": normalized_state, "duration_ms": duration_ms}

    def hotkey(self, keys: list[str]) -> dict[str, list[str]]:
        """按顺序按下组合键，并按逆序释放。"""

        virtual_keys = [self._virtual_key(key) for key in keys]
        for vk_code in virtual_keys:
            self._key_down(vk_code)
            self._sleep_ms(self._settings.timing.key_press_delay_ms)
        for vk_code in reversed(virtual_keys):
            self._key_up(vk_code)
            self._sleep_ms(self._settings.timing.key_press_delay_ms)
        return {"keys": keys}

    def list_windows(
        self,
        title: str | None = None,
        exact: bool = False,
        visible_only: bool = True,
    ) -> list[dict[str, Any]]:
        """枚举顶层窗口并按条件筛选。"""

        windows: list[dict[str, Any]] = []

        def callback(hwnd: int, _: Any) -> None:
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return
            window_title = win32gui.GetWindowText(hwnd)
            if not window_title:
                return
            if not match_window_title(window_title, title, exact):
                return
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            process_id = self._window_process_id(hwnd)
            windows.append(
                {
                    "handle": hwnd,
                    "title": window_title,
                    "class_name": win32gui.GetClassName(hwnd),
                    "process_id": process_id,
                    "process_name": self._process_name(process_id),
                    "visible": bool(win32gui.IsWindowVisible(hwnd)),
                    "minimized": bool(win32gui.IsIconic(hwnd)),
                    "rect": {
                        "left": left,
                        "top": top,
                        "right": right,
                        "bottom": bottom,
                        "width": right - left,
                        "height": bottom - top,
                    },
                }
            )

        win32gui.EnumWindows(callback, None)
        return windows

    def get_active_window(self) -> dict[str, Any]:
        """读取当前前台窗口信息。"""

        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            raise DesktopControlError(code="no_active_window", message="No active window found.")
        return self._window_info(hwnd)

    def focus_window(self, title: str, exact: bool = False, timeout_ms: int | None = None) -> dict[str, Any]:
        """查找并聚焦目标窗口。"""

        window = self._find_window(title=title, exact=exact)
        hwnd = window["handle"]
        deadline = time.perf_counter() + (timeout_ms or self._settings.timing.window_find_timeout_ms) / 1000
        attempt_errors: list[str] = []
        while time.perf_counter() < deadline:
            if self._bring_window_foreground(hwnd, attempt_errors):
                self._sleep_ms(self._settings.timing.post_focus_delay_ms)
                return self._window_info(hwnd)
            time.sleep(0.05)

        raise DesktopControlError(
            code="window_focus_timeout",
            message=f"Timed out while focusing window '{title}'.",
            details={"title": title, "attempt_errors": attempt_errors[-5:]},
        )

    def move_window(self, title: str, x: int, y: int, exact: bool = False) -> dict[str, Any]:
        """移动窗口位置，同时保持原有尺寸不变。"""

        window = self._find_window(title=title, exact=exact)
        rect = window["rect"]
        win32gui.MoveWindow(window["handle"], x, y, rect["width"], rect["height"], True)
        return self._window_info(window["handle"])

    def resize_window(self, title: str, width: int, height: int, exact: bool = False) -> dict[str, Any]:
        """调整窗口尺寸，同时保持原有位置不变。"""

        window = self._find_window(title=title, exact=exact)
        rect = window["rect"]
        win32gui.MoveWindow(window["handle"], rect["left"], rect["top"], width, height, True)
        return self._window_info(window["handle"])

    def get_clipboard(self) -> dict[str, str]:
        """读取文本剪贴板。"""

        win32clipboard.OpenClipboard()
        try:
            if not win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT):
                return {"text": ""}
            return {"text": win32clipboard.GetClipboardData(win32con.CF_UNICODETEXT)}
        finally:
            win32clipboard.CloseClipboard()

    def set_clipboard(self, text: str) -> dict[str, str]:
        """设置文本剪贴板。"""

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardText(text, win32con.CF_UNICODETEXT)
            return {"text": text}
        finally:
            win32clipboard.CloseClipboard()

    def clear_clipboard(self) -> dict[str, bool]:
        """清空剪贴板。"""

        win32clipboard.OpenClipboard()
        try:
            win32clipboard.EmptyClipboard()
            return {"cleared": True}
        finally:
            win32clipboard.CloseClipboard()

    def clipboard_has_text(self) -> dict[str, bool]:
        """判断剪贴板是否存在 Unicode 文本。"""

        win32clipboard.OpenClipboard()
        try:
            return {"has_text": bool(win32clipboard.IsClipboardFormatAvailable(win32con.CF_UNICODETEXT))}
        finally:
            win32clipboard.CloseClipboard()

    def capture_screen(
        self,
        region: dict[str, int] | None = None,
        format: str = "png",
        quality: int = 90,
        grayscale: bool = False,
    ) -> dict[str, Any]:
        """截取全屏或区域截图，并编码为 base64 结果。"""

        with mss() as sct:
            monitor = region or sct.monitors[1]
            screenshot = sct.grab(monitor)
        image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
        return encode_image_payload(image=image, format=format, quality=quality, grayscale=grayscale)

    @staticmethod
    def _monitor_payload(index: int, monitor: dict[str, int], primary: bool) -> dict[str, Any]:
        """把 mss monitor 结构转换为公开的屏幕指标载荷。"""

        return {
            "index": index,
            "left": int(monitor.get("left", 0)),
            "top": int(monitor.get("top", 0)),
            "width": int(monitor.get("width", 0)),
            "height": int(monitor.get("height", 0)),
            "primary": primary,
        }

    @staticmethod
    def _system_dpi() -> int:
        """读取系统 DPI；不可用时回退到 Windows 标准 96 DPI。"""

        try:
            return int(USER32.GetDpiForSystem())
        except Exception:  # noqa: BLE001
            return 96

    def _window_info(self, hwnd: int) -> dict[str, Any]:
        """读取单个窗口的标题、类名与矩形信息。"""

        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        process_id = self._window_process_id(hwnd)
        return {
            "handle": hwnd,
            "title": win32gui.GetWindowText(hwnd),
            "class_name": win32gui.GetClassName(hwnd),
            "process_id": process_id,
            "process_name": self._process_name(process_id),
            "visible": bool(win32gui.IsWindowVisible(hwnd)),
            "minimized": bool(win32gui.IsIconic(hwnd)),
            "rect": {
                "left": left,
                "top": top,
                "right": right,
                "bottom": bottom,
                "width": right - left,
                "height": bottom - top,
            },
        }

    def _find_window(self, title: str, exact: bool) -> dict[str, Any]:
        """查找单个匹配窗口，找不到则抛出稳定错误。"""

        windows = self.list_windows(title=title, exact=exact, visible_only=True)
        if not windows:
            raise DesktopControlError(
                code="window_not_found",
                message=f"Window '{title}' not found.",
                details={"title": title, "exact": exact},
            )
        return windows[0]

    def _bring_window_foreground(self, hwnd: int, attempt_errors: list[str]) -> bool:
        """按多种 Win32 策略尝试把目标窗口切到前台。"""

        if self._is_foreground_window(hwnd):
            return True
        self._prepare_window(hwnd)
        self._try_direct_foreground(hwnd, attempt_errors)
        if self._is_foreground_window(hwnd):
            return True
        self._try_attached_foreground(hwnd, attempt_errors)
        if self._is_foreground_window(hwnd):
            return True
        self._try_switch_to_window(hwnd, attempt_errors)
        if self._is_foreground_window(hwnd):
            return True
        self._try_alt_unlock_foreground(hwnd, attempt_errors)
        return self._is_foreground_window(hwnd)

    def _prepare_window(self, hwnd: int) -> None:
        """在真正聚焦前先恢复并显示窗口。"""

        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        USER32.BringWindowToTop(hwnd)
        USER32.SetWindowPos(hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)

    def _try_direct_foreground(self, hwnd: int, attempt_errors: list[str]) -> None:
        """先用常规的前台切换策略尝试聚焦。"""

        try:
            USER32.AllowSetForegroundWindow(ASFW_ANY)
            USER32.SetForegroundWindow(hwnd)
        except Exception as exc:  # noqa: BLE001
            attempt_errors.append(f"direct:{exc}")

    def _try_attached_foreground(self, hwnd: int, attempt_errors: list[str]) -> None:
        """在输入线程附着后重试前台切换，绕过常见的前台锁定限制。"""

        foreground = USER32.GetForegroundWindow()
        current_thread = KERNEL32.GetCurrentThreadId()
        target_thread = self._window_thread_id(hwnd)
        foreground_thread = self._window_thread_id(foreground) if foreground else 0
        attached_pairs: list[tuple[int, int]] = []

        try:
            for source_thread, target_attach_thread in (
                (current_thread, target_thread),
                (current_thread, foreground_thread),
            ):
                if (
                    source_thread
                    and target_attach_thread
                    and source_thread != target_attach_thread
                    and USER32.AttachThreadInput(source_thread, target_attach_thread, True)
                ):
                    attached_pairs.append((source_thread, target_attach_thread))
            USER32.BringWindowToTop(hwnd)
            USER32.SetForegroundWindow(hwnd)
            USER32.SetActiveWindow(hwnd)
            USER32.SetFocus(hwnd)
        except Exception as exc:  # noqa: BLE001
            attempt_errors.append(f"attach:{exc}")
        finally:
            for source_thread, target_attach_thread in reversed(attached_pairs):
                USER32.AttachThreadInput(source_thread, target_attach_thread, False)

    def _try_switch_to_window(self, hwnd: int, attempt_errors: list[str]) -> None:
        """使用 SwitchToThisWindow 作为兼容性回退。"""

        switch_to_this_window = getattr(USER32, "SwitchToThisWindow", None)
        if switch_to_this_window is None:
            return
        try:
            switch_to_this_window(hwnd, True)
        except Exception as exc:  # noqa: BLE001
            attempt_errors.append(f"switch:{exc}")

    def _try_alt_unlock_foreground(self, hwnd: int, attempt_errors: list[str]) -> None:
        """发送一次轻量 Alt 键解锁，再最后重试常规聚焦。"""

        try:
            self._key_down(win32con.VK_MENU)
            self._sleep_ms(self._settings.timing.key_press_delay_ms)
            self._key_up(win32con.VK_MENU)
            self._sleep_ms(self._settings.timing.key_press_delay_ms)
            USER32.BringWindowToTop(hwnd)
            USER32.SetForegroundWindow(hwnd)
        except Exception as exc:  # noqa: BLE001
            attempt_errors.append(f"alt_unlock:{exc}")

    @staticmethod
    def _is_foreground_window(hwnd: int) -> bool:
        """判断目标窗口当前是否已经处于前台。"""

        return bool(hwnd) and USER32.GetForegroundWindow() == hwnd

    @staticmethod
    def _window_process_id(hwnd: int) -> int:
        """读取窗口所属进程 ID，供高层语义工具识别真实浏览器进程。"""

        if not hwnd:
            return 0
        process_id = ctypes.c_ulong(0)
        USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
        return int(process_id.value)

    @staticmethod
    def _process_name(process_id: int) -> str:
        """通过 Windows 进程句柄读取可执行文件名，失败时返回空字符串。"""

        if not process_id:
            return ""
        handle = KERNEL32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, process_id)
        if not handle:
            return ""
        try:
            size = ctypes.c_ulong(32768)
            buffer = ctypes.create_unicode_buffer(size.value)
            if KERNEL32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
                return Path(buffer.value).name
        finally:
            KERNEL32.CloseHandle(handle)
        return ""

    @staticmethod
    def _window_thread_id(hwnd: int) -> int:
        """读取窗口所属线程 ID，供线程附着策略复用。"""

        if not hwnd:
            return 0
        process_id = ctypes.c_ulong(0)
        return USER32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))

    @staticmethod
    def _mouse_mapping(button: str) -> _MouseButtonMapping:
        """把按钮名称映射到 Win32 鼠标事件常量。"""

        normalized = button.lower()
        if normalized not in MOUSE_BUTTONS:
            raise DesktopControlError(
                code="invalid_mouse_button",
                message=f"Unsupported mouse button: {button}",
                details={"button": button},
            )
        return MOUSE_BUTTONS[normalized]

    def _virtual_key(self, key: str) -> int:
        """将友好的键名解析成 Win32 虚拟键值。"""

        normalized = key.strip().lower()
        if normalized in SPECIAL_KEYS:
            return SPECIAL_KEYS[normalized]
        if len(normalized) == 1:
            scan = USER32.VkKeyScanW(ord(normalized))
            vk_code = scan & 0xFF
            if vk_code == 0xFF:
                raise DesktopControlError(
                    code="invalid_key",
                    message=f"Cannot map key '{key}' to a virtual key.",
                    details={"key": key},
                )
            return vk_code
        raise DesktopControlError(
            code="invalid_key",
            message=f"Unsupported key '{key}'.",
            details={"key": key},
        )

    @staticmethod
    def _key_down(vk_code: int) -> None:
        """发送按键按下事件。"""

        win32api.keybd_event(vk_code, 0, 0, 0)

    @staticmethod
    def _key_up(vk_code: int) -> None:
        """发送按键释放事件。"""

        win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)

    @staticmethod
    def _sleep_ms(duration_ms: int | None) -> None:
        """按毫秒数执行安全睡眠。"""

        if duration_ms and duration_ms > 0:
            time.sleep(duration_ms / 1000)

    @staticmethod
    def _send_unicode_character(char: str) -> None:
        """通过 SendInput 发送单个 Unicode 字符。"""

        extra = ctypes.c_ulong(0)
        down = INPUT(
            type=1,
            union=INPUT_UNION(
                ki=KEYBDINPUT(0, ord(char), win32con.KEYEVENTF_UNICODE, 0, ctypes.pointer(extra))
            ),
        )
        up = INPUT(
            type=1,
            union=INPUT_UNION(
                ki=KEYBDINPUT(
                    0,
                    ord(char),
                    win32con.KEYEVENTF_UNICODE | win32con.KEYEVENTF_KEYUP,
                    0,
                    ctypes.pointer(extra),
                )
            ),
        )
        USER32.SendInput(1, ctypes.pointer(down), ctypes.sizeof(down))
        USER32.SendInput(1, ctypes.pointer(up), ctypes.sizeof(up))
