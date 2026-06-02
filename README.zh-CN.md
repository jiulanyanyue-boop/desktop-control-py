# desktop-control-py

[English](README.md)

`desktop-control-py` 是一个仅面向 Windows 的本地桌面控制 MCP server，使用
Python 实现。它暴露截图、鼠标、键盘、窗口、剪贴板，以及基于截图的浏览器坐标流。

包名保持为 `desktop_control_py`，MCP server 名称保持为 `desktop_control_py`。

## 项目定位

- Windows-only 本地桌面控制 MCP。
- 浏览器交互采用 screenshot-first：先截取真实浏览器窗口，再由外部模型判断坐标，最后点击绝对屏幕坐标。
- 提供可安装的 Python CLI：启动服务、检查环境、执行真实桌面冒烟测试。
- 运行日志和 session audit 文件写入 `runtime/`。

## 非目标

本项目不提供：

- DOM 抓取。
- CAPTCHA 绕过。
- 隐藏页面文本提取。
- 浏览器剪贴板抓取。
- 职位投递自动化。
- 后台凭据提取。
- 跨平台桌面自动化。

## MCP 工具面

现有 MCP 工具名保持稳定。

原子工具：

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

浏览器公开默认匹配提示为通用写法：`Chrome|Edge|Browser`。

## 架构

`DesktopService` 是薄服务门面，负责持有 settings、backend、action engine 和 safety policy。

`ActionFlow` 负责 `action_*` 复合动作，例如点击、输入、热键、截图前的可选窗口聚焦。

`BrowserFlow` 负责浏览器截图和坐标点击。它只依赖真实窗口/进程匹配与截图，不读取 DOM、UIA、页面文本或剪贴板。

`tool_registration.py` 按责任域注册 MCP 工具：

- `AtomicToolRegistrar`
- `ActionToolRegistrar`
- `BrowserToolRegistrar`

`WindowsDesktopBackend` 是 Win32 实现，并满足 typed `DesktopBackend` protocol。

## 安装与启动

要求：

- Windows。
- Python 3.11 或更新版本。
- 推荐使用 `uv` 管理开发环境。

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

旧 `.bat` 启动器继续保留，但只作为 CLI 薄包装：

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

## 配置

默认配置文件是 `config/default.toml`。

配置项包括：

- 动作时间与重试参数。
- 热键和危险窗口安全策略。
- runtime 日志与 session audit 路径。
- 截图格式、质量和灰度默认值。

生成的运行时文件写入 `runtime/`，除 `runtime/.gitkeep` 外均被 git 忽略。

## 安全边界

这个 server 是本地高权限自动化工具，可以通过真实输入事件控制 Windows 桌面。只应在可信本地环境中使用。

安全策略重点：

- 默认阻止高风险系统热键。
- 默认阻止危险窗口标题上的窗口操作。
- 浏览器交互保持 screenshot-first。
- 保留工具调用审计日志。
