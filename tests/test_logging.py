from __future__ import annotations

import json
from pathlib import Path


def _settings(tmp_path: Path):
    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[timing]",
                "safe_retry_attempts = 2",
                "safe_retry_interval_ms = 0",
                "",
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/audit.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def test_action_engine_writes_structured_audit_log(tmp_path: Path) -> None:
    from desktop_control_py.engine import ActionEngine

    settings = _settings(tmp_path)
    engine = ActionEngine(settings=settings)

    engine.execute("screen_size", action=lambda: {"width": 100, "height": 100}, retryable=True)

    lines = settings.logging.session_file.read_text(encoding="utf-8").strip().splitlines()
    payload = json.loads(lines[-1])

    assert payload["action_name"] == "screen_size"
    assert payload["ok"] is True
    assert payload["duration_ms"] >= 0
