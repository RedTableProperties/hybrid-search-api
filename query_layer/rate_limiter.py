import time

from redis.asyncio import Redis

_TOKEN_BUCKET_LUA = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local refill_rate = tonumber(ARGV[2])
local now = tonumber(ARGV[3])

local data = redis.call('GET', key)
local tokens
local last_refill

if data then
    local sep = string.find(data, ':')
    tokens = tonumber(string.sub(data, 1, sep - 1))
    last_refill = tonumber(string.sub(data, sep + 1))
else
    tokens = capacity
    last_refill = now
end

local elapsed = math.max(0, now - last_refill)
tokens = math.min(capacity, tokens + elapsed * refill_rate)

if tokens < 1 then
    return 0
end

tokens = tokens - 1
redis.call('SET', key, tokens .. ':' .. now)
return 1
"""


class RedisTokenBucket:
    """Distributed token-bucket rate limiter backed by Redis."""

    def __init__(self, redis: Redis, key_prefix: str = "ratelimit"):
        self.redis = redis
        self.key_prefix = key_prefix
        self._script = None

    def _key(self, client_id: str) -> str:
        return f"{self.key_prefix}:{client_id}"

    async def _get_script(self):
        if self._script is None:
            self._script = self.redis.register_script(_TOKEN_BUCKET_LUA)
        return self._script

    async def allow_request(
        self,
        client_id: str,
        capacity: int,
        refill_rate: float,
    ) -> bool:
        script = await self._get_script()
        allowed = await script(
            keys=[self._key(client_id)],
            args=[capacity, refill_rate, time.time()],
        )
        return bool(allowed)

    async def reset(self, client_id: str) -> None:
        await self.redis.delete(self._key(client_id))