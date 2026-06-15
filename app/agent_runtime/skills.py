"""Workspace 本地 skill 目录加载."""

import re
from pathlib import Path
from typing import Any

import yaml


class SkillCatalog:
    """扫描并加载 ``skills/**/SKILL.md``."""

    def __init__(self, skills_dir: Path) -> None:
        """建立 skill 名称索引."""
        self.skills_dir = skills_dir
        self._skills = self._load_skills()

    def describe(self) -> str:
        """返回适合注入 prompt 的 skill 摘要."""
        if not self._skills:
            return "(no workspace skills)"
        return "\n".join(f"{name}: {item['description']}" for name, item in sorted(self._skills.items()))

    def load(self, name: str) -> str:
        """按名称加载 skill 正文."""
        skill = self._skills.get(name)
        if not skill:
            available = ", ".join(sorted(self._skills)) or "(none)"
            return f"unknown skill '{name}'. available: {available}"
        return f'<skill name="{name}">\n{skill["body"]}\n</skill>'

    def _load_skills(self) -> dict[str, dict[str, str]]:
        """读取目录中的所有 skill 文件."""
        if not self.skills_dir.exists():
            return {}

        loaded: dict[str, dict[str, str]] = {}
        for skill_file in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = _parse_frontmatter(skill_file.read_text())
            name = str(meta.get("name") or skill_file.parent.name)
            loaded[name] = {
                "description": str(meta.get("description") or "-"),
                "body": body,
            }
        return loaded


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
