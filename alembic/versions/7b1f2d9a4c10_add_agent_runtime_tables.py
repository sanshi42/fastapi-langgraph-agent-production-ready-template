"""增加 Agent runtime 状态表.

Revision ID: 7b1f2d9a4c10
Revises: b25d38b0cd7c
Create Date: 2026-06-15 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "7b1f2d9a4c10"  # pragma: allowlist secret
down_revision: Union[str, Sequence[str], None] = "b25d38b0cd7c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _scope_columns() -> list[sa.Column]:
    """返回 Agent runtime 表共享的隔离字段."""
    return [
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
    ]


def upgrade() -> None:
    """升级 schema."""
    op.create_table(
        "agent_tasks",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("blocked_by", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("worktree", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_tasks_scope", "agent_tasks", ["user_id", "session_id"])
    op.create_index("ix_agent_tasks_status", "agent_tasks", ["status"])

    op.create_table(
        "agent_worktrees",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("branch", sa.String(), nullable=False),
        sa.Column("task_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_worktrees_scope", "agent_worktrees", ["user_id", "session_id"])
    op.create_index("ix_agent_worktrees_name", "agent_worktrees", ["name"])

    op.create_table(
        "agent_jobs",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("lease_owner", sa.String(), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_jobs_scope", "agent_jobs", ["user_id", "session_id"])
    op.create_index("ix_agent_jobs_status", "agent_jobs", ["status"])
    op.create_index("ix_agent_jobs_lease_expires_at", "agent_jobs", ["lease_expires_at"])

    op.create_table(
        "agent_crons",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("cron", sa.String(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("recurring", sa.Boolean(), nullable=False),
        sa.Column("durable", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("last_fired_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_crons_scope", "agent_crons", ["user_id", "session_id"])
    op.create_index("ix_agent_crons_status", "agent_crons", ["status"])

    op.create_table(
        "agent_teammates",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("prompt", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_teammates_scope", "agent_teammates", ["user_id", "session_id"])

    op.create_table(
        "agent_messages",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("sender", sa.String(), nullable=False),
        sa.Column("recipient", sa.String(), nullable=False),
        sa.Column("msg_type", sa.String(), nullable=False),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("read_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_messages_scope", "agent_messages", ["user_id", "session_id"])
    op.create_index("ix_agent_messages_recipient", "agent_messages", ["recipient"])

    op.create_table(
        "agent_approvals",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("tool_args", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_reason", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("decision", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_approvals_scope", "agent_approvals", ["user_id", "session_id"])
    op.create_index("ix_agent_approvals_status", "agent_approvals", ["status"])

    op.create_table(
        "agent_mcp_servers",
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("transport", sa.String(), nullable=False),
        sa.Column("config", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_mcp_servers_scope", "agent_mcp_servers", ["user_id", "session_id"])

    op.create_table(
        "agent_events",
        sa.Column("id", sa.Integer(), nullable=False),
        *_scope_columns(),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_events_scope", "agent_events", ["user_id", "session_id"])
    op.create_index("ix_agent_events_event", "agent_events", ["event"])


def downgrade() -> None:
    """降级 schema."""
    for table_name in [
        "agent_events",
        "agent_mcp_servers",
        "agent_approvals",
        "agent_messages",
        "agent_teammates",
        "agent_crons",
        "agent_jobs",
        "agent_worktrees",
        "agent_tasks",
    ]:
        op.drop_table(table_name)
