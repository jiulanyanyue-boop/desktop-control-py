# desktop-control-py

[简体中文](README.zh-CN.md)

[![CI](https://github.com/jiulanyanyue-boop/desktop-control-py/actions/workflows/ci.yml/badge.svg)](https://github.com/jiulanyanyue-boop/desktop-control-py/actions/workflows/ci.yml)

**Give AI a safe pair of eyes and hands on Windows.**

`desktop-control-py` is a Windows-only MCP server for local desktop control. It
is built for agents that need to observe the real screen, understand the current
desktop context, preflight risky actions, and then use real mouse, keyboard,
window, clipboard, and screenshot primitives under explicit safety rules.

The public package name is `desktop_control_py`. The MCP server name is
`desktop_control_py`.

## Why This Exists

Some useful desktop workflows do not have a clean API. Some browser pages should
not be scraped through DOM or hidden text channels. Some apps only expose a real
window, a real screenshot, and real input events.

This project takes that constraint seriously:

- Observe the desktop first.
- Preflight risky actions before executing them.
- Wrap GUI actions in an observe-act-observe loop when evidence matters.
- Use screenshot-first browser interaction instead of DOM scraping.
- Keep tool calls auditable through local JSONL session logs.
- Stay Windows-only and honest about safety boundaries.

## Highlights

### One-Call Desktop Snapshot

`desktop_snapshot` gives an agent the current desktop context in one read-only
call: screen size, cursor position, active window, visible windows, clipboard
text availability, and optional screenshot.

It does not move the mouse, type, click, focus a window, or read clipboard text.
Screenshots are opt-in because they can be large and privacy-sensitive.

### Computer Use-Style Observe/Step Loop

`computer_observe` is the richer observation tool for visual agents. It returns
the desktop context plus a coordinate contract, screen metrics, optional base64
screenshot data, and an optional screenshot artifact saved under `runtime/`.

`computer_step` wraps a scoped desktop action in an observe-act-observe result.
It supports `click`, `double_click`, `type`, and `hotkey` actions, with optional
before/after observations and screenshot artifacts. Text input results are
redacted to length metadata instead of echoing typed text back into the tool
response.

This is a Computer Use-style loop for Windows MCP agents. It is not a claim of
compatibility with any proprietary Codex protocol.

### Safety Preflight Before Real Input

`safety_check` lets an agent ask whether a hotkey or window operation would be
blocked by the configured safety policy before touching the desktop.

Examples:

- Check whether `alt+f4` would be blocked.
- Check whether a window operation against `Task Manager` would be blocked.
- Inspect the normalized hotkey and reason code returned by the policy.

This is a guardrail and a preflight tool, not a full sandbox.

### Screenshot-First Browser Control

`browser_capture` and `browser_click` focus a real Chrome/Edge/browser window,
capture the visible pixels, and click absolute screen coordinates. They do not
read DOM, UIA text, hidden page text, or browser clipboard content.

This keeps browser interaction compatible with visual-agent workflows: look at
the screenshot, decide a coordinate, click, then capture again.

### Queryable Local Audit Trail

`audit_recent` reads the tail of the structured JSONL session log so users and
agents can inspect recent desktop actions, durations, warnings, and failure
codes from the MCP server itself.

Auditability is not just "there is a log file"; it is a first-class MCP tool.

### Stable Real Desktop Primitives

The server also exposes stable atomic tools for screenshots, mouse, keyboard,
windows, clipboard, and higher-level `action_*` workflows. Existing tool names
are kept stable for compatibility.

## Agent Workflow

A practical agent loop looks like this:

```text
computer_observe
  -> safety_check
  -> computer_step(action=click/type/hotkey, observe_before=true, observe_after=true)
  -> audit_recent
```

For browser-only work, `browser_capture -> browser_click -> audit_recent` remains
the tighter screenshot-first path. For backward compatibility, the older
`desktop_snapshot -> action_*` loop remains available.

## Quickstart

Requirements:

- Windows.
- Python 3.11 or newer.
- `uv` for the recommended workflow.

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

Check the active environment:

```powershell
uv run desktop-control-py check-env
```

The legacy Windows launchers remain as thin wrappers around the CLI:

```powershell
.\启动桌面控制MCP.bat
.\检查桌面控制环境.bat
.\运行桌面控制冒烟测试.bat
```

Launcher resolution order:

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

## MCP Tool Surface

Agent-friendly observation and governance tools:

- `desktop_snapshot`
- `computer_observe`
- `computer_step`
- `safety_check`
- `audit_recent`

Atomic desktop tools:

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

## Configuration

The default config is `config/default.toml`.

It controls:

- Timing and retry settings.
- Hotkey and dangerous-window safety policy.
- Runtime log and session audit paths.
- Screenshot format, quality, and grayscale defaults.

Generated runtime files are written to `runtime/` and are ignored by git except
for `runtime/.gitkeep`. Screenshot artifacts created by `computer_observe` and
`computer_step` are saved under `runtime/screenshots/`.

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

The smoke test is intentionally not part of CI because it requires an unlocked,
interactive Windows desktop.

## Safety Boundaries

This server is local and privileged. It can control your Windows desktop through
real input events. Use it only in trusted local environments.

Safety policy focuses on:

- Blocking risky system hotkeys unless explicitly allowed.
- Blocking dangerous window operations by title.
- Keeping browser interaction screenshot-first.
- Returning explicit coordinate-space metadata for visual clicks.
- Saving optional screenshot artifacts for review and traceability.
- Preserving audit logs for tool calls.
- Making observation and safety preflight available as explicit MCP tools.

This project intentionally does not provide:

- DOM scraping.
- CAPTCHA bypass.
- Hidden page text extraction.
- Browser clipboard scraping.
- Job submission automation.
- Background credential extraction.
- Cross-platform desktop automation.

## Architecture

`DesktopService` is the thin service facade. It owns the shared settings,
backend, action engine, and safety policy.

`ActionFlow` handles high-level `action_*` workflows such as optional window
focus before click/type/hotkey/screenshot.

`ComputerFlow` handles the richer `computer_observe` and `computer_step`
observe-act-observe workflows for visual desktop agents.

`BrowserFlow` handles screenshot-first browser capture and coordinate click
flows. It uses real browser process/title matching and does not read DOM, UIA,
page text, or clipboard content.

`ScreenshotArtifactStore` saves Computer Use-style observation screenshots under
`runtime/screenshots/` so sessions can be reviewed without relying only on large
base64 payloads.

`tool_registration.py` registers MCP tools by responsibility:

- `AtomicToolRegistrar`
- `ActionToolRegistrar`
- `BrowserToolRegistrar`

`WindowsDesktopBackend` contains the Win32 implementation behind the typed
`DesktopBackend` protocol.
