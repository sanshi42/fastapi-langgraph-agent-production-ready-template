"""Agent runtime Postgres-backed 状态模型测试."""

from datetime import UTC, datetime, timedelta

from app.models.agent_runtime import AgentApproval, AgentJob, AgentTask


def test_agent_task_is_scoped_by_user_and_session():
    """Task 状态必须带 user_id 和 session_id 做隔离."""
    task = AgentTask(user_id=7, session_id="s1", subject="Refactor", description="Split tools")

    assert task.user_id == 7
    assert task.session_id == "s1"
    assert task.status == "pending"
    assert task.owner is None


def test_agent_approval_defaults_to_pending():
    """审批记录默认等待用户决策."""
    approval = AgentApproval(
        user_id=7,
        session_id="s1",
        tool_name="bash",
        tool_args={"command": "make test"},
        risk_reason="bash executes shell commands",
    )

    assert approval.status == "pending"
    assert approval.decision is None


def test_agent_job_lease_expiry_detects_claimable_jobs():
    """Lease 过期的 runtime job 可被 worker 重新认领."""
    job = AgentJob(
        user_id=7,
        session_id="s1",
        kind="cron",
        status="running",
        lease_owner="worker-a",
        lease_expires_at=datetime.now(UTC) - timedelta(seconds=1),
    )

    assert job.is_lease_expired(datetime.now(UTC)) is True
