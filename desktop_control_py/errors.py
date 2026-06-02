"""统一定义桌面控制 MCP 的领域错误。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DesktopControlError(Exception):
    """表示桌面控制过程中可以向上游稳定暴露的业务错误。"""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        """返回便于日志与错误消息展示的可读文本。"""

        return f"{self.code}: {self.message}"
