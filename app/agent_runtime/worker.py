"""应用内 Agent runtime lease worker."""

import asyncio
import contextlib
import socket
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from app.agent_runtime.cron import cron_matches
from app.agent_runtime.runtime import AgentRuntime, agent_runtime
from app.agent_runtime.store import AgentRuntimeStore, agent_runtime_store
from app.core.config import settings
from app.core.logging import logger


class AgentRuntimeWorker:
    """用 Postgres lease 去重执行 runtime jobs."""

    def __init__(
        self,
        runtime: AgentRuntime | None = None,
        store: AgentRuntimeStore | None = None,
        worker_id: str | None = None,
    ) -> None:
        """保存 runtime、store 和 worker 身份."""
        self.runtime = runtime or agent_runtime
        self.store = store or agent_runtime_store
        self.worker_id = worker_id or f"{socket.gethostname()}-agent-runtime-worker"
        self._task: asyncio.Task[None] | None = None
        self._stop_event: asyncio.Event | None = None

    def run_once(self) -> bool:
        """认领并执行一个 job；执行了 job 返回 True."""
        self.enqueue_due_crons()
        job = self.store.claim_next_job(self.worker_id, settings.AGENT_JOB_LEASE_SECONDS)
        if job is None:
            return False

        if job.kind == "teammate":
            result = self._process_teammate_job(job.user_id, job.session_id, job.payload)
            self.store.complete_job(job.id or 0, self.worker_id, result=result)
            return True

        if job.kind != "background":
            result = f"unsupported runtime job kind: {job.kind}"
            self.store.complete_job(job.id or 0, self.worker_id, result=result, status="error")
            return True

        command = str(job.payload.get("command", ""))
        if not command:
            self.store.complete_job(job.id or 0, self.worker_id, result="missing command", status="error")
            return True

        self.runtime.bind_scope(job.user_id, job.session_id)
        result = self.runtime.workspace_tools.bash(command)
        self.store.complete_job(job.id or 0, self.worker_id, result=result)
        return True

    def _process_teammate_job(self, user_id: int, session_id: str, payload: dict) -> str:
        """把 teammate job 转换成可恢复 inbox 通知."""
        name = str(payload.get("name", "teammate"))
        role = str(payload.get("role", "worker"))
        prompt = str(payload.get("prompt", ""))
        teammate_id = payload.get("teammate_id")
        if teammate_id:
            self.store.update_teammate_status(user_id, session_id, int(teammate_id), "waiting")
        self.store.create_message(
            user_id=user_id,
            session_id=session_id,
            sender=name,
            recipient="lead",
            msg_type="teammate_ready",
            content=f"{name} ({role}) is ready: {prompt}",
        )
        return f"teammate {name} queued in inbox"

    def enqueue_due_crons(self, now: datetime | None = None) -> int:
        """把到期 cron 转换为 runtime jobs."""
        current_time = now or datetime.now(UTC)
        enqueued = 0
        for cron in self.store.list_active_crons():
            if cron.last_fired_at and _same_minute(cron.last_fired_at, current_time):
                continue
            if not cron_matches(cron.cron, current_time):
                continue
            self.store.create_job(
                user_id=cron.user_id,
                session_id=cron.session_id,
                kind="background",
                payload={"command": cron.prompt, "source": "cron", "cron_id": cron.id},
            )
            self.store.mark_cron_fired(cron.id or 0, cron.recurring)
            enqueued += 1
        return enqueued

    def start(self, interval_seconds: float = 2.0) -> None:
        """启动后台轮询 worker."""
        if self._task is not None:
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run_loop(interval_seconds))
        logger.info("agent_runtime_worker_started", worker_id=self.worker_id)

    async def stop(self) -> None:
        """停止后台轮询 worker."""
        if self._task is None or self._stop_event is None:
            return
        self._stop_event.set()
        with contextlib.suppress(asyncio.CancelledError):
            await self._task
        self._task = None
        self._stop_event = None
        logger.info("agent_runtime_worker_stopped", worker_id=self.worker_id)

    async def _run_loop(self, interval_seconds: float) -> None:
        """后台轮询 loop."""
        if self._stop_event is None:
            return
        while not self._stop_event.is_set():
            try:
                ran_job = await asyncio.to_thread(self.run_once)
                if not ran_job:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=interval_seconds)
            except TimeoutError:
                continue
            except Exception as exc:
                logger.exception("agent_runtime_worker_iteration_failed", worker_id=self.worker_id, error=str(exc))
                await _sleep_or_stop(self._stop_event.wait, interval_seconds)


async def _sleep_or_stop(wait: Callable[[], Awaitable[bool]], timeout: float) -> None:
    """等待 stop event 或 timeout."""
    try:
        await asyncio.wait_for(wait(), timeout=timeout)
    except TimeoutError:
        return


agent_runtime_worker = AgentRuntimeWorker()


def _same_minute(left: datetime, right: datetime) -> bool:
    """判断两个时间是否在同一分钟."""
    return left.replace(second=0, microsecond=0) == right.replace(second=0, microsecond=0)
