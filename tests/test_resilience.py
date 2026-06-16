import pytest

from resilience import BulkheadFull, ResilienceClient


@pytest.mark.asyncio
async def test_resilience_client_executes_async_function():
    client = ResilienceClient(name="test", bulkhead_limit=2)

    async def add_one(value: int) -> int:
        return value + 1

    result = await client.call(add_one, 1)
    assert result == 2


@pytest.mark.asyncio
async def test_resilience_client_invokes_fallback():
    client = ResilienceClient(name="test-fallback", fail_max=1, reset_timeout=1)

    async def always_fail() -> int:
        raise ConnectionError("boom")

    async def fallback() -> int:
        return 42

    result = await client.call(always_fail, fallback=fallback)
    assert result == 42


@pytest.mark.asyncio
async def test_bulkhead_rejects_when_full():
    import asyncio

    client = ResilienceClient(name="test-bulkhead", bulkhead_limit=1)

    async def slow():
        await asyncio.sleep(0.05)
        return "ok"

    first_task = asyncio.create_task(client.call(slow))
    await asyncio.sleep(0.01)

    with pytest.raises(BulkheadFull):
        await client.call(slow)

    assert await first_task == "ok"