"""Agent runtime git worktree helpers."""

import re
import shlex
from pathlib import Path

from app.agent_runtime.workspace import WorkspaceTools

_WORKTREE_NAME = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$")
_GIT_REF = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._/:-]{0,180}$")


def validate_worktree_name(name: str) -> str | None:
    """校验 worktree 名称."""
    if not _WORKTREE_NAME.match(name):
        return "invalid worktree name"
    return None


def default_worktree_path(workspace_root: Path, name: str) -> Path:
    """返回 worktree 默认路径."""
    return (workspace_root / ".worktrees" / name).resolve()


def validate_git_ref(value: str) -> str | None:
    """校验 git ref 参数."""
    if not _GIT_REF.match(value) or ".." in value:
        return "invalid git ref"
    return None


def create_git_worktree(tools: WorkspaceTools, name: str, branch: str, base: str = "HEAD") -> tuple[str, Path]:
    """创建 git worktree."""
    error = validate_worktree_name(name)
    if error:
        return error, default_worktree_path(tools.workspace_root, name)
    for ref in (branch, base):
        error = validate_git_ref(ref)
        if error:
            return error, default_worktree_path(tools.workspace_root, name)
    path = default_worktree_path(tools.workspace_root, name)
    output = tools.bash(f"git worktree add -b {shlex.quote(branch)} {shlex.quote(str(path))} {shlex.quote(base)}")
    return output, path


def remove_git_worktree(tools: WorkspaceTools, path: str) -> str:
    """移除 git worktree."""
    worktree_path = tools.resolve_path(path)
    return tools.bash(f"git worktree remove {shlex.quote(str(worktree_path))}")
