"""应用 thread 模型."""

from datetime import (
    UTC,
    datetime,
)

from sqlmodel import (
    Field,
    SQLModel,
)


class Thread(SQLModel, table=True):
    """用于存储对话 thread 的模型.

    Attributes:
        id: 主键。
        created_at: thread 创建时间。
        messages: 当前 thread 中 messages 的关系字段。
    """

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
