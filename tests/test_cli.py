from __future__ import annotations

from pathlib import Path


def test_cli_defaults_to_serve_stdio_for_backwards_compatibility(monkeypatch, tmp_path: Path) -> None:
    """验证旧入口无参数时仍按 stdio serve 启动。"""

    from desktop_control_py import cli

    calls: dict[str, object] = {}

    class FakeServer:
        """记录 CLI 传入 transport 的假 MCP server。"""

        def run(self, transport: str) -> None:
            """记录 serve 子命令最终使用的 transport。"""

            calls["transport"] = transport

    def fake_load_settings(config_path: Path | None = None) -> object:
        """记录 CLI 传入的配置路径。"""

        calls["config_path"] = config_path
        return object()

    def fake_create_server(settings: object) -> FakeServer:
        """返回可观测的假 server。"""

        calls["settings"] = settings
        return FakeServer()

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "create_server", fake_create_server)

    assert cli.main([]) == 0
    assert calls["transport"] == "stdio"
    assert calls["config_path"] is None


def test_cli_serve_accepts_config_path(monkeypatch, tmp_path: Path) -> None:
    """验证 serve 子命令会把显式 config 路径传给配置加载器。"""

    from desktop_control_py import cli

    config_path = tmp_path / "custom.toml"
    config_path.write_text("[timing]\nwindow_find_timeout_ms = 99\n", encoding="utf-8")
    calls: dict[str, object] = {}

    class FakeServer:
        """记录 serve 调用参数的假 MCP server。"""

        def run(self, transport: str) -> None:
            """保存 transport 以便断言。"""

            calls["transport"] = transport

    def fake_load_settings(config_path: Path | None = None) -> object:
        """保存配置路径并返回假 settings。"""

        calls["config_path"] = config_path
        return object()

    monkeypatch.setattr(cli, "load_settings", fake_load_settings)
    monkeypatch.setattr(cli, "create_server", lambda settings: FakeServer())

    assert cli.main(["serve", "--transport", "stdio", "--config", str(config_path)]) == 0
    assert calls["transport"] == "stdio"
    assert calls["config_path"] == config_path


def test_cli_check_env_passes_config_path(monkeypatch, tmp_path: Path) -> None:
    """验证 check-env 子命令会把 config 路径传给环境检查流程。"""

    from desktop_control_py import cli

    config_path = tmp_path / "check.toml"
    calls: dict[str, object] = {}

    def fake_run_environment_check(config_path: Path | None = None) -> int:
        """记录环境检查接收到的配置路径。"""

        calls["config_path"] = config_path
        return 0

    monkeypatch.setattr(cli, "run_environment_check", fake_run_environment_check)

    assert cli.main(["check-env", "--config", str(config_path)]) == 0
    assert calls["config_path"] == config_path


def test_cli_smoke_test_passes_config_path(monkeypatch, tmp_path: Path) -> None:
    """验证 smoke-test 子命令会把 config 路径传给真实桌面冒烟流程。"""

    from desktop_control_py import cli

    config_path = tmp_path / "smoke.toml"
    calls: dict[str, object] = {}

    def fake_run_smoke_test(config_path: Path | None = None) -> int:
        """记录冒烟测试接收到的配置路径。"""

        calls["config_path"] = config_path
        return 0

    monkeypatch.setattr(cli, "run_smoke_test", fake_run_smoke_test)

    assert cli.main(["smoke-test", "--config", str(config_path)]) == 0
    assert calls["config_path"] == config_path
