"""应用输入清洗工具函数."""

import html
import re
from typing import (
    Any,
    Dict,
    List,
)


def sanitize_string(value: str) -> str:
    """清洗字符串，降低 XSS 和其他注入攻击风险.

    Args:
        value: 待清洗字符串。

    Returns:
        str: 清洗后的字符串。
    """
    # 非字符串输入先转成字符串。
    if not isinstance(value, str):
        value = str(value)

    # HTML 转义以降低 XSS 风险。
    value = html.escape(value)

    # 移除可能已经被转义的 script 标签。
    value = re.sub(r"&lt;script.*?&gt;.*?&lt;/script&gt;", "", value, flags=re.DOTALL)

    # 移除空字节。
    value = value.replace("\0", "")

    return value


def sanitize_email(email: str) -> str:
    """清洗 email 地址.

    Args:
        email: 待清洗 email 地址。

    Returns:
        str: 清洗后的 email 地址。
    """
    # 基础清洗。
    email = sanitize_string(email)

    # 简单检查 email 格式。
    if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError("Invalid email format")

    return email.lower()


def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """递归清洗字典中的所有字符串值.

    Args:
        data: 待清洗字典。

    Returns:
        Dict[str, Any]: 清洗后的字典。
    """
    sanitized = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = sanitize_list(value)
        else:
            sanitized[key] = value
    return sanitized


def sanitize_list(data: List[Any]) -> List[Any]:
    """递归清洗列表中的所有字符串值.

    Args:
        data: 待清洗列表。

    Returns:
        List[Any]: 清洗后的列表。
    """
    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_string(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_list(item))
        else:
            sanitized.append(item)
    return sanitized


def validate_password_strength(password: str) -> bool:
    """校验密码强度.

    Args:
        password: 待校验密码。

    Returns:
        bool: 密码强度是否达标。

    Raises:
        ValueError: 密码强度不足时抛出，并说明原因。
    """
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

    return True
