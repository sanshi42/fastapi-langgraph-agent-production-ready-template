"""应用用户模型."""

from typing import (
    TYPE_CHECKING,
    List,
    Optional,
)

import bcrypt
from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.session import Session


class User(BaseModel, table=True):
    """用于存储用户账号的模型.

    Attributes:
        id: 主键。
        email: 用户 email，唯一。
        hashed_password: Bcrypt 哈希后的密码。
        username: 用户可选展示名称。
        created_at: 用户创建时间。
        sessions: 用户聊天 sessions 的关系字段。
    """

    id: int = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    username: Optional[str] = Field(default=None, index=False)
    sessions: List["Session"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """校验传入密码是否匹配哈希值."""
        return bcrypt.checkpw(password.encode("utf-8"), self.hashed_password.encode("utf-8"))

    @staticmethod
    def hash_password(password: str) -> str:
        """使用 bcrypt 对密码做哈希."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


# 避免循环导入。
from app.models.session import Session  # noqa: E402
