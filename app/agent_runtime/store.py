"""Agent runtime 持久化状态服务."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import Engine
from sqlmodel import Session, col, or_, select

from app.core.config import settings
from app.core.logging import logger
from app.models.agent_runtime import (
    AgentApproval,
    AgentCron,
    AgentJob,
    AgentMessage,
    AgentTask,
    AgentTeammate,
    AgentWorktree,
)


class AgentRuntimeStore:
    """管理按 user_id + session_id 隔离的 runtime 状态."""

    def __init__(self, engine: Engine | None = None) -> None:
        """初始化 store；默认复用应用主数据库 engine."""
        self._engine = engine

    @property
    def engine(self) -> Engine:
        """懒加载数据库 engine，避免测试导入时提前连接真实数据库."""
        if self._engine is None:
            from app.services.database import database_service

            self._engine = database_service.engine
        return self._engine

    def create_task(self, user_id: int, session_id: str, subject: str, description: str = "") -> AgentTask:
        """创建 task board 条目."""
        with Session(self.engine) as session:
            task = AgentTask(user_id=user_id, session_id=session_id, subject=subject, description=description)
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def list_tasks(self, user_id: int, session_id: str) -> list[AgentTask]:
        """按 scope 列出 task."""
        with Session(self.engine) as session:
            statement = (
                select(AgentTask)
                .where(col(AgentTask.user_id) == user_id, col(AgentTask.session_id) == session_id)
                .order_by(col(AgentTask.id))
            )
            return list(session.exec(statement).all())

    def update_task(
        self,
        user_id: int,
        session_id: str,
        task_id: int,
        status: str | None = None,
        owner: str | None = None,
    ) -> AgentTask | None:
        """更新 task 状态."""
        with Session(self.engine) as session:
            task = session.get(AgentTask, task_id)
            if task is None or task.user_id != user_id or task.session_id != session_id:
                return None
            if status:
                task.status = status
            if owner is not None:
                task.owner = owner or None
            task.updated_at = datetime.now(UTC)
            session.add(task)
            session.commit()
            session.refresh(task)
            return task

    def create_approval(
        self,
        user_id: int,
        session_id: str,
        tool_name: str,
        tool_args: dict[str, Any],
        risk_reason: str,
    ) -> AgentApproval:
        """创建 Pending Approval 记录."""
        with Session(self.engine) as session:
            approval = AgentApproval(
                user_id=user_id,
                session_id=session_id,
                tool_name=tool_name,
                tool_args=tool_args,
                risk_reason=risk_reason,
            )
            session.add(approval)
            session.commit()
            session.refresh(approval)
            return approval

    def latest_pending_approval(self, user_id: int, session_id: str) -> AgentApproval | None:
        """返回当前 scope 最新的待审批记录."""
        with Session(self.engine) as session:
            statement = (
                select(AgentApproval)
                .where(
                    col(AgentApproval.user_id) == user_id,
                    col(AgentApproval.session_id) == session_id,
                    col(AgentApproval.status) == "pending",
                )
                .order_by(col(AgentApproval.id).desc())
                .limit(1)
            )
            return session.exec(statement).first()

    def list_approvals(self, user_id: int, session_id: str) -> list[AgentApproval]:
        """列出当前 scope 的审批记录."""
        with Session(self.engine) as session:
            statement = (
                select(AgentApproval)
                .where(col(AgentApproval.user_id) == user_id, col(AgentApproval.session_id) == session_id)
                .order_by(col(AgentApproval.id).desc())
            )
            return list(session.exec(statement).all())

    def decide_approval(
        self,
        user_id: int,
        session_id: str,
        approval_id: int,
        decision: str,
    ) -> AgentApproval | None:
        """记录审批决策."""
        with Session(self.engine) as session:
            approval = session.get(AgentApproval, approval_id)
            if approval is None or approval.user_id != user_id or approval.session_id != session_id:
                return None
            approval.status = "decided"
            approval.decision = decision
            approval.decided_at = datetime.now(UTC)
            session.add(approval)
            session.commit()
            session.refresh(approval)
            return approval

    def create_job(self, user_id: int, session_id: str, kind: str, payload: dict[str, Any]) -> AgentJob:
        """创建 runtime job."""
        with Session(self.engine) as session:
            job = AgentJob(user_id=user_id, session_id=session_id, kind=kind, payload=payload)
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def create_worktree(
        self,
        user_id: int,
        session_id: str,
        name: str,
        path: str,
        branch: str,
        task_id: int | None = None,
    ) -> AgentWorktree:
        """登记 worktree."""
        with Session(self.engine) as session:
            worktree = AgentWorktree(
                user_id=user_id,
                session_id=session_id,
                name=name,
                path=path,
                branch=branch,
                task_id=task_id,
            )
            session.add(worktree)
            session.commit()
            session.refresh(worktree)
            return worktree

    def list_worktrees(self, user_id: int, session_id: str) -> list[AgentWorktree]:
        """列出当前 scope 的 worktrees."""
        with Session(self.engine) as session:
            statement = (
                select(AgentWorktree)
                .where(col(AgentWorktree.user_id) == user_id, col(AgentWorktree.session_id) == session_id)
                .order_by(col(AgentWorktree.id))
            )
            return list(session.exec(statement).all())

    def update_worktree_status(
        self,
        user_id: int,
        session_id: str,
        name: str,
        status: str,
    ) -> AgentWorktree | None:
        """更新 worktree 状态."""
        with Session(self.engine) as session:
            statement = select(AgentWorktree).where(
                col(AgentWorktree.user_id) == user_id,
                col(AgentWorktree.session_id) == session_id,
                col(AgentWorktree.name) == name,
            )
            worktree = session.exec(statement).first()
            if worktree is None:
                return None
            worktree.status = status
            worktree.updated_at = datetime.now(UTC)
            session.add(worktree)
            session.commit()
            session.refresh(worktree)
            return worktree

    def list_jobs(self, user_id: int, session_id: str) -> list[AgentJob]:
        """列出当前 scope 的 runtime jobs."""
        with Session(self.engine) as session:
            statement = (
                select(AgentJob)
                .where(col(AgentJob.user_id) == user_id, col(AgentJob.session_id) == session_id)
                .order_by(col(AgentJob.id))
            )
            return list(session.exec(statement).all())

    def add_job_for_test(self, job: AgentJob) -> AgentJob:
        """测试辅助：直接插入一个 job."""
        with Session(self.engine) as session:
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def claim_next_job(self, worker_id: str, lease_seconds: int | None = None) -> AgentJob | None:
        """认领一个 pending 或 lease 过期的 job."""
        now = datetime.now(UTC)
        lease_expires_at = now + timedelta(seconds=lease_seconds or settings.AGENT_JOB_LEASE_SECONDS)
        with Session(self.engine) as session:
            statement = (
                select(AgentJob)
                .where(
                    or_(
                        col(AgentJob.status) == "pending",
                        col(AgentJob.lease_expires_at) <= now,
                    )
                )
                .order_by(col(AgentJob.id))
                .limit(1)
            )
            job = session.exec(statement).first()
            if job is None:
                return None

            job.status = "running"
            job.lease_owner = worker_id
            job.lease_expires_at = lease_expires_at
            job.heartbeat_at = now
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info("agent_runtime_job_claimed", job_id=job.id, worker_id=worker_id, kind=job.kind)
            return job

    def heartbeat_job(self, job_id: int, worker_id: str, lease_seconds: int | None = None) -> AgentJob | None:
        """刷新 worker 持有的 job lease."""
        now = datetime.now(UTC)
        with Session(self.engine) as session:
            job = session.get(AgentJob, job_id)
            if job is None or job.lease_owner != worker_id or job.status != "running":
                return None
            job.heartbeat_at = now
            job.lease_expires_at = now + timedelta(seconds=lease_seconds or settings.AGENT_JOB_LEASE_SECONDS)
            job.updated_at = now
            session.add(job)
            session.commit()
            session.refresh(job)
            return job

    def complete_job(self, job_id: int, worker_id: str, result: str, status: str = "completed") -> AgentJob | None:
        """完成 worker 持有的 job."""
        with Session(self.engine) as session:
            job = session.get(AgentJob, job_id)
            if job is None or job.lease_owner != worker_id:
                return None
            job.status = status
            job.result = result
            job.lease_expires_at = None
            job.updated_at = datetime.now(UTC)
            session.add(job)
            session.commit()
            session.refresh(job)
            logger.info("agent_runtime_job_completed", job_id=job.id, worker_id=worker_id, status=status)
            return job

    def create_cron(
        self,
        user_id: int,
        session_id: str,
        cron: str,
        prompt: str,
        recurring: bool,
    ) -> AgentCron:
        """创建 cron prompt."""
        with Session(self.engine) as session:
            cron_job = AgentCron(user_id=user_id, session_id=session_id, cron=cron, prompt=prompt, recurring=recurring)
            session.add(cron_job)
            session.commit()
            session.refresh(cron_job)
            return cron_job

    def list_crons(self, user_id: int, session_id: str) -> list[AgentCron]:
        """列出当前 scope 的 cron prompt."""
        with Session(self.engine) as session:
            statement = (
                select(AgentCron)
                .where(col(AgentCron.user_id) == user_id, col(AgentCron.session_id) == session_id)
                .order_by(col(AgentCron.id))
            )
            return list(session.exec(statement).all())

    def list_active_crons(self) -> list[AgentCron]:
        """列出所有 active cron."""
        with Session(self.engine) as session:
            statement = select(AgentCron).where(col(AgentCron.status) == "active").order_by(col(AgentCron.id))
            return list(session.exec(statement).all())

    def mark_cron_fired(self, cron_id: int, recurring: bool) -> AgentCron | None:
        """记录 cron 已触发."""
        with Session(self.engine) as session:
            cron_job = session.get(AgentCron, cron_id)
            if cron_job is None:
                return None
            now = datetime.now(UTC)
            cron_job.last_fired_at = now
            cron_job.updated_at = now
            if not recurring:
                cron_job.status = "completed"
            session.add(cron_job)
            session.commit()
            session.refresh(cron_job)
            return cron_job

    def cancel_cron(self, user_id: int, session_id: str, job_id: int) -> AgentCron | None:
        """取消 cron prompt."""
        with Session(self.engine) as session:
            cron_job = session.get(AgentCron, job_id)
            if cron_job is None or cron_job.user_id != user_id or cron_job.session_id != session_id:
                return None
            cron_job.status = "cancelled"
            cron_job.updated_at = datetime.now(UTC)
            session.add(cron_job)
            session.commit()
            session.refresh(cron_job)
            return cron_job

    def create_teammate(
        self,
        user_id: int,
        session_id: str,
        name: str,
        role: str,
        prompt: str,
    ) -> AgentTeammate:
        """创建 teammate job."""
        with Session(self.engine) as session:
            teammate = AgentTeammate(
                user_id=user_id,
                session_id=session_id,
                name=name,
                role=role,
                prompt=prompt,
                status="queued",
            )
            session.add(teammate)
            session.commit()
            session.refresh(teammate)
            return teammate

    def list_teammates(self, user_id: int, session_id: str) -> list[AgentTeammate]:
        """列出 teammate 状态."""
        with Session(self.engine) as session:
            statement = (
                select(AgentTeammate)
                .where(col(AgentTeammate.user_id) == user_id, col(AgentTeammate.session_id) == session_id)
                .order_by(col(AgentTeammate.id))
            )
            return list(session.exec(statement).all())

    def update_teammate_status(
        self,
        user_id: int,
        session_id: str,
        teammate_id: int,
        status: str,
    ) -> AgentTeammate | None:
        """更新 teammate 状态."""
        with Session(self.engine) as session:
            teammate = session.get(AgentTeammate, teammate_id)
            if teammate is None or teammate.user_id != user_id or teammate.session_id != session_id:
                return None
            teammate.status = status
            teammate.updated_at = datetime.now(UTC)
            session.add(teammate)
            session.commit()
            session.refresh(teammate)
            return teammate

    def create_message(
        self,
        user_id: int,
        session_id: str,
        sender: str,
        recipient: str,
        content: str,
        msg_type: str = "message",
        metadata: dict[str, Any] | None = None,
    ) -> AgentMessage:
        """写入 teammate/lead 消息."""
        with Session(self.engine) as session:
            message = AgentMessage(
                user_id=user_id,
                session_id=session_id,
                sender=sender,
                recipient=recipient,
                msg_type=msg_type,
                content=content,
                metadata_=metadata or {},
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message

    def read_inbox(self, user_id: int, session_id: str, recipient: str) -> list[AgentMessage]:
        """读取指定 recipient 的消息."""
        with Session(self.engine) as session:
            statement = (
                select(AgentMessage)
                .where(
                    col(AgentMessage.user_id) == user_id,
                    col(AgentMessage.session_id) == session_id,
                    col(AgentMessage.recipient) == recipient,
                )
                .order_by(col(AgentMessage.id))
            )
            return list(session.exec(statement).all())


agent_runtime_store = AgentRuntimeStore()
