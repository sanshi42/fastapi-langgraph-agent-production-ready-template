"""Agent runtime 状态 API."""

from fastapi import APIRouter, Depends, Request

from app.agent_runtime.store import (
    AgentRuntimeStore,
    agent_runtime_store,
)
from app.api.v1.auth import get_current_session
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import logger
from app.models.session import Session
from app.schemas.runtime import (
    RuntimeApprovalSummary,
    RuntimeCronSummary,
    RuntimeJobSummary,
    RuntimeStateResponse,
    RuntimeTaskSummary,
    RuntimeTeammateSummary,
    RuntimeVisibility,
    RuntimeWorktreeSummary,
)

router = APIRouter()
runtime_store: AgentRuntimeStore = agent_runtime_store


@router.get("/state", response_model=RuntimeStateResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["runtime_state"][0])
async def get_runtime_state(
    request: Request,
    session: Session = Depends(get_current_session),
) -> RuntimeStateResponse:
    """返回当前 session 的只读 Agent runtime 状态."""
    logger.info("runtime_state_requested", session_id=session.id, user_id=session.user_id)

    user_id = int(session.user_id)
    session_id = session.id
    return RuntimeStateResponse(
        session_id=session_id,
        runtime=RuntimeVisibility(
            approval_enabled=settings.AGENT_TOOL_APPROVAL_ENABLED,
            worker_enabled=settings.AGENT_WORKER_ENABLED,
            workspace_root=str(settings.AGENT_WORKSPACE_ROOT),
        ),
        tasks=[
            RuntimeTaskSummary.model_validate(task, from_attributes=True)
            for task in runtime_store.list_tasks(user_id, session_id)
        ],
        jobs=[
            RuntimeJobSummary.model_validate(job, from_attributes=True)
            for job in runtime_store.list_jobs(user_id, session_id)
        ],
        crons=[
            RuntimeCronSummary.model_validate(cron, from_attributes=True)
            for cron in runtime_store.list_crons(user_id, session_id)
        ],
        teammates=[
            RuntimeTeammateSummary.model_validate(teammate, from_attributes=True)
            for teammate in runtime_store.list_teammates(user_id, session_id)
        ],
        worktrees=[
            RuntimeWorktreeSummary.model_validate(worktree, from_attributes=True)
            for worktree in runtime_store.list_worktrees(user_id, session_id)
        ],
        approvals=[
            RuntimeApprovalSummary.model_validate(approval, from_attributes=True)
            for approval in runtime_store.list_approvals(user_id, session_id)
        ],
    )
