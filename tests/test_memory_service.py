"""Memory service 启动行为测试."""

import asyncio

from app.services import memory


def test_memory_service_uses_sync_from_config(monkeypatch):
    """AsyncMemory.from_config 是同步工厂方法，不应被 await."""
    created_memory = object()

    class FakeAsyncMemory:
        @classmethod
        def from_config(cls, config_dict):
            return created_memory

    service = memory.MemoryService()

    monkeypatch.setattr(memory, "AsyncMemory", FakeAsyncMemory)
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_ENABLED", True)

    assert service._memory is None

    async def run():
        await service.initialize()

    asyncio.run(run())

    assert service._memory is created_memory


def test_memory_service_passes_explicit_provider_config(monkeypatch):
    """mem0 配置应显式带上 provider、model、api key 和 base URL."""
    captured_config = {}
    created_memory = object()

    class FakeAsyncMemory:
        @classmethod
        def from_config(cls, config_dict):
            captured_config.update(config_dict)
            return created_memory

    service = memory.MemoryService()

    monkeypatch.setattr(memory, "AsyncMemory", FakeAsyncMemory)
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_ENABLED", True)
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_LLM_PROVIDER", "deepseek")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_MODEL", "deepseek-v4-flash")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_API_KEY", "memory-chat-key")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_BASE_URL", "https://api.deepseek.com")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_EMBEDDER_PROVIDER", "openai")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_EMBEDDER_MODEL", "text-embedding-3-small")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_EMBEDDER_API_KEY", "memory-embed-key")
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_EMBEDDER_BASE_URL", "https://embeddings.example/v1")

    async def run():
        await service.initialize()

    asyncio.run(run())

    assert service._memory is created_memory
    assert captured_config["llm"] == {
        "provider": "deepseek",
        "config": {
            "model": "deepseek-v4-flash",
            "api_key": "memory-chat-key",  # pragma: allowlist secret
            "deepseek_base_url": "https://api.deepseek.com",
        },
    }
    assert captured_config["embedder"] == {
        "provider": "openai",
        "config": {
            "model": "text-embedding-3-small",
            "api_key": "memory-embed-key",  # pragma: allowlist secret
            "openai_base_url": "https://embeddings.example/v1",
        },
    }


def test_memory_service_can_be_disabled(monkeypatch):
    """关闭长期记忆时不应初始化 mem0."""

    class FakeAsyncMemory:
        @classmethod
        def from_config(cls, config_dict):
            raise AssertionError("disabled memory should not initialize mem0")

    service = memory.MemoryService()

    monkeypatch.setattr(memory, "AsyncMemory", FakeAsyncMemory)
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_ENABLED", False)

    async def run():
        await service.initialize()
        result = await service.search("user-1", "hello")
        await service.add("user-1", [{"role": "user", "content": "hello"}])
        return result

    assert asyncio.run(run()) == ""
    assert service._memory is None


def test_memory_service_supports_awaitable_from_config(monkeypatch):
    """兼容类型声明中 from_config 返回 awaitable 的情况."""
    created_memory = object()

    class FakeAsyncMemory:
        @classmethod
        async def from_config(cls, config_dict):
            return created_memory

    service = memory.MemoryService()

    monkeypatch.setattr(memory, "AsyncMemory", FakeAsyncMemory)
    monkeypatch.setattr(memory.settings, "LONG_TERM_MEMORY_ENABLED", True)

    assert service._memory is None

    async def run():
        await service.initialize()

    asyncio.run(run())

    assert service._memory is created_memory
