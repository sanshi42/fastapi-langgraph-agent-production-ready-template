"""LangGraph 的 human-in-the-loop 确认工具.

本模块提供一个工具，在执行敏感操作前暂停 graph 并向用户请求确认。
"""

from langchain_core.tools import tool
from langgraph.types import interrupt


@tool
def ask_human(question: str) -> str:
    """暂停执行，并在继续前向用户提问.

    当重大操作前需要用户澄清、确认或补充输入时使用，例如删除数据、发送邮件、
    购买或其他不可逆操作。

    Args:
        question: 要询问用户的问题。

    Returns:
        str: 用户回复。
    """
    user_response = interrupt(question)
    return str(user_response)
