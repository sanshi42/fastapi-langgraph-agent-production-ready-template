"""Agent runtime cron 表达式支持."""

from datetime import datetime


def validate_cron(cron_expr: str) -> str | None:
    """校验五字段 cron 表达式."""
    fields = cron_expr.strip().split()
    if len(fields) != 5:
        return f"expected 5 fields, got {len(fields)}"

    bounds = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    for field, (low, high) in zip(fields, bounds, strict=True):
        error = _validate_field(field, low, high)
        if error:
            return error
    return None


def cron_matches(cron_expr: str, value: datetime) -> bool:
    """判断 cron 表达式是否匹配给定时间."""
    if validate_cron(cron_expr):
        return False

    minute, hour, day_of_month, month, day_of_week = cron_expr.strip().split()
    cron_day_of_week = (value.weekday() + 1) % 7

    if not (
        _field_matches(minute, value.minute)
        and _field_matches(hour, value.hour)
        and _field_matches(month, value.month)
    ):
        return False

    dom_matches = _field_matches(day_of_month, value.day)
    dow_matches = _field_matches(day_of_week, cron_day_of_week)
    if day_of_month == "*" and day_of_week == "*":
        return True
    if day_of_month == "*":
        return dow_matches
    if day_of_week == "*":
        return dom_matches
    return dom_matches or dow_matches


def _field_matches(field: str, value: int) -> bool:
    """判断单个 cron 字段是否匹配."""
    if field == "*":
        return True
    if field.startswith("*/"):
        step = int(field[2:])
        return step > 0 and value % step == 0
    if "," in field:
        return any(_field_matches(part.strip(), value) for part in field.split(","))
    if "-" in field:
        start, end = (int(part) for part in field.split("-", 1))
        return start <= value <= end
    return value == int(field)


def _validate_field(field: str, low: int, high: int) -> str | None:
    """校验单个 cron 字段."""
    if field == "*":
        return None
    if field.startswith("*/"):
        step = field[2:]
        if not step.isdigit() or int(step) <= 0:
            return f"invalid step: {field}"
        return None
    if "," in field:
        for part in field.split(","):
            error = _validate_field(part.strip(), low, high)
            if error:
                return error
        return None
    if "-" in field:
        left, right = field.split("-", 1)
        if not left.isdigit() or not right.isdigit():
            return f"invalid range: {field}"
        start, end = int(left), int(right)
        if start > end:
            return f"range starts after end: {field}"
        if start < low or end > high:
            return f"value out of range: {field}"
        return None
    if not field.isdigit():
        return f"invalid field: {field}"
    value = int(field)
    if value < low or value > high:
        return f"value out of range: {field}"
    return None
