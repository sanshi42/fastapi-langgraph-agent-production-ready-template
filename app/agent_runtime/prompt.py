"""Agent runtime system prompt 组装."""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PromptSection:
    """一个可独立维护的 prompt 片段."""

    name: str
    render: Callable[[dict[str, Any]], str]


class PromptAssembler:
    """按 context 拼接 prompt，并复用上一轮结果."""

    def __init__(self, sections: list[PromptSection]) -> None:
        """保存 prompt 片段."""
        self.sections = sections
        self._last_context_key: str | None = None
        self._last_prompt: str | None = None

    def get(self, context: dict[str, Any]) -> str:
        """返回 context 对应 prompt."""
        context_key = json.dumps(context, sort_keys=True, ensure_ascii=False, default=str)
        if context_key == self._last_context_key and self._last_prompt is not None:
            return self._last_prompt

        prompt = "\n\n".join(text for section in self.sections if (text := section.render(context).strip()))
        self._last_context_key = context_key
        self._last_prompt = prompt
        return prompt
