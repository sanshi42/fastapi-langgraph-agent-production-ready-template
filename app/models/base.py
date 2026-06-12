"""所有模型共享的基础模型."""

from datetime import datetime, UTC
from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """包含公共字段的基础模型."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
