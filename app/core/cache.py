"""支持可选 Redis/Valkey 后端的缓存服务.

配置 VALKEY_HOST 时，通过 Redis client 连接 Valkey 做分布式缓存。
否则回退到简单的内存 TTL 缓存。
"""

import hashlib
import time
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Optional,
    cast,
)

from app.core.config import settings
from app.core.logging import logger

# 尝试导入 redis；它是可选依赖。
if TYPE_CHECKING:
    from redis.asyncio import Redis  # pyright: ignore[reportMissingImports]

    REDIS_AVAILABLE = True
else:
    try:
        from redis.asyncio import Redis

        REDIS_AVAILABLE = True
    except ImportError:
        logger.debug("redis_not_available")
        Redis = None
        REDIS_AVAILABLE = False


class InMemoryCacheService:
    """Valkey 不可用时使用的简单内存 TTL 缓存."""

    def __init__(self, default_ttl: int = 60):
        """初始化内存缓存.

        Args:
            default_ttl: 缓存条目的默认存活秒数。
        """
        self._cache: dict[str, tuple[float, str]] = {}
        self._default_ttl = default_ttl

    async def initialize(self) -> None:
        """内存缓存无需额外初始化."""
        logger.info("cache_initialized", backend="in_memory", ttl=self._default_ttl)

    async def get(self, key: str) -> Optional[str]:
        """从缓存读取值.

        Args:
            key: 缓存 key。

        Returns:
            缓存值；未命中或已过期时返回 None。
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._cache[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """把值写入缓存并设置 TTL.

        Args:
            key: 缓存 key。
            value: 要缓存的值。
            ttl: 存活秒数；未指定时使用默认值。
        """
        expires_at = time.monotonic() + (ttl or self._default_ttl)
        self._cache[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        """从缓存删除指定值.

        Args:
            key: 缓存 key。
        """
        self._cache.pop(key, None)

    async def close(self) -> None:
        """清空内存缓存."""
        self._cache.clear()


class ValkeyCacheService:
    """用于分布式缓存的 Redis/Valkey 后端."""

    def __init__(self, default_ttl: int = 60):
        """初始化基于 Redis client 的缓存服务.

        Args:
            default_ttl: 缓存条目的默认存活秒数。
        """
        self._client: Optional[Redis] = None
        self._default_ttl = default_ttl

    async def initialize(self) -> None:
        """连接 Redis/Valkey 服务."""
        client = Redis(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            db=settings.VALKEY_DB,
            password=settings.VALKEY_PASSWORD or None,
            max_connections=settings.VALKEY_MAX_CONNECTIONS,
            decode_responses=True,
        )
        await cast(Awaitable[bool], client.ping())
        self._client = client
        logger.info(
            "cache_initialized",
            backend="redis",
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            ttl=self._default_ttl,
        )

    async def get(self, key: str) -> Optional[str]:
        """从 Valkey 读取值.

        Args:
            key: 缓存 key。

        Returns:
            缓存值；未命中时返回 None。
        """
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """把值写入 Valkey 并设置 TTL.

        Args:
            key: 缓存 key。
            value: 要缓存的值。
            ttl: 存活秒数；未指定时使用默认值。
        """
        if not self._client:
            return
        try:
            await self._client.set(key, value, ex=(ttl or self._default_ttl))
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        """从 Valkey 删除指定值.

        Args:
            key: 缓存 key。
        """
        if not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))

    async def close(self) -> None:
        """关闭 Valkey 连接."""
        if self._client:
            await self._client.aclose()
            logger.info("cache_connection_closed")


def _create_cache_service() -> InMemoryCacheService | ValkeyCacheService:
    """根据配置创建合适的缓存服务.

    Returns:
        缓存服务实例；配置 Redis 时使用 Redis，否则使用内存缓存。
    """
    ttl = settings.CACHE_TTL_SECONDS

    if settings.VALKEY_HOST and REDIS_AVAILABLE:
        return ValkeyCacheService(default_ttl=ttl)

    if settings.VALKEY_HOST and not REDIS_AVAILABLE:
        logger.warning(
            "redis_client_not_installed",
            hint="install with: uv add redis --optional cache",
        )

    return InMemoryCacheService(default_ttl=ttl)


def cache_key(prefix: str, *parts: str) -> str:
    """用前缀和哈希后的组成部分构建缓存 key.

    Args:
        prefix: 缓存 key 前缀，例如 "memory"。
        *parts: 要纳入 key 的其他组成部分。

    Returns:
        稳定可复现的缓存 key 字符串。
    """
    raw = ":".join(parts)
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{hashed}"


# 全局缓存服务单例，在 lifespan 中懒初始化。
cache_service = _create_cache_service()
