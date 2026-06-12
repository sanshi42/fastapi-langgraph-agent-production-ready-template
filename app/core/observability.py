"""应用可观测性模块."""

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

from app.core.config import settings
from app.core.logging import logger


def langfuse_init() -> bool:
    """初始化 Langfuse，失败时不阻塞应用启动."""
    if not settings.LANGFUSE_TRACING_ENABLED:
        logger.debug("langfuse_tracing_disabled")
        return False

    try:
        langfuse = Langfuse(
            tracing_enabled=True,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            secret_key=settings.LANGFUSE_SECRET_KEY,
            host=settings.LANGFUSE_HOST,
            environment=settings.ENVIRONMENT.value,
            debug=settings.DEBUG,
        )

        if langfuse.auth_check():
            logger.debug("langfuse_auth_success")
            return True

        logger.warning("langfuse_auth_failure")
    except Exception:
        logger.exception("langfuse_initialization_failed")

    settings.LANGFUSE_TRACING_ENABLED = False
    return False


def get_langfuse_callback_handler() -> CallbackHandler:
    """创建用于追踪 LLM 交互的 Langfuse CallbackHandler.

    Returns:
        CallbackHandler: 已配置的 Langfuse callback handler。
    """
    return CallbackHandler()


langfuse_callback_handler = get_langfuse_callback_handler()
