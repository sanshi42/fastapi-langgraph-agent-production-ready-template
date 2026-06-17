"""Agent runtime API schema."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RuntimeVisibility(BaseModel):
    """前端 Settings 可展示的 runtime 配置."""

    approval_enabled: bool = Field(..., description="工具审批是否启用")
    worker_enabled: bool = Field(..., description="应用内 runtime worker 是否启用")
    workspace_root: str = Field(..., description="Agent Workspace 根目录")


class RuntimeTaskSummary(BaseModel):
    """Task Board 条目摘要."""

    id: int | None = Field(default=None, description="Task ID")
    subject: str = Field(..., description="Task 主题")
    description: str = Field(default="", description="Task 描述")
    status: str = Field(..., description="Task 状态")
    owner: str | None = Field(default=None, description="Task owner")
    updated_at: datetime = Field(..., description="更新时间")


class RuntimeJobSummary(BaseModel):
    """Runtime job 摘要."""

    id: int | None = Field(default=None, description="Job ID")
    kind: str = Field(..., description="Job 类型")
    status: str = Field(..., description="Job 状态")
    result: str | None = Field(default=None, description="Job 结果")
    updated_at: datetime = Field(..., description="更新时间")


class RuntimeCronSummary(BaseModel):
    """Cron prompt 摘要."""

    id: int | None = Field(default=None, description="Cron ID")
    cron: str = Field(..., description="五字段 cron 表达式")
    prompt: str = Field(..., description="触发时执行的 prompt")
    recurring: bool = Field(..., description="是否重复执行")
    status: str = Field(..., description="Cron 状态")
    last_fired_at: datetime | None = Field(default=None, description="最近触发时间")
    updated_at: datetime = Field(..., description="更新时间")


class RuntimeTeammateSummary(BaseModel):
    """Teammate 状态摘要."""

    id: int | None = Field(default=None, description="Teammate ID")
    name: str = Field(..., description="Teammate 名称")
    role: str = Field(..., description="Teammate 角色")
    status: str = Field(..., description="Teammate 状态")
    updated_at: datetime = Field(..., description="更新时间")


class RuntimeWorktreeSummary(BaseModel):
    """Worktree 状态摘要."""

    id: int | None = Field(default=None, description="Worktree ID")
    name: str = Field(..., description="Worktree 名称")
    path: str = Field(..., description="Worktree 路径")
    branch: str = Field(..., description="Git branch")
    task_id: int | None = Field(default=None, description="关联 task ID")
    status: str = Field(..., description="Worktree 状态")
    updated_at: datetime = Field(..., description="更新时间")


class RuntimeApprovalSummary(BaseModel):
    """Pending Approval 状态摘要."""

    id: int | None = Field(default=None, description="Approval ID")
    tool_name: str = Field(..., description="工具名")
    tool_args: dict[str, Any] = Field(default_factory=dict, description="工具参数")
    risk_reason: str = Field(..., description="风险原因")
    status: str = Field(..., description="审批状态")
    decision: str | None = Field(default=None, description="审批决定")
    decided_at: datetime | None = Field(default=None, description="决定时间")
    created_at: datetime = Field(..., description="创建时间")


class RuntimeStateResponse(BaseModel):
    """当前 session 的 Agent runtime 状态."""

    session_id: str = Field(..., description="当前聊天 session ID")
    runtime: RuntimeVisibility
    tasks: list[RuntimeTaskSummary] = Field(default_factory=list)
    jobs: list[RuntimeJobSummary] = Field(default_factory=list)
    crons: list[RuntimeCronSummary] = Field(default_factory=list)
    teammates: list[RuntimeTeammateSummary] = Field(default_factory=list)
    worktrees: list[RuntimeWorktreeSummary] = Field(default_factory=list)
    approvals: list[RuntimeApprovalSummary] = Field(default_factory=list)
