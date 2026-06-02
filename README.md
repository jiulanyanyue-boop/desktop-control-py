# desktop-control-py

[简体中文](README.zh-CN.md)

`desktop-control-py` is a Windows-only desktop control MCP server implemented in
Python. It exposes local desktop primitives such as screenshots, mouse input,
keyboard input, window management, clipboard operations, and screenshot-first
browser coordinate flows.

The package name is `desktop_control_py`. The MCP server name is
`desktop_control_py`.

## What It Is

- A local MCP server for Windows desktop control.
- A screenshot-first browser interaction layer: capture a real browser window,
  inspect the screenshot externally, then click absolute screen coordinates.
- A small Python package with CLI entry points for serving, environment checks,
  and real-machine smoke testing.
- An auditable local automation server that writes runtime logs and session
  audit files under `runtime/`.

## Non-Goals

This project intentionally does not provide:

- DOM scraping.
- CAPTCHA bypass.
- Hidden page text extraction.
- Browser clipboard scraping.
- Job submission automation.
- Background credential extraction.
- Cross-platform desktop automation.

## Tool Surface

Existing MCP tool names are kept stable.

Atomic tools:

- `screen_capture`, `screen_size`, `cursor_position`
- `mouse_move`, `mouse_click`, `mouse_double_click`, `mouse_drag`, `mouse_scroll`
- `keyboard_type`, `keyboard_press`, `keyboard_hold`, `keyboard_hotkey`
- `window_list`, `window_active`, `window_focus`, `window_move`, `window_resize`
- `clipboard_get`, `clipboard_set`, `clipboard_clear`, `clipboard_has_text`

High-level action tools:

- `action_focus_window`, `action_wait_window`
- `action_click`, `action_double_click`, `action_type`, `action_hotkey`
- `action_capture_screen`

Browser screenshot tools:

- `browser_capture`
- `browser_click`

Browser defaults use generic browser wording: `Chrome|Edge|Browser`.

## Architecture

`DesktopService` is the thin service facade. It owns the shared settings,
backend, action engine, and safety policy.

`ActionFlow` handles high-level `action_*` workflows such as optional window
focus before click/type/hotkey/screenshot.

`BrowserFlow` handles screenshot-first browser capture and coordinate click
flows. It uses real browser process/title matching and does not read DOM, UIA,
page text, or clipboard content.

`tool_registration.py` registers MCP tools by responsibility:

- `AtomicToolRegistrar`
- `ActionToolRegistrar`
- `BrowserToolRegistrar`

`WindowsDesktopBackend` contains the Win32 implementation behind the typed
`DesktopBackend` protocol.

## Install

Requirements:

- Windows.
- Python 3.11 or newer.
- `uv` for the recommended development workflow.

Install dependencies:

```powershell
uv sync --extra dev
```

Run the MCP server:

```powershell
uv run desktop-control-py serve --transport stdio
```

Run with a config override:

```powershell
uv run desktop-control-py serve --transport stdio --config .\config\default.toml
```

The legacy `.bat` launchers remain as thin Windows wrappers around the CLI:

```powershell
.\启动桌面控制MCP.bat
.\检查桌面控制环境.bat
.\运行桌面控制冒烟测试.bat
```

The launchers resolve dependencies in this order:

1. `DESKTOP_CONTROL_PY_PYTHON` and `DESKTOP_CONTROL_PY_UV`.
2. `uv` and `python` from `PATH`.
3. A clear setup failure message.

## Command Reference

```powershell
desktop-control-py serve [--transport stdio] [--config <path>]
desktop-control-py check-env [--config <path>]
desktop-control-py smoke-test [--config <path>]
```

`serve` starts the MCP server.

`check-env` validates Python, platform, config loading, and required runtime
modules.

`smoke-test` is a real-machine test. It can move the mouse, type into Notepad,
read the clipboard, manipulate a window, capture the screen, and try a browser
screenshot capture if a browser is already open.

## Validation

CI-safe validation:

```powershell
uv run --extra dev python -m pytest -q
uv run --extra dev python -m build
uv run --extra dev ruff check .
```

Manual real-machine validation:

```powershell
desktop-control-py check-env
desktop-control-py smoke-test
desktop-control-py serve --transport stdio
```

The smoke test is intentionally not part of CI because it requires an unlocked
interactive Windows desktop.

## Configuration

The default config is `config/default.toml`.

It controls:

- Timing and retry settings.
- Hotkey and dangerous-window safety policy.
- Runtime log and session audit paths.
- Screenshot format, quality, and grayscale defaults.

Generated runtime files are written to `runtime/` and are ignored by git except
for `runtime/.gitkeep`.

## Safety

This server is local and privileged. It can control your Windows desktop through
real input events. Use it only in trusted local environments.

Safety policy focuses on:

- Blocking risky system hotkeys unless explicitly allowed.
- Blocking dangerous window operations by title.
- Keeping browser interaction screenshot-first.
- Preserving audit logs for tool calls.
