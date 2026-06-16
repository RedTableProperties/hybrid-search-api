import json

import fakeredis.aioredis
import pytest

from clients.faiss_index import InMemoryFaissIndex
from clients.postgres import InMemoryPostgresClient
from query_layer import AsyncBatchedQueryService, RedisTokenBucket


@pytest.fixture
def sample_vector():
    return [0.1] * 768


@pytest.fixture
def sample_assets():
    return {
        1: {"id": 1, "city": "Pretoria", "title": "Luxury Villa"},
        2: {"id": 2, "city": "Pretoria", "title": "Modern Apartment"},
        3: {"id": 3, "city": "Cape Town", "title": "Coastal Home"},
    }


@pytest.fixture
def sample_vectors(sample_vector):
    return {1: sample_vector, 2: sample_vector, 3: sample_vector}


@pytest.fixture
async def redis_client():
    client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    yield client
    await client.aclose()


@pytest.fixture
async def search_service(sample_assets, sample_vectors, redis_client):
    postgres = InMemoryPostgresClient(sample_assets)
    faiss = InMemoryFaissIndex(sample_vectors)
    rate_limiter = RedisTokenBucket(redis_client)
    return AsyncBatchedQueryService(
        postgres_client=postgres,
        faiss_index=faiss,
        redis_client=redis_client,
        rate_limiter=rate_limiter,
        cache_ttl=60,
    )


async def seed_cache(redis_client, cache_key: str, payload):
    await redis_client.set(cache_key, json.dumps(payload), ex=60)