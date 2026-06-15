"""LLM 调用恢复状态."""

from dataclasses import dataclass

CONTINUATION_PROMPT = "Output token limit hit. Resume directly - no apology, no recap."
DEFAULT_MAX_TOKENS = 8000
ESCALATED_MAX_TOKENS = 64000
MAX_RECOVERY_RETRIES = 3


@dataclass
class RecoveryState:
    """一次 runtime 调用中的恢复状态."""

    current_model: str
    fallback_model: str | None = None
    has_escalated: bool = False
    recovery_count: int = 0
    consecutive_529: int = 0
    has_attempted_reactive_compact: bool = False


def is_prompt_too_long(exc: Exception) -> bool:
    """判断异常是否表示上下文过长."""
    message = str(exc).lower()
    return (
        ("prompt" in message and "long" in message)
        or "prompt_is_too_long" in message
        or "context_length_exceeded" in message
        or "max_context_window" in message
    )
