"""Agent Workspace 文件和 shell 工具."""

import subprocess
from pathlib import Path

DANGEROUS_COMMAND_SNIPPETS = ("rm -rf /", "sudo", "shutdown", "reboot", "> /dev/")


class WorkspaceTools:
    """限制在 Agent Workspace 内执行的基础工具."""

    def __init__(self, workspace_root: Path, max_output_chars: int) -> None:
        """保存工作区路径和输出截断上限."""
        self.workspace_root = workspace_root.resolve()
        self.max_output_chars = max_output_chars

    def resolve_path(self, path: str) -> Path:
        """解析 workspace 内路径，拒绝目录逃逸."""
        resolved = (self.workspace_root / path).resolve()
        if not resolved.is_relative_to(self.workspace_root):
            raise ValueError(f"path escapes agent workspace: {path}")
        return resolved

    def bash(self, command: str, timeout: int = 120) -> str:
        """在 Agent Workspace 中执行 shell 命令."""
        blocked = next((snippet for snippet in DANGEROUS_COMMAND_SNIPPETS if snippet in command), None)
        if blocked:
            return f"blocked dangerous command snippet: {blocked}"

        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.workspace_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return f"command timed out after {timeout}s"
        except OSError as exc:
            return f"command failed: {exc}"

        output = (result.stdout + result.stderr).strip()
        return output[: self.max_output_chars] if output else "(no output)"

    def read_file(self, path: str, limit: int | None = None) -> str:
        """读取 workspace 内文本文件."""
        file_path = self.resolve_path(path)
        lines = file_path.read_text().splitlines()
        if limit is not None and limit < len(lines):
            lines = lines[:limit] + [f"...({len(lines) - limit} more lines)"]
        return "\n".join(lines)[: self.max_output_chars]

    def write_file(self, path: str, content: str) -> str:
        """写入 workspace 内文本文件."""
        file_path = self.resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        return f"wrote {len(content)} bytes to {path}"

    def edit_file(self, path: str, old_text: str, new_text: str) -> str:
        """对 workspace 内文本文件执行一次精确替换."""
        file_path = self.resolve_path(path)
        content = file_path.read_text()
        if old_text not in content:
            return f"target text not found in {path}"
        file_path.write_text(content.replace(old_text, new_text, 1))
        return f"edited {path}"
