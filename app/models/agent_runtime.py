"""Agent runtime 持久化模型."""

from datetime import UTC, datetime
from typing import Any, ClassVar, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.base import BaseModel


class AgentTask(BaseModel, table=True):
    """按用户和聊天 session 隔离的 Agent task."""

    __tablename__: ClassVar[str] = "agent_tasks"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    subject: str
    description: str = Field(default="")
    status: str = Field(default="pending", index=True)
    owner: Optional[str] = Field(default=None, index=True)
    blocked_by: list[int] = Field(default_factory=list, sa_column=Column(JSON, nullable=False))
    worktree: str = Field(default="")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentWorktree(BaseModel, table=True):
    """Agent 管理的 git worktree 索引."""

    __tablename__: ClassVar[str] = "agent_worktrees"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    name: str = Field(index=True)
    path: str
    branch: str
    task_id: Optional[int] = Field(default=None, index=True)
    status: str = Field(default="active", index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentJob(BaseModel, table=True):
    """可由应用内 worker 租约执行的 runtime job."""

    __tablename__: ClassVar[str] = "agent_jobs"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    kind: str = Field(index=True)
    status: str = Field(default="pending", index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    result: Optional[str] = Field(default=None)
    lease_owner: Optional[str] = Field(default=None, index=True)
    lease_expires_at: Optional[datetime] = Field(default=None, index=True)
    heartbeat_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def is_lease_expired(self, now: datetime) -> bool:
        """判断 job lease 是否已过期."""
        return self.lease_expires_at is not None and self.lease_expires_at <= now


class AgentCron(BaseModel, table=True):
    """持久化 cron prompt."""

    __tablename__: ClassVar[str] = "agent_crons"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    cron: str
    prompt: str
    recurring: bool = Field(default=True)
    durable: bool = Field(default=True)
    status: str = Field(default="active", index=True)
    last_fired_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentTeammate(BaseModel, table=True):
    """持久化 teammate 状态."""

    __tablename__: ClassVar[str] = "agent_teammates"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    name: str = Field(index=True)
    role: str
    status: str = Field(default="working", index=True)
    prompt: str = Field(default="")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentMessage(BaseModel, table=True):
    """teammate 和 lead 之间的 runtime 消息."""

    __tablename__: ClassVar[str] = "agent_messages"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    sender: str = Field(index=True)
    recipient: str = Field(index=True)
    msg_type: str = Field(default="message", index=True)
    content: str
    metadata_: dict[str, Any] = Field(default_factory=dict, sa_column=Column("metadata", JSON, nullable=False))
    read_at: Optional[datetime] = Field(default=None, index=True)


class AgentApproval(BaseModel, table=True):
    """工具执行前的用户审批记录."""

    __tablename__: ClassVar[str] = "agent_approvals"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    tool_name: str = Field(index=True)
    tool_args: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    risk_reason: str
    status: str = Field(default="pending", index=True)
    decision: Optional[str] = Field(default=None)
    decided_at: Optional[datetime] = Field(default=None)


class AgentMCPServer(BaseModel, table=True):
    """MCP server 配置状态."""

    __tablename__: ClassVar[str] = "agent_mcp_servers"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    name: str = Field(index=True)
    transport: str
    config: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    status: str = Field(default="configured", index=True)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class AgentEvent(SQLModel, table=True):
    """Agent runtime append-only 事件."""

    __tablename__: ClassVar[str] = "agent_events"  # pyright: ignore[reportIncompatibleVariableOverride]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    session_id: str = Field(index=True)
    event: str = Field(index=True)
    payload: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON, nullable=False))
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
