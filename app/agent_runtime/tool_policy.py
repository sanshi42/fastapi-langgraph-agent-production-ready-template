"""Agent 工具执行策略."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.agent_runtime.workspace import DANGEROUS_COMMAND_SNIPPETS

SENSITIVE_TOOLS = {
    "bash": "bash executes shell commands",
    "background_run": "background_run executes shell commands outside the request lifecycle",
    "write_file": "write_file modifies workspace files",
    "edit_file": "edit_file modifies workspace files",
    "worktree_create": "worktree_create changes git worktree state",
    "worktree_run": "worktree_run executes commands in a git worktree",
    "worktree_remove": "worktree_remove deletes a git worktree",
    "schedule_cron": "schedule_cron creates a background trigger",
    "spawn_teammate": "spawn_teammate starts autonomous background work",
    "request_teammate_shutdown": "request_teammate_shutdown changes teammate lifecycle state",
}


@dataclass(frozen=True)
class ToolDecision:
    """工具策略判定结果."""

    requires_approval: bool
    denied: bool = False
    reason: str = ""


class ToolPolicy:
    """统一判断工具调用是否允许、拒绝或需要审批."""

    def __init__(self, workspace_root: Path, approval_enabled: bool = True) -> None:
        """保存工作区和审批开关."""
        self.workspace_root = workspace_root.resolve()
        self.approval_enabled = approval_enabled

    def evaluate(self, tool_name: str, args: dict[str, Any]) -> ToolDecision:
        """返回工具调用的策略判定."""
        command = str(args.get("command", ""))
        if tool_name in {"bash", "background_run", "worktree_run"}:
            blocked = next((snippet for snippet in DANGEROUS_COMMAND_SNIPPETS if snippet in command), None)
            if blocked:
                return ToolDecision(
                    requires_approval=False,
                    denied=True,
                    reason=f"command contains denied snippet: {blocked}",
                )

        if tool_name in {"write_file", "edit_file"} and self._path_escapes(str(args.get("path", ""))):
            return ToolDecision(
                requires_approval=False,
                denied=True,
                reason="path escapes agent workspace",
            )

        reason = SENSITIVE_TOOLS.get(tool_name)
        if reason and self.approval_enabled:
            return ToolDecision(requires_approval=True, reason=reason)

        if tool_name.startswith("mcp__") and self.approval_enabled and _looks_destructive_mcp_tool(tool_name):
            return ToolDecision(requires_approval=True, reason="mcp tool may change external state")

        return ToolDecision(requires_approval=False)

    def _path_escapes(self, path: str) -> bool:
        """判断路径是否逃逸 Agent Workspace."""
        return not (self.workspace_root / path).resolve().is_relative_to(self.workspace_root)


def _looks_destructive_mcp_tool(tool_name: str) -> bool:
    """用名称启发式识别可能写外部状态的 MCP 工具."""
    destructive_words = ("write", "edit", "delete", "remove", "create", "update", "trigger", "deploy")
    normalized = tool_name.lower()
    return any(word in normalized for word in destructive_words)
