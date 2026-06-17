"""Agent runtime 持久化服务测试."""

import json
from datetime import UTC, datetime, timedelta

from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.agent_runtime.store import AgentRuntimeStore
from app.agent_runtime.runtime import AgentRuntime
from app.agent_runtime.worker import AgentRuntimeWorker
from app.models.agent_runtime import AgentJob


def _store() -> AgentRuntimeStore:
    """创建基于内存数据库的 runtime store."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return AgentRuntimeStore(engine=engine)


def test_store_scopes_tasks_by_user_and_session():
    """Task board 查询必须按 user_id + session_id 隔离."""
    store = _store()
    store.create_task(user_id=1, session_id="s1", subject="One")
    store.create_task(user_id=2, session_id="s1", subject="Two")
    store.create_task(user_id=1, session_id="s2", subject="Three")

    tasks = store.list_tasks(user_id=1, session_id="s1")

    assert [task.subject for task in tasks] == ["One"]


def test_store_records_and_decides_approvals():
    """Pending Approval 应能持久化并记录最终决策."""
    store = _store()

    approval = store.create_approval(
        user_id=7,
        session_id="s1",
        tool_name="write_file",
        tool_args={"path": "a.txt"},
        risk_reason="write_file modifies workspace files",
    )
    decided = store.decide_approval(
        user_id=7,
        session_id="s1",
        approval_id=approval.id or 0,
        decision="approved",
    )

    assert approval.status == "pending"
    assert decided is not None
    assert decided.status == "decided"
    assert decided.decision == "approved"
    assert decided.decided_at is not None


def test_store_lists_approvals_by_user_and_session():
    """Approval 列表查询必须按 user_id + session_id 隔离."""
    store = _store()
    first = store.create_approval(
        user_id=7,
        session_id="s1",
        tool_name="write_file",
        tool_args={"path": "a.txt"},
        risk_reason="write_file modifies workspace files",
    )
    second = store.create_approval(
        user_id=7,
        session_id="s1",
        tool_name="bash",
        tool_args={"command": "npm run build"},
        risk_reason="bash may change workspace state",
    )
    store.create_approval(
        user_id=8,
        session_id="s1",
        tool_name="write_file",
        tool_args={"path": "hidden.txt"},
        risk_reason="write_file modifies workspace files",
    )
    store.create_approval(
        user_id=7,
        session_id="s2",
        tool_name="write_file",
        tool_args={"path": "other.txt"},
        risk_reason="write_file modifies workspace files",
    )

    approvals = store.list_approvals(user_id=7, session_id="s1")

    assert [approval.id for approval in approvals] == [second.id, first.id]
    assert [approval.tool_name for approval in approvals] == ["bash", "write_file"]


def test_store_claims_only_expired_or_pending_jobs_once():
    """Lease claim 应避免多个 worker 认领同一个未过期 job."""
    store = _store()
    job = store.create_job(user_id=7, session_id="s1", kind="background", payload={"command": "echo hi"})

    claimed = store.claim_next_job(worker_id="worker-a", lease_seconds=60)
    second_claim = store.claim_next_job(worker_id="worker-b", lease_seconds=60)

    assert claimed is not None
    assert claimed.id == job.id
    assert claimed.status == "running"
    assert claimed.lease_owner == "worker-a"
    assert second_claim is None


def test_store_reclaims_expired_jobs():
    """过期 lease 的 running job 应可被新 worker 重新认领."""
    store = _store()
    job = AgentJob(
        user_id=7,
        session_id="s1",
        kind="background",
        status="running",
        payload={"command": "echo hi"},
        lease_owner="worker-a",
        lease_expires_at=datetime.now(UTC) - timedelta(seconds=5),
    )
    store.add_job_for_test(job)

    claimed = store.claim_next_job(worker_id="worker-b", lease_seconds=60)

    assert claimed is not None
    assert claimed.lease_owner == "worker-b"
    assert claimed.status == "running"


def test_store_updates_heartbeat_and_completion():
    """Worker heartbeat 和完成结果应写回 job."""
    store = _store()
    job = store.create_job(user_id=7, session_id="s1", kind="background", payload={"command": "echo hi"})
    claimed = store.claim_next_job(worker_id="worker-a", lease_seconds=60)
    assert claimed is not None

    heartbeat = store.heartbeat_job(job_id=job.id or 0, worker_id="worker-a", lease_seconds=60)
    completed = store.complete_job(job_id=job.id or 0, worker_id="worker-a", result="ok")

    assert heartbeat is not None
    assert heartbeat.heartbeat_at is not None
    assert completed is not None
    assert completed.status == "completed"
    assert completed.result == "ok"


def test_store_persists_cron_teammate_and_messages():
    """Cron、teammate 和 inbox message 都应持久化到 runtime store."""
    store = _store()

    cron = store.create_cron(user_id=7, session_id="s1", cron="*/5 * * * *", prompt="check", recurring=True)
    teammate = store.create_teammate(user_id=7, session_id="s1", name="reviewer", role="review", prompt="review")
    message = store.create_message(
        user_id=7,
        session_id="s1",
        sender="lead",
        recipient="reviewer",
        content="please review",
    )

    assert cron.status == "active"
    assert teammate.status == "queued"
    assert message.content == "please review"
    assert [msg.content for msg in store.read_inbox(user_id=7, session_id="s1", recipient="reviewer")] == [
        "please review"
    ]


def test_runtime_facade_uses_store_scope_for_tasks_and_jobs(tmp_path, monkeypatch):
    """AgentRuntime 工具执行面应把状态写入当前 scope 的 store."""
    store = _store()
    runtime = AgentRuntime(store=store)
    runtime.bind_scope(user_id=7, session_id="s1")
    monkeypatch.setattr(runtime, "workspace_root", tmp_path)
    monkeypatch.setattr(runtime.workspace_tools, "workspace_root", tmp_path)
    monkeypatch.setattr(runtime.tool_policy, "workspace_root", tmp_path)

    task_result = runtime.execute("task_create", {"subject": "Migrate", "description": "runtime"})
    job_result = runtime.execute("background_run", {"command": "echo hi"})
    cron_result = runtime.execute("schedule_cron", {"cron": "*/5 * * * *", "prompt": "check", "recurring": True})

    assert json.loads(task_result)["subject"] == "Migrate"
    assert job_result == "job-1"
    assert cron_result == "cron-1"
    assert [task.subject for task in store.list_tasks(user_id=7, session_id="s1")] == ["Migrate"]
    assert [job.kind for job in store.list_jobs(user_id=7, session_id="s1")] == ["background"]


def test_worker_runs_background_job_once(tmp_path):
    """Runtime worker 应通过 lease 执行 background job 并写回结果."""
    store = _store()
    store.create_job(user_id=7, session_id="s1", kind="background", payload={"command": "printf done"})
    runtime = AgentRuntime(store=store)
    runtime.workspace_tools.workspace_root = tmp_path
    worker = AgentRuntimeWorker(runtime=runtime, store=store, worker_id="worker-a")

    assert worker.run_once() is True
    assert worker.run_once() is False

    jobs = store.list_jobs(user_id=7, session_id="s1")
    assert jobs[0].status == "completed"
    assert jobs[0].result == "done"


def test_worker_enqueues_due_cron_once(tmp_path):
    """Runtime worker 应把到期 cron 转换为 background job."""
    store = _store()
    store.create_cron(user_id=7, session_id="s1", cron="* * * * *", prompt="printf cron", recurring=False)
    runtime = AgentRuntime(store=store)
    runtime.workspace_tools.workspace_root = tmp_path
    worker = AgentRuntimeWorker(runtime=runtime, store=store, worker_id="worker-a")

    assert worker.enqueue_due_crons() == 1
    assert worker.enqueue_due_crons() == 0

    jobs = store.list_jobs(user_id=7, session_id="s1")
    crons = store.list_crons(user_id=7, session_id="s1")
    assert jobs[0].kind == "background"
    assert jobs[0].payload["command"] == "printf cron"
    assert crons[0].status == "completed"


def test_worker_turns_teammate_job_into_inbox_message(tmp_path):
    """Teammate job 至少应可通过 inbox 恢复，不应被 worker 标成 unsupported."""
    store = _store()
    teammate = store.create_teammate(user_id=7, session_id="s1", name="reviewer", role="review", prompt="review code")
    store.create_job(
        user_id=7,
        session_id="s1",
        kind="teammate",
        payload={"teammate_id": teammate.id, "name": "reviewer", "role": "review", "prompt": "review code"},
    )
    runtime = AgentRuntime(store=store)
    runtime.workspace_tools.workspace_root = tmp_path
    worker = AgentRuntimeWorker(runtime=runtime, store=store, worker_id="worker-a")

    assert worker.run_once() is True

    jobs = store.list_jobs(user_id=7, session_id="s1")
    messages = store.read_inbox(user_id=7, session_id="s1", recipient="lead")
    assert jobs[0].status == "completed"
    assert "reviewer" in messages[0].content


def test_runtime_teammate_plan_and_shutdown_protocol(tmp_path):
    """Teammate plan approval 和 shutdown 协议应通过消息与状态持久化."""
    store = _store()
    runtime = AgentRuntime(store=store)
    runtime.bind_scope(user_id=7, session_id="s1")
    runtime.workspace_tools.workspace_root = tmp_path
    store.create_teammate(user_id=7, session_id="s1", name="reviewer", role="review", prompt="review code")

    plan_result = runtime.execute(
        "respond_plan",
        {"teammate": "reviewer", "decision": "approved", "comments": "go"},
    )
    shutdown_result = runtime.execute(
        "request_teammate_shutdown",
        {"teammate": "reviewer", "reason": "done"},
    )
    confirm_result = runtime.execute("confirm_teammate_shutdown", {"teammate": "reviewer"})

    teammate = store.list_teammates(user_id=7, session_id="s1")[0]
    inbox = store.read_inbox(user_id=7, session_id="s1", recipient="reviewer")
    assert "plan response sent" in plan_result
    assert "shutdown requested" in shutdown_result
    assert "shutdown confirmed" in confirm_result
    assert teammate.status == "shutdown"
    assert [message.msg_type for message in inbox] == ["plan_approval_response", "shutdown_request"]


def test_runtime_tracks_worktrees_in_store(tmp_path, monkeypatch):
    """Worktree 工具应校验名称并把状态写入 store."""
    store = _store()
    runtime = AgentRuntime(store=store)
    runtime.bind_scope(user_id=7, session_id="s1")
    monkeypatch.setattr(runtime, "workspace_root", tmp_path)
    monkeypatch.setattr(runtime.workspace_tools, "workspace_root", tmp_path)
    monkeypatch.setattr(runtime.tool_policy, "workspace_root", tmp_path)

    result = runtime.execute(
        "worktree_track", {"name": "feature-x", "path": str(tmp_path / "wt"), "branch": "feature/x"}
    )

    assert "feature-x" in result
    assert "feature/x" in runtime.execute("worktree_list", {})
    assert "invalid worktree name" in runtime.execute("worktree_track", {"name": "../bad", "path": "x", "branch": "b"})
    assert "invalid git ref" in runtime.execute(
        "worktree_create", {"name": "safe-name", "branch": "bad;rm", "base": "HEAD"}
    )
