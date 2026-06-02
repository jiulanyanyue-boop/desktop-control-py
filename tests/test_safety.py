from pathlib import Path


def _settings(tmp_path: Path):
    from desktop_control_py.config import load_settings

    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[timing]",
                "safe_retry_attempts = 3",
                "",
                "[safety]",
                "block_system_hotkeys = true",
                "block_dangerous_window_ops = true",
                'dangerous_window_titles = ["Task Manager", "Registry Editor"]',
                'allowed_system_hotkeys = ["ctrl+shift+esc"]',
                "",
                "[logging]",
                'log_file = "runtime/app.log"',
                'session_file = "runtime/app.jsonl"',
            ]
        ),
        encoding="utf-8",
    )
    return load_settings(config_path=config_path, project_root=tmp_path)


def test_system_hotkey_is_blocked_when_not_allowlisted(tmp_path: Path) -> None:
    from desktop_control_py.safety import SafetyPolicy

    policy = SafetyPolicy(_settings(tmp_path))

    result = policy.evaluate_hotkey(["alt", "f4"])

    assert result.allowed is False
    assert result.reason_code == "blocked_system_hotkey"


def test_allowlisted_system_hotkey_can_pass(tmp_path: Path) -> None:
    from desktop_control_py.safety import SafetyPolicy

    policy = SafetyPolicy(_settings(tmp_path))

    result = policy.evaluate_hotkey(["ctrl", "shift", "esc"])

    assert result.allowed is True
    assert result.reason_code is None


def test_dangerous_window_operation_is_blocked(tmp_path: Path) -> None:
    from desktop_control_py.safety import SafetyPolicy

    policy = SafetyPolicy(_settings(tmp_path))

    result = policy.evaluate_window_operation("window_focus", "Task Manager")

    assert result.allowed is False
    assert result.reason_code == "blocked_dangerous_window"
