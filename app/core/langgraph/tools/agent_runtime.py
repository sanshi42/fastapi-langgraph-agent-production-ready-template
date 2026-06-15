"""Agent runtime LangChain tools."""

from typing import Any, cast

from langchain_core.tools import StructuredTool
from langchain_core.tools.base import BaseTool
from pydantic import BaseModel, create_model

from app.agent_runtime.runtime import agent_runtime


def _runtime_tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: set[str] | None = None,
) -> BaseTool:
    """创建一个转发到 AgentRuntime 的 LangChain structured tool."""

    async def _call(**kwargs: Any) -> str:
        return agent_runtime.execute(name, kwargs)

    return StructuredTool.from_function(
        coroutine=_call,
        name=name,
        description=description,
        args_schema=_create_args_model(name, properties, required or set()),
    )


def _create_args_model(name: str, properties: dict[str, Any], required: set[str]) -> type[BaseModel]:
    """根据简化 JSON schema 构建 Pydantic args model."""
    fields: dict[str, tuple[Any, Any]] = {}
    for field_name, field_schema in properties.items():
        field_type = _python_type_for(field_schema)
        default = ... if field_name in required else None
        fields[field_name] = (field_type, default)
    field_definitions = cast(dict[str, Any], fields)
    return cast(type[BaseModel], create_model(f"{name.title().replace('_', '')}Args", **field_definitions))


def _python_type_for(field_schema: dict[str, Any]) -> Any:
    """把少量 JSON schema 类型映射到 Python 类型."""
    match field_schema.get("type"):
        case "integer":
            return int
        case "boolean":
            return bool
        case "array":
            return list[dict[str, Any]]
        case _:
            return str


def build_agent_runtime_tools() -> list[BaseTool]:
    """构建默认暴露给聊天 Agent 的 runtime tools."""
    return [
        _runtime_tool(
            "bash",
            "Run a shell command inside the configured Agent Workspace.",
            {"command": {"type": "string"}, "timeout": {"type": "integer"}},
            {"command"},
        ),
        _runtime_tool(
            "read_file",
            "Read a text file from the configured Agent Workspace.",
            {"path": {"type": "string"}, "limit": {"type": "integer"}},
            {"path"},
        ),
        _runtime_tool(
            "write_file",
            "Write a text file inside the configured Agent Workspace.",
            {"path": {"type": "string"}, "content": {"type": "string"}},
            {"path", "content"},
        ),
        _runtime_tool(
            "edit_file",
            "Replace exact text once in a workspace file.",
            {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}},
            {"path", "old_text", "new_text"},
        ),
        _runtime_tool(
            "TodoWrite",
            "Update the short-term todo list.",
            {"items": {"type": "array"}},
            {"items"},
        ),
        _runtime_tool("list_skills", "List workspace-local skills.", {}),
        _runtime_tool("load_skill", "Load a workspace-local skill by name.", {"name": {"type": "string"}}, {"name"}),
        _runtime_tool("list_project_memories", "List workspace project memory files.", {}),
        _runtime_tool(
            "load_project_memory",
            "Load a workspace project memory markdown file.",
            {"filename": {"type": "string"}},
            {"filename"},
        ),
        _runtime_tool(
            "task_create",
            "Create an Agent task scoped to this runtime.",
            {"subject": {"type": "string"}, "description": {"type": "string"}},
            {"subject"},
        ),
        _runtime_tool("task_list", "List Agent tasks.", {}),
        _runtime_tool(
            "task_update",
            "Update an Agent task.",
            {"task_id": {"type": "integer"}, "status": {"type": "string"}, "owner": {"type": "string"}},
            {"task_id"},
        ),
        _runtime_tool("worktree_list", "List tracked Agent worktrees.", {}),
        _runtime_tool(
            "worktree_track",
            "Track an existing git worktree inside the Agent Workspace.",
            {
                "name": {"type": "string"},
                "path": {"type": "string"},
                "branch": {"type": "string"},
                "task_id": {"type": "integer"},
            },
            {"name", "path", "branch"},
        ),
        _runtime_tool(
            "worktree_create",
            "Create a git worktree under .worktrees in the Agent Workspace.",
            {
                "name": {"type": "string"},
                "branch": {"type": "string"},
                "base": {"type": "string"},
                "task_id": {"type": "integer"},
            },
            {"name", "branch"},
        ),
        _runtime_tool("worktree_remove", "Remove a tracked Agent worktree.", {"name": {"type": "string"}}, {"name"}),
        _runtime_tool(
            "background_run",
            "Queue a background shell command.",
            {"command": {"type": "string"}},
            {"command"},
        ),
        _runtime_tool("check_background", "Check background job state.", {"job_id": {"type": "string"}}),
        _runtime_tool(
            "schedule_cron",
            "Schedule a prompt using a five-field cron expression.",
            {
                "cron": {"type": "string"},
                "prompt": {"type": "string"},
                "recurring": {"type": "boolean"},
            },
            {"cron", "prompt"},
        ),
        _runtime_tool("list_crons", "List scheduled runtime cron jobs.", {}),
        _runtime_tool("cancel_cron", "Cancel a runtime cron job.", {"job_id": {"type": "string"}}, {"job_id"}),
        _runtime_tool(
            "spawn_teammate",
            "Spawn a queued teammate job.",
            {"name": {"type": "string"}, "role": {"type": "string"}, "prompt": {"type": "string"}},
            {"name", "role", "prompt"},
        ),
        _runtime_tool("list_teammates", "List teammate jobs.", {}),
        _runtime_tool(
            "send_message",
            "Send a runtime message to a teammate or lead.",
            {"to": {"type": "string"}, "content": {"type": "string"}, "msg_type": {"type": "string"}},
            {"to", "content"},
        ),
        _runtime_tool("read_inbox", "Read runtime inbox messages.", {}),
        _runtime_tool(
            "respond_plan",
            "Respond to a teammate-submitted plan.",
            {
                "teammate": {"type": "string"},
                "decision": {"type": "string"},
                "comments": {"type": "string"},
            },
            {"teammate", "decision"},
        ),
        _runtime_tool(
            "request_teammate_shutdown",
            "Ask a teammate to shut down gracefully.",
            {"teammate": {"type": "string"}, "reason": {"type": "string"}},
            {"teammate"},
        ),
        _runtime_tool(
            "confirm_teammate_shutdown",
            "Mark a teammate as shut down after it confirms exit.",
            {"teammate": {"type": "string"}},
            {"teammate"},
        ),
    ]


async def build_mcp_runtime_tools() -> list[BaseTool]:
    """发现并构建 MCP runtime tools."""
    mcp_specs = await agent_runtime.discover_mcp_tools()
    return [
        _mcp_tool(spec.namespaced_name, spec.description or f"Call MCP tool {spec.tool_name}", spec.input_schema)
        for spec in mcp_specs
    ]


def _mcp_tool(name: str, description: str, input_schema: dict[str, Any]) -> BaseTool:
    """创建一个转发到 MCP client 的 LangChain tool."""
    properties = input_schema.get("properties", {})
    required = set(input_schema.get("required", []))

    async def _call(**kwargs: Any) -> str:
        return await agent_runtime.call_mcp_tool(name, kwargs)

    return StructuredTool.from_function(
        coroutine=_call,
        name=name,
        description=description,
        args_schema=_create_args_model(name, properties, required),
    )
