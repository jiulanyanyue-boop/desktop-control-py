"""导出当前项目使用的桌面后端抽象与实现。"""

from .protocol import DesktopBackend
from .win32 import WindowsDesktopBackend

__all__ = ["DesktopBackend", "WindowsDesktopBackend"]
