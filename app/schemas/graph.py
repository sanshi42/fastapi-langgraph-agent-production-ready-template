"""应用 graph 相关 schema."""

from typing import Annotated

from langgraph.graph.message import add_messages
from pydantic import (
    BaseModel,
    Field,
)


class GraphState(BaseModel):
    """LangGraph Agent/Workflow 的状态定义."""

    messages: Annotated[list, add_messages] = Field(default_factory=list, description="对话中的消息")
    long_term_memory: str = Field(default="", description="对话相关的长期记忆")
