"""定义 MCP 服务入口，并按责任域注册桌面控制工具。"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .backends.protocol import DesktopBackend
from .config import load_settings
from .models import AppSettings
from .service import DesktopService
from .tool_registration import ActionToolRegistrar, AtomicToolRegistrar, BrowserToolRegistrar


class DesktopControlServer:
    """对 FastMCP 做薄包装，统一直接调用时的返回形态。"""

    def __init__(self, mcp: FastMCP) -> None:
        """保存底层 FastMCP 实例，供 run/list/call 统一转发。"""

        self._mcp = mcp

    async def list_tools(self) -> Any:
        """转发到底层 MCP 的工具列表读取。"""

        return await self._mcp.list_tools()

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        """转发到底层 MCP 调用，并优先返回结构化结果包。"""

        result = await self._mcp.call_tool(name, arguments)
        if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], dict):
            return result[1]
        return result

    def run(self, transport: str = "stdio") -> None:
        """按指定传输方式启动底层 MCP 服务。"""

        self._mcp.run(transport=transport)


def create_server(
    settings: AppSettings | None = None,
    backend: DesktopBackend | None = None,
) -> DesktopControlServer:
    """创建并返回完整的桌面控制 MCP 服务实例。"""

    settings = settings or load_settings()
    if backend is None:
        from .backends.win32 import WindowsDesktopBackend

        backend = WindowsDesktopBackend(settings)

    service = DesktopService(settings=settings, backend=backend)
    server = FastMCP(
        name="desktop_control_py",
        instructions=(
            "Windows-only local desktop control MCP. Use computer_observe and computer_step for "
            "observe-act-observe desktop loops. Browser pages use screenshot-first coordinate flow only; "
            "no DOM/UIA/page-text/clipboard capture tools are registered."
        ),
    )

    AtomicToolRegistrar(server=server, service=service).register()
    ActionToolRegistrar(server=server, service=service).register()
    BrowserToolRegistrar(server=server, service=service).register()

    return DesktopControlServer(server)
