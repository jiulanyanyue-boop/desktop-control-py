from __future__ import annotations

from pathlib import Path


def _settings(tmp_path: Path):
    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[timing]",
                "safe_retry_attempts = 3",
                "safe_retry_interval_ms = 0",
                "",
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/app.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def test_retryable_action_retries_until_success(tmp_path: Path) -> None:
    from desktop_control_py.engine import ActionEngine

    settings = _settings(tmp_path)
    engine = ActionEngine(settings=settings)
    attempts = {"count": 0}

    def flaky_action() -> dict:
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise RuntimeError("transient")
        return {"value": "ok"}

    result = engine.execute(
        action_name="screen_size",
        action=flaky_action,
        retryable=True,
    )

    assert attempts["count"] == 3
    assert result.ok is True
    assert result.data == {"value": "ok"}
    assert len(result.warnings) == 2


def test_non_retryable_action_fails_fast(tmp_path: Path) -> None:
    from desktop_control_py.engine import ActionEngine
    from desktop_control_py.errors import DesktopControlError

    settings = _settings(tmp_path)
    engine = ActionEngine(settings=settings)

    def always_fail() -> dict:
        raise RuntimeError("boom")

    try:
        engine.execute(
            action_name="mouse_click",
            action=always_fail,
            retryable=False,
        )
    except DesktopControlError as exc:
        assert exc.code == "action_failed"
    else:
        raise AssertionError("Expected DesktopControlError")
