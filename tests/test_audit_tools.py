from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class MinimalBackend:
    """满足服务构造但不应被 audit_recent 使用的后端替身。"""

    def __getattr__(self, name: str) -> object:
        """拦截所有后端访问。"""

        raise AssertionError(f"audit_recent must not call backend method: {name}")


def _settings(tmp_path: Path):
    """构造审计日志路径位于临时目录的测试配置。"""

    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/app.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def _write_audit_lines(path: Path, rows: list[dict[str, Any] | str]) -> None:
    """向 JSONL 文件写入测试审计记录或原始坏行。"""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            if isinstance(row, str):
                handle.write(row + "\n")
            else:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_audit_recent_returns_empty_records_when_file_is_missing(tmp_path: Path) -> None:
    """验证审计文件不存在时查询返回空记录而不是失败。"""

    from desktop_control_py.service import DesktopService

    settings = _settings(tmp_path)
    service = DesktopService(settings=settings, backend=MinimalBackend())

    result = service.audit_recent()

    assert result.ok is True
    assert result.data["records"] == []
    assert result.data["read_warnings"] == []


def test_audit_recent_limits_and_filters_records(tmp_path: Path) -> None:
    """验证审计查询支持最近记录数量、动作名和成功状态过滤。"""

    from desktop_control_py.service import DesktopService

    settings = _settings(tmp_path)
    _write_audit_lines(
        settings.logging.session_file,
        [
            {"timestamp": "1", "action_name": "screen_size", "ok": True},
            {"timestamp": "2", "action_name": "mouse_click", "ok": False},
            {"timestamp": "3", "action_name": "screen_size", "ok": False},
            {"timestamp": "4", "action_name": "screen_size", "ok": True},
        ],
    )
    service = DesktopService(settings=settings, backend=MinimalBackend())

    result = service.audit_recent(limit=2, action_name="screen_size", ok=True)

    assert result.ok is True
    assert result.data["records"] == [
        {"timestamp": "1", "action_name": "screen_size", "ok": True},
        {"timestamp": "4", "action_name": "screen_size", "ok": True},
    ]
    assert result.data["limit"] == 2
    assert result.data["read_warnings"] == []


def test_audit_recent_reports_malformed_json_lines(tmp_path: Path) -> None:
    """验证坏 JSON 行会被跳过并出现在读取 warning 中。"""

    from desktop_control_py.service import DesktopService

    settings = _settings(tmp_path)
    _write_audit_lines(
        settings.logging.session_file,
        [
            {"timestamp": "1", "action_name": "screen_size", "ok": True},
            "{not-json",
            {"timestamp": "2", "action_name": "mouse_click", "ok": False},
        ],
    )
    service = DesktopService(settings=settings, backend=MinimalBackend())

    result = service.audit_recent(limit=10)

    assert result.ok is True
    assert [record["timestamp"] for record in result.data["records"]] == ["1", "2"]
    assert len(result.data["read_warnings"]) == 1
    assert "line 2" in result.data["read_warnings"][0]
