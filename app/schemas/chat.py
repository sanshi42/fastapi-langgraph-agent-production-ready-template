"""应用聊天相关 schema."""

import re
from typing import (
    List,
    Literal,
)

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)

from app.schemas.base import BaseResponse


class Message(BaseModel):
    """聊天端点使用的消息模型.

    Attributes:
        role: 消息发送者角色（user 或 assistant）。
        content: 消息内容。
    """

    model_config = {"extra": "ignore"}

    role: Literal["user", "assistant", "system"] = Field(..., description="消息发送者角色")
    content: str = Field(..., description="消息内容", min_length=1, max_length=3000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        """校验消息内容.

        Args:
            v: 待校验内容。

        Returns:
            str: 校验通过的内容。

        Raises:
            ValueError: 内容包含不允许的模式时抛出。
        """
        # 检查潜在有害内容。
        if re.search(r"<script.*?>.*?</script>", v, re.IGNORECASE | re.DOTALL):
            raise ValueError("Content contains potentially harmful script tags")

        # 检查空字节。
        if "\0" in v:
            raise ValueError("Content contains null bytes")

        return v


class ChatRequest(BaseModel):
    """聊天端点请求模型.

    Attributes:
        messages: 对话中的消息列表。
    """

    messages: List[Message] = Field(
        ...,
        description="对话中的消息列表",
        min_length=1,
    )


class ChatResponse(BaseResponse):
    """聊天端点响应模型.

    Attributes:
        messages: 对话中的消息列表。
        status: Agent runtime 的结构化状态。
        approval_id: 等待用户审批的记录 ID。
        tool_name: 触发审批或运行状态的工具名。
        risk_reason: 工具命中审批策略的原因。
        job_id: 后台 runtime job ID。
    """

    messages: List[Message] = Field(..., description="对话中的消息列表")
    status: Literal["completed", "pending_approval", "running", "error"] = Field(
        default="completed",
        description="Agent runtime 状态",
    )
    approval_id: str | None = Field(default=None, description="待审批记录 ID")
    tool_name: str | None = Field(default=None, description="相关工具名")
    risk_reason: str | None = Field(default=None, description="审批或风险原因")
    job_id: str | None = Field(default=None, description="后台 runtime job ID")


class StreamResponse(BaseResponse):
    """流式聊天端点响应模型.

    Attributes:
        content: 当前 chunk 内容。
        done: 流是否已结束。
    """

    content: str = Field(default="", description="当前 chunk 内容")
    done: bool = Field(default=False, description="流是否已结束")
    status: Literal["completed", "pending_approval", "running", "error"] = Field(
        default="running",
        description="Agent runtime 状态",
    )
    approval_id: str | None = Field(default=None, description="待审批记录 ID")
    tool_name: str | None = Field(default=None, description="相关工具名")
    risk_reason: str | None = Field(default=None, description="审批或风险原因")
    job_id: str | None = Field(default=None, description="后台 runtime job ID")


class SessionTitle(BaseModel):
    """生成 session 标题时使用的结构化输出 schema."""

    title: str = Field(
        ...,
        min_length=1,
        max_length=60,
    )

    @field_validator("title")
    @classmethod
    def _normalize(cls, v: str) -> str:
        v = " ".join(v.split()).strip(" \"'`.,:;!?-")
        if not v:
            raise ValueError("empty title after normalization")
        return v
