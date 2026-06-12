"""所有端点共享的基础响应 schema."""

from uuid import UUID, uuid4

from asgi_correlation_id import correlation_id
from pydantic import BaseModel, Field


def _get_request_id() -> UUID:
    """返回当前请求的 correlation ID；没有时生成新的 UUID 兜底."""
    value = correlation_id.get()
    return UUID(value) if value else uuid4()


class BaseResponse(BaseModel):
    """所有端点响应继承的基础响应模型.

    request_id 会从 CorrelationIdMiddleware 的 ContextVar 自动填充，
    端点无需显式传入。
    """

    request_id: UUID = Field(default_factory=_get_request_id, description="当前请求的唯一标识")
