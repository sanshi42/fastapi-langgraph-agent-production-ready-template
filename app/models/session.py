"""应用 session 模型."""

from typing import (
    TYPE_CHECKING,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Session(BaseModel, table=True):
    """用于存储聊天 session 的模型.

    Attributes:
        id: 主键。
        user_id: 指向用户的外键。
        name: session 名称，默认空字符串。
        username: session 创建时从用户复制的展示名称。
        created_at: session 创建时间。
        messages: session messages 的关系字段。
        user: session 所有者的关系字段。
    """

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str = Field(default="")
    username: Optional[str] = Field(default=None)
    user: "User" = Relationship(back_populates="sessions")
