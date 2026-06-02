"""定义配置、返回值和安全判断等核心数据模型。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TimingSettings(BaseModel):
    """定义动作引擎用于机械控制、重试和聚焦等待的时间参数。"""

    model_config = ConfigDict(extra="ignore")

    mouse_move_duration_ms: int = 0
    post_move_delay_ms: int = 0
    key_press_delay_ms: int = 20
    text_type_interval_ms: int = 8
    post_click_delay_ms: int = 40
    post_focus_delay_ms: int = 120
    safe_retry_attempts: int = 3
    safe_retry_interval_ms: int = 150
    window_find_timeout_ms: int = 1500


class SafetySettings(BaseModel):
    """定义软保护规则与风险窗口白名单。"""

    model_config = ConfigDict(extra="ignore")

    block_system_hotkeys: bool = True
    block_dangerous_window_ops: bool = True
    dangerous_window_titles: list[str] = Field(default_factory=list)
    allowed_system_hotkeys: list[str] = Field(default_factory=list)


class LoggingSettings(BaseModel):
    """定义文本日志与结构化会话日志的落盘位置。"""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    level: str = "INFO"
    log_file: Path
    session_file: Path


class ScreenshotSettings(BaseModel):
    """定义截图工具的默认输出行为。"""

    model_config = ConfigDict(extra="ignore")

    default_format: Literal["png", "jpeg"] = "png"
    default_quality: int = 90
    grayscale: bool = False


class AppSettings(BaseModel):
    """表示整个桌面控制服务的最终运行配置。"""

    model_config = ConfigDict(extra="ignore", arbitrary_types_allowed=True)

    project_root: Path
    config_path: Path
    runtime_dir: Path
    timing: TimingSettings
    safety: SafetySettings
    logging: LoggingSettings
    screenshot: ScreenshotSettings


class SafetyDecision(BaseModel):
    """表示某个动作在当前安全策略下是否允许执行。"""

    model_config = ConfigDict(extra="ignore")

    allowed: bool
    reason_code: str | None = None
    message: str | None = None


class ActionResult(BaseModel):
    """统一约束所有工具对外返回的结果包。"""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    duration_ms: int
    warnings: list[str] = Field(default_factory=list)
    data: Any = None
