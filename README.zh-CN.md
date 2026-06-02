# desktop-control-py

[English](README.md)

[![CI](https://github.com/jiulanyanyue-boop/desktop-control-py/actions/workflows/ci.yml/badge.svg)](https://github.com/jiulanyanyue-boop/desktop-control-py/actions/workflows/ci.yml)

**给 AI 一双带护栏、可审计的 Windows 手和眼。**

`desktop-control-py` 是一个 Windows-only 本地桌面控制 MCP server。它面向需要操作真实桌面的 agent：先观察屏幕和窗口状态，再预检高风险动作，然后通过真实鼠标、键盘、窗口、剪贴板和截图能力执行操作。

公开包名保持为 `desktop_control_py`，MCP server 名称保持为 `desktop_control_py`。

## 为什么需要它

很多有价值的桌面工作流没有干净 API。有些浏览器页面不应该通过 DOM 或隐藏文本通道抓取。有些桌面应用只暴露真实窗口、真实截图和真实输入事件。

这个项目接受这个现实，并把边界说清楚：

- 先观察桌面，再行动。
- 执行高风险动作前先做安全预检。
- 浏览器交互采用 screenshot-first，而不是 DOM scraping。
- 工具调用写入本地 JSONL session audit。
- 只做 Windows，并且不假装它是跨平台沙箱。

## 亮点

### 一次调用拿桌面上下文

`desktop_snapshot` 是面向 agent 的只读桌面快照工具。一次调用返回屏幕尺寸、鼠标位置、活动窗口、可见窗口列表、剪贴板是否包含文本，以及可选截图。

默认不会移动鼠标、输入、点击、聚焦窗口，也不会读取剪贴板文本。截图需要显式开启，因为截图 payload 较大且可能包含隐私信息。

### 真实输入前的安全预检

`safety_check` 可以在真实触碰桌面前检查某个热键或窗口操作是否会被当前安全策略拦截。

典型用途：

- 检查 `alt+f4` 是否会被拦截。
- 检查针对 `Task Manager` 的窗口操作是否会被拦截。
- 查看策略返回的 normalized hotkey、reason code 和 message。

它是 guardrail 和 preflight tool，不是完整安全沙箱。

### Screenshot-First 浏览器控制

`browser_capture` 和 `browser_click` 会聚焦真实 Chrome/Edge/browser 窗口，截取可见像素，再点击绝对屏幕坐标。它们不读取 DOM、UIA、隐藏页面文本或浏览器剪贴板内容。

这适合视觉 agent 工作流：看截图，判断坐标，点击，再截图确认。

### 可查询的本地审计记录

`audit_recent` 可以从 MCP server 内部读取最近的结构化 JSONL session audit，查看近期桌面动作、耗时、warnings 和失败码。

审计不只是“写了个日志文件”，而是一个可以被 MCP 查询的能力。

### 稳定的真实桌面原语

项目还暴露截图、鼠标、键盘、窗口、剪贴板和高阶 `action_*` 工作流。现有 MCP 工具名保持稳定，方便已有客户端继续使用。

## Agent 工作流

一个实用的 agent loop 可以是：

```text
desktop_snapshot
  -> safety_check
  -> browser_capture 或 action_capture_screen
  -> browser_click / action_click / action_type / keyboard_hotkey
  -> audit_recent
```

核心原则很简单：先观察，再预检，再操作，最后检查发生了什么。

## 快速开始

要求：

- Windows。
- Python 3.11 或更新版本。
- 推荐使用 `uv`。

安装依赖：

```powershell
uv sync --extra dev
```

启动 MCP server：

```powershell
uv run desktop-control-py serve --transport stdio
```

使用配置覆盖：

```powershell
uv run desktop-control-py serve --transport stdio --config .\config\default.toml
```

检查当前环境：

```powershell
uv run desktop-control-py check-env
```

旧 Windows 启动器继续保留，但只作为 CLI 薄包装：

```powershell
.\启动桌面控制MCP.bat
.\检查桌面控制环境.bat
.\运行桌面控制冒烟测试.bat
```

启动器解析顺序固定：

1. 环境变量 `DESKTOP_CONTROL_PY_PYTHON` 和 `DESKTOP_CONTROL_PY_UV`。
2. `PATH` 中的 `uv` 和 `python`。
3. 找不到时输出明确 setup 提示并失败。

## 命令参考

```powershell
desktop-control-py serve [--transport stdio] [--config <path>]
desktop-control-py check-env [--config <path>]
desktop-control-py smoke-test [--config <path>]
```

`serve` 启动 MCP server。

`check-env` 检查 Python、平台、配置加载和核心依赖。

`smoke-test` 是真实桌面验证，会移动鼠标、向 Notepad 输入文本、读取剪贴板、操作窗口、截图，并在已有浏览器窗口时尝试浏览器截图。

## MCP 工具面

面向 agent 的观察和治理工具：

- `desktop_snapshot`
- `safety_check`
- `audit_recent`

原子桌面工具：

- `screen_capture`, `screen_size`, `cursor_position`
- `mouse_move`, `mouse_click`, `mouse_double_click`, `mouse_drag`, `mouse_scroll`
- `keyboard_type`, `keyboard_press`, `keyboard_hold`, `keyboard_hotkey`
- `window_list`, `window_active`, `window_focus`, `window_move`, `window_resize`
- `clipboard_get`, `clipboard_set`, `clipboard_clear`, `clipboard_has_text`

高阶 action 工具：

- `action_focus_window`, `action_wait_window`
- `action_click`, `action_double_click`, `action_type`, `action_hotkey`
- `action_capture_screen`

浏览器截图工具：

- `browser_capture`
- `browser_click`

浏览器默认匹配提示为通用写法：`Chrome|Edge|Browser`。

## 配置

默认配置文件是 `config/default.toml`。

配置项包括：

- 动作时间与重试参数。
- 热键和危险窗口安全策略。
- runtime 日志与 session audit 路径。
- 截图格式、质量和灰度默认值。

生成的运行时文件写入 `runtime/`，除 `runtime/.gitkeep` 外均被 git 忽略。

## 验证

CI-safe 验证：

```powershell
uv run --extra dev python -m pytest -q
uv run --extra dev python -m build
uv run --extra dev ruff check .
```

真实机器手动验证：

```powershell
desktop-control-py check-env
desktop-control-py smoke-test
desktop-control-py serve --transport stdio
```

冒烟测试不会进入 CI，因为它需要未锁屏、可交互的 Windows 桌面。

## 安全边界

这个 server 是本地高权限自动化工具，可以通过真实输入事件控制 Windows 桌面。只应在可信本地环境中使用。

安全策略重点：

- 默认阻止高风险系统热键。
- 默认阻止危险窗口标题上的窗口操作。
- 浏览器交互保持 screenshot-first。
- 保留工具调用审计日志。
- 把观察和安全预检暴露为明确 MCP 工具。

本项目不提供：

- DOM 抓取。
- CAPTCHA 绕过。
- 隐藏页面文本提取。
- 浏览器剪贴板抓取。
- 职位投递自动化。
- 后台凭据提取。
- 跨平台桌面自动化。

## 架构

`DesktopService` 是薄服务门面，负责持有 settings、backend、action engine 和 safety policy。

`ActionFlow` 负责 `action_*` 复合动作，例如点击、输入、热键、截图前的可选窗口聚焦。

`BrowserFlow` 负责浏览器截图和坐标点击。它只依赖真实窗口/进程匹配与截图，不读取 DOM、UIA、页面文本或剪贴板。

`tool_registration.py` 按责任域注册 MCP 工具：

- `AtomicToolRegistrar`
- `ActionToolRegistrar`
- `BrowserToolRegistrar`

`WindowsDesktopBackend` 是 Win32 实现，并满足 typed `DesktopBackend` protocol。
