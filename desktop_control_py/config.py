"""负责读取 TOML 配置并生成运行时设置对象。"""

from __future__ import annotations

from pathlib import Path
from typing import Any
import tomllib

from .models import (
    AppSettings,
    LoggingSettings,
    SafetySettings,
    ScreenshotSettings,
    TimingSettings,
)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """递归合并配置字典，让用户配置覆盖默认配置。"""

    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
            continue
        merged[key] = value
    return merged


def _read_toml(path: Path) -> dict[str, Any]:
    """读取 TOML 文件内容并返回普通字典。"""

    if not path.exists():
        return {}
    return tomllib.loads(path.read_text(encoding="utf-8"))


def _resolve_runtime_path(project_root: Path, raw_path: str) -> Path:
    """将配置中的相对路径统一解析到项目根目录下。"""

    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (project_root / path).resolve()


def load_settings(config_path: Path | None = None, project_root: Path | None = None) -> AppSettings:
    """加载默认配置与可选覆盖配置，并生成强类型运行设置。"""

    if project_root is None:
        project_root = Path(__file__).resolve().parent.parent
    project_root = project_root.resolve()

    default_config_path = project_root / "config" / "default.toml"
    effective_config_path = config_path.resolve() if config_path else default_config_path

    default_data = _read_toml(default_config_path)
    override_data = _read_toml(effective_config_path) if effective_config_path != default_config_path else {}
    merged = _deep_merge(default_data, override_data)

    timing = TimingSettings.model_validate(merged.get("timing", {}))
    safety = SafetySettings.model_validate(merged.get("safety", {}))
    logging_data = merged.get("logging", {})
    runtime_dir = (project_root / "runtime").resolve()
    logging = LoggingSettings(
        level=logging_data.get("level", "INFO"),
        log_file=_resolve_runtime_path(project_root, logging_data.get("log_file", "runtime/desktop-control.log")),
        session_file=_resolve_runtime_path(
            project_root,
            logging_data.get("session_file", "runtime/session.jsonl"),
        ),
    )
    screenshot = ScreenshotSettings.model_validate(merged.get("screenshot", {}))
    runtime_dir.mkdir(parents=True, exist_ok=True)
    logging.log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.session_file.parent.mkdir(parents=True, exist_ok=True)

    return AppSettings(
        project_root=project_root,
        config_path=effective_config_path,
        runtime_dir=runtime_dir,
        timing=timing,
        safety=safety,
        logging=logging,
        screenshot=screenshot,
    )
