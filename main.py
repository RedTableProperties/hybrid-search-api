"""FastAPI entrypoint for local development and contract testing."""

from contextlib import asynccontextmanager

import fakeredis.aioredis
from fastapi import FastAPI

from api.routes import create_search_router
from clients.faiss_index import InMemoryFaissIndex
from clients.postgres import InMemoryPostgresClient
from query_layer import AsyncBatchedQueryService, RedisTokenBucket

SAMPLE_VECTOR = [0.1] * 768

SAMPLE_ASSETS = {
    1: {"id": 1, "city": "Pretoria", "title": "Luxury Villa"},
    2: {"id": 2, "city": "Pretoria", "title": "Modern Apartment"},
    3: {"id": 3, "city": "Cape Town", "title": "Coastal Home"},
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_client = fakeredis.aioredis.FakeRedis(decode_responses=False)
    postgres = InMemoryPostgresClient(SAMPLE_ASSETS)
    faiss = InMemoryFaissIndex({asset_id: SAMPLE_VECTOR for asset_id in SAMPLE_ASSETS})
    rate_limiter = RedisTokenBucket(redis_client)
    service = AsyncBatchedQueryService(
        postgres_client=postgres,
        faiss_index=faiss,
        redis_client=redis_client,
        rate_limiter=rate_limiter,
    )
    app.include_router(create_search_router(service), prefix="/v1")
    yield
    await redis_client.aclose()


app = FastAPI(
    title="Web Data Discovery API",
    version="1.0.0",
    lifespan=lifespan,
)