"""应用限流配置.

本模块使用 slowapi 配置限流，默认限流值来自应用配置。
限流按远端 IP 地址生效。

配置 Valkey 时，它会作为分布式存储后端，确保多个应用实例之间的限流正确协同。
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings
from app.core.logging import logger

# 配置 Valkey 时构建 storage URI。
_storage_uri = None
if settings.VALKEY_HOST:
    _password_part = f":{settings.VALKEY_PASSWORD}@" if settings.VALKEY_PASSWORD else ""
    _storage_uri = f"redis://{_password_part}{settings.VALKEY_HOST}:{settings.VALKEY_PORT}/{settings.VALKEY_DB}"
    logger.info("rate_limiter_using_valkey", host=settings.VALKEY_HOST, port=settings.VALKEY_PORT)

# 初始化限流器；没有 Valkey 时使用内存存储。
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=settings.RATE_LIMIT_DEFAULT,  # pyright: ignore[reportArgumentType]
    storage_uri=_storage_uri,
)
