"""MCP 工具命名空间和客户端适配."""

import json
import re
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client

_DISALLOWED_CHARS = re.compile(r"[^a-zA-Z0-9_-]")


def normalize_mcp_name(name: str) -> str:
    """把 MCP server/tool 名称转换为安全工具名片段."""
    return _DISALLOWED_CHARS.sub("_", name)


@dataclass(frozen=True)
class MCPToolSpec:
    """MCP 工具描述."""

    server_name: str
    tool_name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def namespaced_name(self) -> str:
        """返回 LangChain 工具池使用的命名空间化名称."""
        return f"mcp__{normalize_mcp_name(self.server_name)}__{normalize_mcp_name(self.tool_name)}"


class MCPRegistry:
    """保存已发现 MCP 工具的轻量 registry.

    真实 MCP 连接由 MCPClientManager 注入；这个 registry 只负责命名空间和路由，
    便于在单元测试中不用启动外部 server。
    """

    def __init__(self) -> None:
        """初始化工具路由."""
        self._tools: dict[str, MCPToolSpec] = {}

    def register_tool(self, spec: MCPToolSpec) -> None:
        """注册一个 MCP 工具."""
        self._tools[spec.namespaced_name] = spec

    def tools(self) -> list[MCPToolSpec]:
        """返回已注册工具."""
        return [self._tools[name] for name in sorted(self._tools)]

    def get(self, namespaced_name: str) -> MCPToolSpec | None:
        """按命名空间化名称查找工具."""
        return self._tools.get(namespaced_name)


@dataclass(frozen=True)
class MCPServerConfig:
    """MCP server 连接配置."""

    name: str
    transport: str
    command: str | None = None
    args: list[str] | None = None
    env: dict[str, str] | None = None
    url: str | None = None


class MCPClientManager:
    """管理真实 MCP client session 和工具发现."""

    def __init__(self, servers: list[MCPServerConfig]) -> None:
        """保存 server 配置."""
        self.servers = servers
        self.registry = MCPRegistry()
        self._exit_stack = AsyncExitStack()
        self._sessions: dict[str, ClientSession] = {}

    @classmethod
    def from_config_path(cls, config_path: Path) -> "MCPClientManager":
        """从 JSON 配置文件加载 MCP servers."""
        if str(config_path) in {"", "."} or not config_path.is_file():
            return cls([])

        raw = json.loads(config_path.read_text())
        servers_raw = raw.get("servers", raw.get("mcpServers", {}))
        servers: list[MCPServerConfig] = []
        for name, server in servers_raw.items():
            if not isinstance(server, dict):
                continue
            servers.append(
                MCPServerConfig(
                    name=str(name),
                    transport=str(server.get("transport", "stdio")),
                    command=server.get("command"),
                    args=[str(arg) for arg in server.get("args", [])],
                    env={str(key): str(value) for key, value in server.get("env", {}).items()},
                    url=server.get("url"),
                )
            )
        return cls(servers)

    async def discover(self) -> MCPRegistry:
        """连接所有 MCP servers 并发现工具."""
        for server in self.servers:
            session = await self._connect(server)
            await session.initialize()
            tools_result = await session.list_tools()
            for tool in tools_result.tools:
                self.registry.register_tool(
                    MCPToolSpec(
                        server_name=server.name,
                        tool_name=tool.name,
                        description=tool.description or "",
                        input_schema=tool.inputSchema or {},
                    )
                )
        return self.registry

    async def call_tool(self, namespaced_name: str, args: dict[str, Any]) -> str:
        """调用 namespaced MCP tool."""
        spec = self.registry.get(namespaced_name)
        if spec is None:
            return f"unknown mcp tool: {namespaced_name}"
        session = self._sessions.get(spec.server_name)
        if session is None:
            return f"mcp server not connected: {spec.server_name}"

        result = await session.call_tool(spec.tool_name, args)
        return str(result.content)

    async def close(self) -> None:
        """关闭所有 MCP sessions."""
        await self._exit_stack.aclose()
        self._sessions.clear()

    async def _connect(self, server: MCPServerConfig) -> ClientSession:
        """按 transport 建立 MCP ClientSession."""
        if server.name in self._sessions:
            return self._sessions[server.name]

        if server.transport == "stdio":
            if not server.command:
                raise ValueError(f"stdio MCP server missing command: {server.name}")
            read_stream, write_stream = await self._exit_stack.enter_async_context(
                stdio_client(
                    StdioServerParameters(
                        command=server.command,
                        args=server.args or [],
                        env=server.env or None,
                    )
                )
            )
        elif server.transport in {"streamable_http", "http"}:
            if not server.url:
                raise ValueError(f"streamable_http MCP server missing url: {server.name}")
            read_stream, write_stream, _ = await self._exit_stack.enter_async_context(
                streamablehttp_client(server.url)
            )
        else:
            raise ValueError(f"unsupported MCP transport: {server.transport}")

        session = await self._exit_stack.enter_async_context(ClientSession(read_stream, write_stream))
        self._sessions[server.name] = session
        return session
