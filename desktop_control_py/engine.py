"""提供动作执行、重试、节奏控制与结构化结果包装。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from .errors import DesktopControlError
from .logging_utils import StructuredLogger
from .models import ActionResult, AppSettings


class ActionEngine:
    """统一驱动所有桌面动作的执行、重试和审计逻辑。"""

    def __init__(self, settings: AppSettings, logger: StructuredLogger | None = None):
        """保存配置并准备可复用的结构化日志器。"""

        self._settings = settings
        self._logger = logger or StructuredLogger(settings)

    def execute(
        self,
        action_name: str,
        action: Callable[[], Any],
        *,
        retryable: bool,
        metadata: dict[str, Any] | None = None,
    ) -> ActionResult:
        """同步执行一个动作，并按策略包装结果与错误。"""

        warnings: list[str] = []
        attempts = self._settings.timing.safe_retry_attempts if retryable else 1
        started = time.perf_counter()
        last_error: Exception | None = None

        for attempt in range(1, attempts + 1):
            try:
                data = action()
                duration_ms = int((time.perf_counter() - started) * 1000)
                result = ActionResult(duration_ms=duration_ms, warnings=warnings, data=data)
                self._logger.audit(
                    action_name,
                    {
                        "ok": True,
                        "duration_ms": duration_ms,
                        "warnings": warnings,
                        "metadata": metadata or {},
                    },
                )
                return result
            except DesktopControlError as exc:
                last_error = exc
                break
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= attempts:
                    break
                warning = f"{action_name} retry {attempt} failed: {exc}"
                warnings.append(warning)
                self._logger.warning(warning)
                time.sleep(max(self._settings.timing.safe_retry_interval_ms, 0) / 1000)

        duration_ms = int((time.perf_counter() - started) * 1000)
        if isinstance(last_error, DesktopControlError):
            error = last_error
        else:
            error = DesktopControlError(
                code="action_failed",
                message=str(last_error) if last_error else f"{action_name} failed",
                details={"action_name": action_name},
            )
        self._logger.audit(
            action_name,
            {
                "ok": False,
                "duration_ms": duration_ms,
                "warnings": warnings,
                "metadata": metadata or {},
                "error_code": error.code,
                "error_message": error.message,
            },
        )
        raise error
