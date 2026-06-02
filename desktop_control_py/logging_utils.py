"""提供文本日志与结构化 JSONL 审计日志能力。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import AppSettings


class StructuredLogger:
    """统一负责文本日志和结构化审计日志的写入。"""

    def __init__(self, settings: AppSettings):
        """根据配置初始化 logger 与落盘目录。"""

        self._settings = settings
        self._logger = logging.getLogger("desktop_control_py")
        self._logger.setLevel(settings.logging.level.upper())
        self._logger.handlers.clear()
        handler = logging.FileHandler(settings.logging.log_file, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        self._logger.addHandler(handler)
        self._logger.propagate = False

    def info(self, message: str) -> None:
        """写入一条普通信息日志。"""

        self._logger.info(message)

    def warning(self, message: str) -> None:
        """写入一条警告日志。"""

        self._logger.warning(message)

    def error(self, message: str) -> None:
        """写入一条错误日志。"""

        self._logger.error(message)

    def audit(self, action_name: str, payload: dict[str, Any]) -> None:
        """把一次动作执行结果以结构化 JSONL 形式写入审计日志。"""

        record = {
            "timestamp": datetime.now(UTC).isoformat(),
            "action_name": action_name,
            **payload,
        }
        self._append_jsonl(self._settings.logging.session_file, record)

    @staticmethod
    def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
        """向 JSONL 文件尾部追加一条结构化记录。"""

        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
