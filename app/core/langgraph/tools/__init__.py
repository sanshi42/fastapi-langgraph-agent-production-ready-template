"""用于增强语言模型能力的 LangGraph tools.

本包包含可与 LangGraph 搭配使用的自定义工具，用于扩展语言模型能力。
当前包含网页搜索和其他外部集成工具。
"""

from langchain_core.tools.base import BaseTool

from .agent_runtime import build_agent_runtime_tools, build_mcp_runtime_tools
from .ask_human import ask_human
from .duckduckgo_search import duckduckgo_search_tool

tools: list[BaseTool] = [duckduckgo_search_tool, ask_human, *build_agent_runtime_tools()]


async def refresh_runtime_tools() -> list[BaseTool]:
    """刷新包含 MCP discovered tools 的工具池."""
    global tools
    tools = [duckduckgo_search_tool, ask_human, *build_agent_runtime_tools(), *await build_mcp_runtime_tools()]
    return tools
