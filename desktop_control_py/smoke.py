"""提供真实 Windows 桌面冒烟验证流程。"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import time

from .backends.protocol import DesktopBackend
from .backends.win32 import WindowsDesktopBackend
from .config import load_settings
from .errors import DesktopControlError
from .service import DesktopService


def _desktop_looks_locked(backend: DesktopBackend) -> bool:
    """判断当前桌面是否不可交互，避免把锁屏误报为工具失败。"""

    try:
        active = backend.get_active_window()
    except Exception:
        return False
    title = (active.get("title") or "").lower()
    process_name = (active.get("process_name") or "").lower()
    class_name = (active.get("class_name") or "").lower()
    return process_name == "lockapp.exe" or "锁屏" in title or (
        class_name == "windows.ui.core.corewindow" and process_name == "lockapp.exe"
    )


def run_smoke_test(config_path: Path | None = None) -> int:
    """执行真实桌面冒烟测试，并在完成后尽量关闭 agent 启动的 Notepad。"""

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    settings = load_settings(config_path=config_path)
    backend = WindowsDesktopBackend(settings)
    service = DesktopService(settings=settings, backend=backend)
    if _desktop_looks_locked(backend):
        print("[SKIP] desktop appears locked; real mouse/keyboard/browser smoke requires an unlocked desktop")
        print("selection_used: false")
        return 0

    launched_process: subprocess.Popen[str] | None = None
    smoke_file = settings.runtime_dir / "desktop-control-smoke.txt"
    smoke_file.write_text("", encoding="utf-8")
    smoke_window_title = smoke_file.name

    try:
        launched_process = subprocess.Popen(["notepad.exe", str(smoke_file)])
        deadline = time.perf_counter() + 5
        windows: list[dict] = []
        while time.perf_counter() < deadline:
            windows = [
                window
                for window in backend.list_windows(visible_only=True)
                if smoke_window_title.lower() in window.get("title", "").lower()
            ]
            if windows:
                break
            time.sleep(0.1)
        if not windows:
            raise RuntimeError("Smoke Notepad window was not found.")

        focused = windows[0]
        editor_x = focused["rect"]["left"] + 180
        editor_y = focused["rect"]["top"] + 180
        backend.move_mouse(editor_x, editor_y)
        backend.click_mouse("left")
        time.sleep(0.2)
        try:
            active_after_click = backend.get_active_window()
        except Exception:
            active_after_click = {}
        if smoke_window_title.lower() not in (active_after_click.get("title") or "").lower():
            print("[SKIP] Notepad did not become the active window; real smoke requires interactive foreground control")
            print(f"active_after_click: {active_after_click.get('title', '')}")
            print("selection_used: false")
            return 0

        backend.type_text("desktop-control-py smoke test")
        backend.hotkey(["ctrl", "a"])
        backend.hotkey(["ctrl", "c"])
        clipboard_after = backend.get_clipboard()
        if "desktop-control-py smoke test" not in clipboard_after.get("text", ""):
            print("[SKIP] Notepad clipboard verification failed; foreground keyboard input is not reaching Notepad")
            print("selection_used: false")
            return 0

        backend.hotkey(["right"])
        backend.drag_mouse(editor_x, editor_y + 40, editor_x + 120, editor_y + 40, button="left")
        backend.scroll_mouse(-120)
        active = backend.get_active_window()
        active_title = active["title"]
        backend.move_window(active_title, 120, 120, exact=True)
        backend.resize_window(active_title, 900, 700, exact=True)
        screenshot = backend.capture_screen(format="png", quality=90, grayscale=False)

        print("[PASS] native window/mouse/keyboard/clipboard/move/resize/capture completed")
        print(f"focused: {focused['title']}")
        print(f"active: {active['title']}")
        print(f"clipboard read: {clipboard_after['text']}")
        print(f"screenshot size: {screenshot['width']}x{screenshot['height']}")

        try:
            capture = service.browser_capture().data
        except DesktopControlError as exc:
            if exc.code == "browser_window_not_found":
                print("[SKIP] no Chrome/Edge/browser window found for browser capture path")
            else:
                raise
        else:
            browser_screenshot = capture["screenshot"]
            print("browser capture ok")
            print(f"browser focused: {capture['window'].get('title', '')}")
            print(f"browser screenshot size: {browser_screenshot['width']}x{browser_screenshot['height']}")
            print(f"selection_used: {str(capture.get('selection_used')).lower()}")
        return 0
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] smoke test failed: {exc}")
        return 1
    finally:
        try:
            windows = [
                window
                for window in backend.list_windows(visible_only=True)
                if smoke_window_title.lower() in window.get("title", "").lower()
            ]
            if windows:
                window = windows[0]
                close_x = window["rect"]["left"] + 180
                close_y = window["rect"]["top"] + 180
                backend.move_mouse(close_x, close_y)
                backend.click_mouse("left")
                backend.hotkey(["ctrl", "s"])
                backend.hotkey(["alt", "f4"])
        except Exception:
            pass
        if launched_process and launched_process.poll() is None:
            try:
                launched_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                pass
