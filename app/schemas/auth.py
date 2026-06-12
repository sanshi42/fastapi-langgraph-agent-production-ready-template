"""应用认证相关 schema."""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)

from app.schemas.base import BaseResponse


class Token(BaseModel):
    """认证 token 模型.

    Attributes:
        access_token: JWT access token。
        token_type: token 类型，固定为 "bearer"。
        expires_at: token 过期时间戳。
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="token 类型")
    expires_at: datetime = Field(..., description="token 过期时间戳")


class TokenResponse(BaseResponse):
    """登录端点响应模型.

    Attributes:
        access_token: JWT access token。
        token_type: token 类型，固定为 "bearer"。
        expires_at: token 过期时间。
    """

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="token 类型")
    expires_at: datetime = Field(..., description="token 过期时间")


class UserCreate(BaseModel):
    """用户注册请求模型.

    Attributes:
        email: 用户 email 地址。
        password: 用户密码。
        username: 可选展示名称。
    """

    email: EmailStr = Field(..., description="用户 email 地址")
    password: SecretStr = Field(..., description="用户密码", min_length=8, max_length=64)
    username: str | None = Field(default=None, description="可选展示名称", max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """校验密码强度.

        Args:
            v: 待校验密码。

        Returns:
            SecretStr: 校验通过的密码。

        Raises:
            ValueError: 密码强度不足时抛出。
        """
        password = v.get_secret_value()

        # 检查常见密码强度要求。
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")

        return v


class UserResponse(BaseResponse):
    """用户操作响应模型.

    Attributes:
        id: 用户 ID。
        email: 用户 email 地址。
        username: 可选展示名称。
        token: 认证 token。
    """

    id: int = Field(..., description="用户 ID")
    email: str = Field(..., description="用户 email 地址")
    username: str | None = Field(default=None, description="可选展示名称")
    token: Token = Field(..., description="认证 token")


class SessionResponse(BaseResponse):
    """session 创建响应模型.

    Attributes:
        session_id: 聊天 session 的唯一标识。
        name: session 名称，默认空字符串。
        token: session 的认证 token。
    """

    session_id: str = Field(..., description="聊天 session 的唯一标识")
    name: str = Field(default="", description="session 名称", max_length=100)
    token: Token = Field(..., description="session 的认证 token")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """清洗 session 名称.

        Args:
            v: 待清洗名称。

        Returns:
            str: 清洗后的名称。
        """
        # 移除可能有害的字符。
        sanitized = re.sub(r'[<>{}[\]()\'"`]', "", v)
        return sanitized
