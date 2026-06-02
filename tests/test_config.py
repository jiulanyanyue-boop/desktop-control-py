from pathlib import Path


def test_load_settings_reads_toml_and_resolves_runtime_paths(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.toml"
    config_path.write_text(
        "\n".join(
            [
                "[timing]",
                "safe_retry_attempts = 5",
                "",
                "[logging]",
                'log_file = "runtime/custom.log"',
                'session_file = "runtime/custom.jsonl"',
            ]
        ),
        encoding="utf-8",
    )

    from desktop_control_py.config import load_settings

    settings = load_settings(config_path=config_path, project_root=tmp_path)

    assert settings.timing.safe_retry_attempts == 5
    assert settings.logging.log_file == tmp_path / "runtime" / "custom.log"
    assert settings.logging.session_file == tmp_path / "runtime" / "custom.jsonl"


def test_load_settings_uses_default_config_when_path_is_omitted(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "default.toml").write_text(
        "\n".join(
            [
                "[timing]",
                "window_find_timeout_ms = 2222",
                "",
                "[logging]",
                'log_file = "runtime/default.log"',
                'session_file = "runtime/default.jsonl"',
            ]
        ),
        encoding="utf-8",
    )

    from desktop_control_py.config import load_settings

    settings = load_settings(project_root=project_root)

    assert settings.timing.window_find_timeout_ms == 2222
    assert settings.logging.log_file == project_root / "runtime" / "default.log"
    assert settings.logging.session_file == project_root / "runtime" / "default.jsonl"
