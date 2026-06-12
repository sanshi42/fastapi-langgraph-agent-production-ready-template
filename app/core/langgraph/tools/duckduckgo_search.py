"""LangGraph 使用的 DuckDuckGo 搜索工具.

本模块提供可被 LangGraph 调用的 DuckDuckGo 搜索工具，用于执行网页搜索。
它最多返回 10 条搜索结果，并优雅处理错误。
"""

from langchain_community.tools import DuckDuckGoSearchResults

duckduckgo_search_tool = DuckDuckGoSearchResults(num_results=10, handle_tool_error=True)
