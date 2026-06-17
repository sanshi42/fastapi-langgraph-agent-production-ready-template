"""Runtime state API 测试."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.agent_runtime.store import AgentRuntimeStore
from app.api.v1.auth import get_current_session
from app.models.session import Session as ChatSession


def _store() -> AgentRuntimeStore:
    """创建基于内存数据库的 runtime store."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return AgentRuntimeStore(engine=engine)


def _client(store: AgentRuntimeStore) -> TestClient:
    """创建只挂载 runtime router 的测试客户端."""
    from app.api.v1 import runtime

    app = FastAPI()
    app.include_router(runtime.router, prefix="/runtime")

    async def current_session() -> ChatSession:
        return ChatSession(id="session-a", user_id=7, name="Console", username="hl")

    app.dependency_overrides[get_current_session] = current_session
    runtime.runtime_store = store
    return TestClient(app)


def test_runtime_state_returns_current_session_summary():
    """Runtime state API 应返回当前 session 范围内的状态摘要."""
    store = _store()
    task = store.create_task(user_id=7, session_id="session-a", subject="Build frontend")
    job = store.create_job(user_id=7, session_id="session-a", kind="background", payload={"command": "npm run build"})
    cron = store.create_cron(user_id=7, session_id="session-a", cron="*/5 * * * *", prompt="check", recurring=True)
    teammate = store.create_teammate(
        user_id=7,
        session_id="session-a",
        name="reviewer",
        role="review",
        prompt="review code",
    )
    worktree = store.create_worktree(
        user_id=7,
        session_id="session-a",
        name="console",
        path="/repo/.worktrees/console",
        branch="hl/master/feat/console",
    )
    approval = store.create_approval(
        user_id=7,
        session_id="session-a",
        tool_name="write_file",
        tool_args={"path": "frontend/src/App.tsx"},
        risk_reason="write_file modifies workspace files",
    )
    store.create_task(user_id=8, session_id="session-a", subject="Other user")
    store.create_job(user_id=7, session_id="session-b", kind="background", payload={"command": "echo hidden"})

    response = _client(store).get("/runtime/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["session_id"] == "session-a"
    assert payload["runtime"]["approval_enabled"] is True
    assert payload["tasks"][0]["id"] == task.id
    assert payload["tasks"][0]["subject"] == "Build frontend"
    assert payload["jobs"][0]["id"] == job.id
    assert payload["jobs"][0]["kind"] == "background"
    assert payload["crons"][0]["id"] == cron.id
    assert payload["teammates"][0]["id"] == teammate.id
    assert payload["worktrees"][0]["id"] == worktree.id
    assert payload["approvals"][0]["id"] == approval.id
    assert payload["approvals"][0]["tool_name"] == "write_file"
    assert len(payload["tasks"]) == 1
    assert len(payload["jobs"]) == 1


def test_runtime_state_handles_empty_scope():
    """Runtime state API 在当前 session 无数据时应返回空列表."""
    response = _client(_store()).get("/runtime/state")

    assert response.status_code == 200
    payload = response.json()
    assert payload["tasks"] == []
    assert payload["jobs"] == []
    assert payload["crons"] == []
    assert payload["teammates"] == []
    assert payload["worktrees"] == []
    assert payload["approvals"] == []
