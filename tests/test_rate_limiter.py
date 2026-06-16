import pytest

from query_layer.rate_limiter import RedisTokenBucket


@pytest.mark.asyncio
async def test_token_bucket_allows_burst_then_blocks(redis_client):
    limiter = RedisTokenBucket(redis_client)
    capacity = 3
    refill_rate = 0.0

    assert await limiter.allow_request("client-a", capacity, refill_rate)
    assert await limiter.allow_request("client-a", capacity, refill_rate)
    assert await limiter.allow_request("client-a", capacity, refill_rate)
    assert not await limiter.allow_request("client-a", capacity, refill_rate)