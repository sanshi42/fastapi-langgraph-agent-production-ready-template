"""Langfuse 可观测性启动行为测试."""

from app.core import observability


def test_langfuse_init_skips_auth_when_tracing_disabled(monkeypatch):
    """LANGFUSE_TRACING_ENABLED=false 时不应初始化 Langfuse 客户端."""

    class FailingLangfuse:
        def __init__(self, **kwargs):
            raise AssertionError("Langfuse should not be initialized")

    monkeypatch.setattr(observability.settings, "LANGFUSE_TRACING_ENABLED", False)
    monkeypatch.setattr(observability, "Langfuse", FailingLangfuse)

    assert observability.langfuse_init() is False


def test_langfuse_init_disables_tracing_when_auth_check_fails(monkeypatch):
    """Langfuse 认证异常不应阻止应用启动."""

    class UnauthenticatedLangfuse:
        def __init__(self, **kwargs):
            pass

        def auth_check(self) -> bool:
            raise RuntimeError("invalid credentials")

    monkeypatch.setattr(observability.settings, "LANGFUSE_TRACING_ENABLED", True)
    monkeypatch.setattr(observability, "Langfuse", UnauthenticatedLangfuse)

    assert observability.langfuse_init() is False
    assert observability.settings.LANGFUSE_TRACING_ENABLED is False
