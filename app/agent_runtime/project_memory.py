"""Agent Workspace 项目资料库."""

import re
from pathlib import Path
from typing import Any

import yaml


class ProjectMemoryCatalog:
    """读取 workspace ``.memory/*.md`` 资料文件."""

    def __init__(self, memory_dir: Path) -> None:
        """保存资料库目录."""
        self.memory_dir = memory_dir

    def describe(self) -> str:
        """返回资料库摘要."""
        items = self._items()
        if not items:
            return "(no project memory)"
        return "\n".join(f"{item['name']} ({item['filename']}) - {item['description']}" for item in items)

    def load(self, filename: str) -> str:
        """读取一个资料文件，拒绝目录逃逸."""
        path = (self.memory_dir / filename).resolve()
        if not path.is_relative_to(self.memory_dir.resolve()):
            return "memory path escapes project memory directory"
        if path.name == "MEMORY.md" or not path.exists():
            return f"unknown project memory: {filename}"
        return path.read_text()

    def _items(self) -> list[dict[str, str]]:
        """列出可加载的 markdown 资料."""
        if not self.memory_dir.exists():
            return []
        items: list[dict[str, str]] = []
        for path in sorted(self.memory_dir.glob("*.md")):
            if path.name == "MEMORY.md":
                continue
            meta, _ = _parse_frontmatter(path.read_text())
            items.append(
                {
                    "filename": path.name,
                    "name": str(meta.get("name") or path.stem),
                    "description": str(meta.get("description") or "-"),
                }
            )
        return items


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析简化 YAML frontmatter."""
    match = re.match(r"^---\s*\n(?P<yaml>.*?)\s*\n---\s*\n(?P<body>.*)$", text, re.DOTALL)
    if not match:
        return {}, text.strip()
    try:
        meta = yaml.safe_load(match.group("yaml")) or {}
    except yaml.YAMLError:
        meta = {}
    return meta, match.group("body").strip()
