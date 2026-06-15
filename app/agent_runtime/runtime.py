"""Agent runtime 组合入口."""

import json
from pathlib import Path
from typing import Any

from app.agent_runtime.cron import validate_cron
from app.agent_runtime.mcp import MCPClientManager, MCPToolSpec
from app.agent_runtime.project_memory import ProjectMemoryCatalog
from app.agent_runtime.skills import SkillCatalog
from app.agent_runtime.store import AgentRuntimeStore, agent_runtime_store
from app.agent_runtime.tool_policy import ToolDecision, ToolPolicy
from app.agent_runtime.workspace import WorkspaceTools
from app.agent_runtime.worktree import (
    create_git_worktree,
    default_worktree_path,
    remove_git_worktree,
    validate_worktree_name,
)
from app.core.config import settings
from app.core.logging import logger


DEFAULT_USER_ID = 0
DEFAULT_SESSION_ID = "default"


class AgentRuntime:
    """把 workspace、skills、memory、task 等能力组合成工具执行面."""

    def __init__(self, store: AgentRuntimeStore | None = None) -> None:
        """按 settings 初始化 runtime."""
        self.workspace_root = settings.AGENT_WORKSPACE_ROOT.resolve()
        self.workspace_tools = WorkspaceTools(self.workspace_root, settings.AGENT_MAX_OUTPUT_CHARS)
        self.tool_policy = ToolPolicy(self.workspace_root, settings.AGENT_TOOL_APPROVAL_ENABLED)
        self.skills = SkillCatalog(settings.AGENT_SKILLS_DIR)
        self.project_memory = ProjectMemoryCatalog(settings.AGENT_PROJECT_MEMORY_DIR)
        self.store = store or agent_runtime_store
        self.mcp = MCPClientManager.from_config_path(settings.AGENT_MCP_CONFIG_PATH)
        self.user_id = DEFAULT_USER_ID
        self.session_id = DEFAULT_SESSION_ID
        self.todos: list[dict[str, Any]] = []
        self.tasks: list[dict[str, Any]] = []
        self.background_jobs: dict[str, dict[str, Any]] = {}
        self.crons: dict[str, dict[str, Any]] = {}
        self.teammates: dict[str, dict[str, Any]] = {}

    def bind_scope(self, user_id: str | int | None, session_id: str | None) -> None:
        """绑定当前工具调用的 runtime scope."""
        try:
            self.user_id = int(user_id) if user_id is not None else DEFAULT_USER_ID
        except (TypeError, ValueError):
            self.user_id = DEFAULT_USER_ID
        self.session_id = session_id or DEFAULT_SESSION_ID

    def evaluate_tool(self, tool_name: str, args: dict[str, Any]) -> ToolDecision:
        """返回工具策略判定."""
        return self.tool_policy.evaluate(tool_name, args)

    def prompt_context(self) -> dict[str, Any]:
        """返回可注入 system prompt 的 runtime 上下文."""
        return {
            "agent_workspace": str(self.workspace_root),
            "skills": self.skills.describe(),
            "project_memory": self.project_memory.describe(),
            "task_summary": self.list_tasks(),
            "mcp_servers": self.describe_mcp_servers(),
        }

    async def discover_mcp_tools(self) -> list[MCPToolSpec]:
        """发现配置的 MCP tools."""
        registry = await self.mcp.discover()
        return registry.tools()

    def describe_mcp_servers(self) -> str:
        """描述 MCP server 配置."""
        if not self.mcp.servers:
            return "(no MCP servers configured)"
        return "\n".join(f"- {server.name}: {server.transport}" for server in self.mcp.servers)

    def execute(self, tool_name: str, args: dict[str, Any]) -> str:
        """执行一个 runtime 工具."""
        handlers = {
            "bash": lambda: self.workspace_tools.bash(str(args["command"]), int(args.get("timeout", 120))),
            "read_file": lambda: self.workspace_tools.read_file(str(args["path"]), args.get("limit")),
            "write_file": lambda: self.workspace_tools.write_file(str(args["path"]), str(args["content"])),
            "edit_file": lambda: self.workspace_tools.edit_file(
                str(args["path"]),
                str(args["old_text"]),
                str(args["new_text"]),
            ),
            "TodoWrite": lambda: self.update_todos(args.get("items", [])),
            "list_skills": self.skills.describe,
            "load_skill": lambda: self.skills.load(str(args["name"])),
            "list_project_memories": self.project_memory.describe,
            "load_project_memory": lambda: self.project_memory.load(str(args["filename"])),
            "task_create": lambda: self.create_task(str(args["subject"]), str(args.get("description", ""))),
            "task_list": self.list_tasks,
            "task_update": lambda: self.update_task(
                int(args["task_id"]),
                args.get("status"),
                args.get("owner"),
            ),
            "worktree_list": self.list_worktrees,
            "worktree_track": lambda: self.track_worktree(
                str(args["name"]),
                str(args["path"]),
                str(args["branch"]),
                args.get("task_id"),
            ),
            "worktree_create": lambda: self.create_worktree(
                str(args["name"]),
                str(args["branch"]),
                str(args.get("base", "HEAD")),
                args.get("task_id"),
            ),
            "worktree_remove": lambda: self.remove_worktree(str(args["name"])),
            "background_run": lambda: self.start_background_job(str(args["command"])),
            "check_background": lambda: self.check_background(args.get("job_id")),
            "schedule_cron": lambda: self.schedule_cron(
                str(args["cron"]),
                str(args["prompt"]),
                bool(args.get("recurring", True)),
            ),
            "list_crons": self.list_crons,
            "cancel_cron": lambda: self.cancel_cron(str(args["job_id"])),
            "spawn_teammate": lambda: self.spawn_teammate(
                str(args["name"]),
                str(args["role"]),
                str(args["prompt"]),
            ),
            "list_teammates": self.list_teammates,
            "send_message": lambda: self.send_message(
                str(args["to"]),
                str(args["content"]),
                str(args.get("msg_type", "message")),
            ),
            "read_inbox": lambda: self.read_inbox(),
            "respond_plan": lambda: self.respond_plan(
                str(args["teammate"]),
                str(args["decision"]),
                str(args.get("comments", "")),
            ),
            "request_teammate_shutdown": lambda: self.request_teammate_shutdown(
                str(args["teammate"]),
                str(args.get("reason", "")),
            ),
            "confirm_teammate_shutdown": lambda: self.confirm_teammate_shutdown(str(args["teammate"])),
        }
        handler = handlers.get(tool_name)
        if handler is None and tool_name.startswith("mcp__"):
            return "mcp tools require async execution through call_mcp_tool"
        if handler is None:
            return f"unknown agent runtime tool: {tool_name}"
        return str(handler())

    async def call_mcp_tool(self, tool_name: str, args: dict[str, Any]) -> str:
        """调用 MCP tool."""
        return await self.mcp.call_tool(tool_name, args)

    def update_todos(self, items: Any) -> str:
        """更新短期 todo 列表."""
        if not isinstance(items, list):
            return "items must be a list"
        in_progress = [item for item in items if isinstance(item, dict) and item.get("status") == "in_progress"]
        if len(in_progress) > 1:
            return "only one todo item can be in_progress"
        self.todos = [item for item in items if isinstance(item, dict)]
        return json.dumps(self.todos, ensure_ascii=False)

    def create_task(self, subject: str, description: str = "") -> str:
        """创建 task."""
        try:
            task_model = self.store.create_task(self.user_id, self.session_id, subject, description)
            return json.dumps(task_model.model_dump(mode="json"), ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_task_store_failed", error=str(exc), session_id=self.session_id)

        task = {
            "id": len(self.tasks) + 1,
            "subject": subject,
            "description": description,
            "status": "pending",
            "owner": None,
        }
        self.tasks.append(task)
        return json.dumps(task, ensure_ascii=False)

    def list_tasks(self) -> str:
        """列出 task 摘要."""
        try:
            tasks = self.store.list_tasks(self.user_id, self.session_id)
            if tasks:
                return "\n".join(f"#{task.id} [{task.status}] {task.subject}" for task in tasks)
        except Exception as exc:
            logger.exception("agent_runtime_task_list_failed", error=str(exc), session_id=self.session_id)

        if not self.tasks:
            return "(no runtime tasks)"
        return "\n".join(f"#{task['id']} [{task['status']}] {task['subject']}" for task in self.tasks)

    def update_task(self, task_id: int, status: Any = None, owner: Any = None) -> str:
        """更新 task 状态."""
        try:
            task_model = self.store.update_task(
                self.user_id,
                self.session_id,
                task_id,
                str(status) if status else None,
                str(owner) if owner is not None else None,
            )
            if task_model is not None:
                return json.dumps(task_model.model_dump(mode="json"), ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_task_update_failed", error=str(exc), session_id=self.session_id)

        for task in self.tasks:
            if task["id"] == task_id:
                if status:
                    task["status"] = str(status)
                if owner is not None:
                    task["owner"] = str(owner) if owner else None
                return json.dumps(task, ensure_ascii=False)
        return f"unknown task: {task_id}"

    def start_background_job(self, command: str) -> str:
        """登记一个后台任务."""
        try:
            job = self.store.create_job(
                self.user_id,
                self.session_id,
                kind="background",
                payload={"command": command},
            )
            return f"job-{job.id}"
        except Exception as exc:
            logger.exception("agent_runtime_background_job_store_failed", error=str(exc), session_id=self.session_id)

        job_id = f"job-{len(self.background_jobs) + 1}"
        self.background_jobs[job_id] = {"command": command, "status": "queued"}
        return job_id

    def check_background(self, job_id: Any = None) -> str:
        """查询后台任务."""
        if job_id:
            normalized_id = _parse_runtime_id(job_id, prefix="job-")
            try:
                if normalized_id is not None:
                    jobs = [
                        job for job in self.store.list_jobs(self.user_id, self.session_id) if job.id == normalized_id
                    ]
                    if jobs:
                        return json.dumps(jobs[0].model_dump(mode="json"), ensure_ascii=False)
            except Exception as exc:
                logger.exception("agent_runtime_background_check_failed", error=str(exc), session_id=self.session_id)
            return json.dumps(self.background_jobs.get(str(job_id), {"status": "unknown"}), ensure_ascii=False)
        try:
            jobs = self.store.list_jobs(self.user_id, self.session_id)
            if jobs:
                return json.dumps([job.model_dump(mode="json") for job in jobs], ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_background_list_failed", error=str(exc), session_id=self.session_id)
        return json.dumps(self.background_jobs, ensure_ascii=False)

    def track_worktree(self, name: str, path: str, branch: str, task_id: Any = None) -> str:
        """登记已有 worktree."""
        error = validate_worktree_name(name)
        if error:
            return error
        candidate_path = Path(path)
        if candidate_path.is_absolute():
            worktree_path = candidate_path.resolve()
            if not worktree_path.is_relative_to(self.workspace_root):
                return "path escapes agent workspace"
        else:
            worktree_path = self.workspace_tools.resolve_path(path)
        try:
            worktree = self.store.create_worktree(
                self.user_id,
                self.session_id,
                name=name,
                path=str(worktree_path),
                branch=branch,
                task_id=int(task_id) if task_id else None,
            )
            return json.dumps(worktree.model_dump(mode="json"), ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_worktree_track_failed", error=str(exc), session_id=self.session_id)
            return f"failed to track worktree: {exc}"

    def create_worktree(self, name: str, branch: str, base: str = "HEAD", task_id: Any = None) -> str:
        """创建并登记 git worktree."""
        error = validate_worktree_name(name)
        if error:
            return error
        output, path = create_git_worktree(self.workspace_tools, name, branch, base)
        try:
            self.store.create_worktree(
                self.user_id,
                self.session_id,
                name=name,
                path=str(path),
                branch=branch,
                task_id=int(task_id) if task_id else None,
            )
        except Exception as exc:
            logger.exception("agent_runtime_worktree_create_store_failed", error=str(exc), session_id=self.session_id)
        return output

    def list_worktrees(self) -> str:
        """列出 tracked worktrees."""
        try:
            worktrees = self.store.list_worktrees(self.user_id, self.session_id)
            if worktrees:
                return "\n".join(
                    f"{worktree.name} [{worktree.status}] {worktree.branch} -> {worktree.path}"
                    for worktree in worktrees
                )
        except Exception as exc:
            logger.exception("agent_runtime_worktree_list_failed", error=str(exc), session_id=self.session_id)
        return "(no worktrees tracked)"

    def remove_worktree(self, name: str) -> str:
        """移除 tracked worktree."""
        error = validate_worktree_name(name)
        if error:
            return error
        path = default_worktree_path(self.workspace_root, name)
        output = remove_git_worktree(self.workspace_tools, str(path.relative_to(self.workspace_root)))
        try:
            self.store.update_worktree_status(self.user_id, self.session_id, name=name, status="removed")
        except Exception as exc:
            logger.exception("agent_runtime_worktree_remove_store_failed", error=str(exc), session_id=self.session_id)
        return output

    def schedule_cron(self, cron: str, prompt: str, recurring: bool) -> str:
        """登记 cron prompt."""
        error = validate_cron(cron)
        if error:
            return error
        try:
            cron_model = self.store.create_cron(self.user_id, self.session_id, cron, prompt, recurring)
            return f"cron-{cron_model.id}"
        except Exception as exc:
            logger.exception("agent_runtime_cron_store_failed", error=str(exc), session_id=self.session_id)

        job_id = f"cron-{len(self.crons) + 1}"
        self.crons[job_id] = {"cron": cron, "prompt": prompt, "recurring": recurring}
        return job_id

    def list_crons(self) -> str:
        """列出 cron prompt."""
        try:
            crons = self.store.list_crons(self.user_id, self.session_id)
            if crons:
                return json.dumps([cron.model_dump(mode="json") for cron in crons], ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_cron_list_failed", error=str(exc), session_id=self.session_id)
        return json.dumps(self.crons, ensure_ascii=False)

    def cancel_cron(self, job_id: str) -> str:
        """取消 cron prompt."""
        cron_id = _parse_runtime_id(job_id, prefix="cron-")
        if cron_id is not None:
            try:
                cron_model = self.store.cancel_cron(self.user_id, self.session_id, cron_id)
                if cron_model is not None:
                    return f"cancelled cron-{cron_model.id}"
            except Exception as exc:
                logger.exception("agent_runtime_cron_cancel_failed", error=str(exc), session_id=self.session_id)

        if self.crons.pop(job_id, None) is None:
            return f"unknown cron: {job_id}"
        return f"cancelled {job_id}"

    def spawn_teammate(self, name: str, role: str, prompt: str) -> str:
        """登记 teammate job."""
        try:
            teammate = self.store.create_teammate(self.user_id, self.session_id, name, role, prompt)
            self.store.create_job(
                self.user_id,
                self.session_id,
                kind="teammate",
                payload={"teammate_id": teammate.id, "name": name, "role": role, "prompt": prompt},
            )
            return f"spawned {teammate.name}"
        except Exception as exc:
            logger.exception("agent_runtime_teammate_store_failed", error=str(exc), session_id=self.session_id)

        self.teammates[name] = {"role": role, "prompt": prompt, "status": "queued"}
        return f"spawned {name}"

    def list_teammates(self) -> str:
        """列出 teammate 状态."""
        try:
            teammates = self.store.list_teammates(self.user_id, self.session_id)
            if teammates:
                return json.dumps([teammate.model_dump(mode="json") for teammate in teammates], ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_teammate_list_failed", error=str(exc), session_id=self.session_id)
        return json.dumps(self.teammates, ensure_ascii=False)

    def send_message(self, recipient: str, content: str, msg_type: str = "message") -> str:
        """发送 runtime 消息."""
        try:
            message = self.store.create_message(
                self.user_id,
                self.session_id,
                sender="lead",
                recipient=recipient,
                msg_type=msg_type,
                content=content,
            )
            return f"message-{message.id} queued"
        except Exception as exc:
            logger.exception("agent_runtime_message_store_failed", error=str(exc), session_id=self.session_id)
            return "message queue unavailable"

    def read_inbox(self) -> str:
        """读取 lead inbox."""
        try:
            messages = self.store.read_inbox(self.user_id, self.session_id, recipient="lead")
            return json.dumps([message.model_dump(mode="json") for message in messages], ensure_ascii=False)
        except Exception as exc:
            logger.exception("agent_runtime_inbox_read_failed", error=str(exc), session_id=self.session_id)
            return "[]"

    def respond_plan(self, teammate: str, decision: str, comments: str = "") -> str:
        """向 teammate 发送计划审批结果."""
        normalized_decision = decision.strip().lower()
        if normalized_decision not in {"approved", "denied"}:
            return "decision must be approved or denied"
        try:
            self.store.create_message(
                self.user_id,
                self.session_id,
                sender="lead",
                recipient=teammate,
                msg_type="plan_approval_response",
                content=f"{normalized_decision}: {comments}".strip(),
            )
            return f"plan response sent to {teammate}"
        except Exception as exc:
            logger.exception("agent_runtime_plan_response_failed", error=str(exc), session_id=self.session_id)
            return "plan response failed"

    def request_teammate_shutdown(self, teammate: str, reason: str = "") -> str:
        """请求 teammate 优雅退出."""
        try:
            self.store.create_message(
                self.user_id,
                self.session_id,
                sender="lead",
                recipient=teammate,
                msg_type="shutdown_request",
                content=reason or "shutdown requested",
            )
            return f"shutdown requested for {teammate}"
        except Exception as exc:
            logger.exception("agent_runtime_shutdown_request_failed", error=str(exc), session_id=self.session_id)
            return "shutdown request failed"

    def confirm_teammate_shutdown(self, teammate: str) -> str:
        """确认 teammate 已退出."""
        try:
            for item in self.store.list_teammates(self.user_id, self.session_id):
                if item.name == teammate and item.id is not None:
                    self.store.update_teammate_status(self.user_id, self.session_id, item.id, "shutdown")
                    return f"shutdown confirmed for {teammate}"
            return f"unknown teammate: {teammate}"
        except Exception as exc:
            logger.exception("agent_runtime_shutdown_confirm_failed", error=str(exc), session_id=self.session_id)
            return "shutdown confirm failed"


def _parse_runtime_id(value: Any, prefix: str) -> int | None:
    """解析 job-1 / cron-1 这类 runtime ID."""
    text = str(value)
    if text.startswith(prefix):
        text = text[len(prefix) :]
    try:
        return int(text)
    except ValueError:
        return None


agent_runtime = AgentRuntime()
