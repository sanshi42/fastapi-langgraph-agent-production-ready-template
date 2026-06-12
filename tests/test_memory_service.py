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

    assert service._memory is None

    async def run():
        await service.initialize()

    asyncio.run(run())

    assert service._memory is created_memory


def test_memory_service_supports_awaitable_from_config(monkeypatch):
    """兼容类型声明中 from_config 返回 awaitable 的情况."""
    created_memory = object()

    class FakeAsyncMemory:
        @classmethod
        async def from_config(cls, config_dict):
            return created_memory

    service = memory.MemoryService()

    monkeypatch.setattr(memory, "AsyncMemory", FakeAsyncMemory)

    assert service._memory is None

    async def run():
        await service.initialize()

    asyncio.run(run())

    assert service._memory is created_memory
