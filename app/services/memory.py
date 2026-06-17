"""基于 mem0 和 pgvector 的长期记忆服务，带可选缓存层."""

import inspect
from typing import cast

from mem0 import AsyncMemory

from app.core.cache import (
    cache_key,
    cache_service,
)
from app.core.config import settings
from app.core.logging import logger


class MemoryService:
    """使用 mem0 和 pgvector 管理长期记忆的服务."""

    def __init__(self):
        """初始化 memory service."""
        self._memory: AsyncMemory | None = None

    async def _get_memory(self) -> AsyncMemory:
        if self._memory is None:
            memory = AsyncMemory.from_config(
                config_dict={
                    "vector_store": {
                        "provider": "pgvector",
                        "config": {
                            "collection_name": settings.LONG_TERM_MEMORY_COLLECTION_NAME,
                            "dbname": settings.POSTGRES_DB,
                            "user": settings.POSTGRES_USER,
                            "password": settings.POSTGRES_PASSWORD,
                            "host": settings.POSTGRES_HOST,
                            "port": settings.POSTGRES_PORT,
                        },
                    },
                    "llm": {
                        "provider": settings.LONG_TERM_MEMORY_LLM_PROVIDER,
                        "config": _llm_config(),
                    },
                    "embedder": {
                        "provider": settings.LONG_TERM_MEMORY_EMBEDDER_PROVIDER,
                        "config": _embedder_config(),
                    },
                }
            )
            if inspect.isawaitable(memory):
                memory = await memory
            self._memory = cast(AsyncMemory, memory)
        return self._memory

    async def initialize(self) -> None:
        """预热 mem0 AsyncMemory 实例及其 pgvector 连接池.

        启动时调用一次，避免首次 search() 或 add() 承担约 130ms 的
        from_config + pgvector.list_cols() 冷启动成本。
        """
        if not settings.LONG_TERM_MEMORY_ENABLED:
            logger.info("memory_service_disabled")
            return
        await self._get_memory()
        logger.info("memory_service_initialized")

    async def search(self, user_id: str | None, query: str) -> str:
        """为指定用户搜索相关记忆.

        先查缓存；未命中时查询 mem0，并缓存成功结果。

        返回格式化后的 memory 字符串。失败或未提供 user_id 时返回空字符串；
        匿名 session 会跳过长期记忆，避免落入共享分区。
        """
        if not settings.LONG_TERM_MEMORY_ENABLED:
            return ""
        if user_id is None:
            return ""
        try:
            # 先检查缓存。
            key = cache_key("memory", str(user_id), query)
            cached = await cache_service.get(key)
            if cached is not None:
                logger.debug("memory_search_cache_hit", user_id=user_id)
                return cached

            memory = await self._get_memory()
            results = await memory.search(user_id=str(user_id), query=query)
            result = "\n".join([f"* {r['memory']}" for r in results["results"]])

            # 只缓存成功结果。
            if result:
                await cache_service.set(key, result)

            return result
        except Exception as e:
            logger.error("failed_to_get_relevant_memory", error=str(e), user_id=user_id, query=query)
            return ""

    async def add(self, user_id: str | None, messages: list[dict], metadata: dict | None = None) -> None:
        """把消息加入指定用户的长期记忆.

        ``user_id`` 为 ``None`` 时不执行操作，原因见 ``search``。
        """
        if not settings.LONG_TERM_MEMORY_ENABLED:
            return
        if user_id is None:
            return
        try:
            memory = await self._get_memory()
            await memory.add(messages, user_id=str(user_id), metadata=metadata)
            logger.info("long_term_memory_updated_successfully", user_id=user_id)
        except Exception as e:
            logger.exception("failed_to_update_long_term_memory", user_id=user_id, error=str(e))


memory_service = MemoryService()


def _llm_config() -> dict[str, object]:
    """返回 mem0 LLM provider 配置."""
    config: dict[str, object] = {
        "model": settings.LONG_TERM_MEMORY_MODEL,
        "api_key": settings.LONG_TERM_MEMORY_API_KEY,
    }
    _set_base_url(
        config,
        provider=settings.LONG_TERM_MEMORY_LLM_PROVIDER,
        base_url=settings.LONG_TERM_MEMORY_BASE_URL,
    )
    return config


def _embedder_config() -> dict[str, object]:
    """返回 mem0 embedding provider 配置."""
    config: dict[str, object] = {
        "model": settings.LONG_TERM_MEMORY_EMBEDDER_MODEL,
        "api_key": settings.LONG_TERM_MEMORY_EMBEDDER_API_KEY,
    }
    _set_base_url(
        config,
        provider=settings.LONG_TERM_MEMORY_EMBEDDER_PROVIDER,
        base_url=settings.LONG_TERM_MEMORY_EMBEDDER_BASE_URL,
    )
    return config


def _set_base_url(config: dict[str, object], *, provider: str, base_url: str) -> None:
    """按 mem0 provider 使用的字段名设置 base URL."""
    if not base_url:
        return

    match provider:
        case "openai":
            config["openai_base_url"] = base_url
        case "deepseek":
            config["deepseek_base_url"] = base_url
        case "ollama":
            config["ollama_base_url"] = base_url
        case "lmstudio":
            config["lmstudio_base_url"] = base_url
        case _:
            logger.warning("memory_provider_base_url_ignored", provider=provider)
