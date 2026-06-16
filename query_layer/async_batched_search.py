import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, List, Optional

import numpy as np
from opentelemetry import trace
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field, field_validator
from pybreaker import CircuitBreakerError
from redis.asyncio import Redis

from config.settings import settings
from resilience.resilience import BulkheadFull, ResilienceClient

from .exceptions import RateLimitExceeded
from .rate_limiter import RedisTokenBucket

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)

SEARCH_REQUESTS_TOTAL = Counter(
    "search_requests_total",
    "Total searches by outcome",
    ["status"],
)
SEARCH_LATENCY_SECONDS = Histogram(
    "search_latency_seconds",
    "End-to-end batched search latency",
)
SEARCH_EMPTY_RESULTS_TOTAL = Counter(
    "search_empty_results_total",
    "Searches that returned zero hits",
)
PRE_FILTER_CANDIDATES = Histogram(
    "pre_filter_candidates",
    "Candidate count after metadata/geo pre-filter",
)
RATE_LIMIT_HITS = Counter(
    "rate_limit_hits_total",
    "Rate limit rejections",
    ["mode"],
)


class SearchRequest(BaseModel):
    query: str = Field(default="", max_length=500)
    query_vector: List[float]
    filters: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=100)
    ef: int = Field(default=settings.DEFAULT_EF, ge=1, le=512)
    use_reranking: bool = False

    @field_validator("query_vector")
    @classmethod
    def validate_vector_dimension(cls, value: List[float]) -> List[float]:
        if len(value) not in settings.VECTOR_DIMS:
            raise ValueError(
                f"Invalid embedding dimension {len(value)}; "
                f"expected one of {settings.VECTOR_DIMS}"
            )
        return value

    @field_validator("filters")
    @classmethod
    def sanitize_filters(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if len(str(value)) > 4000:
            raise ValueError("Filter payload too large")
        return value

    @field_validator("use_reranking", mode="before")
    @classmethod
    def strict_use_reranking(cls, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        raise ValueError("use_reranking must be a boolean")


class SearchResult(BaseModel):
    request_index: int
    results: List[Dict[str, Any]]
    from_cache: bool = False
    degraded: bool = False


class AsyncBatchedQueryService:
    """
    Async batched hybrid search with metadata pre-filtering and vector retrieval.

    Features:
    - Circuit breaker + retry + bulkhead via ResilienceClient
    - Redis cache-aside with stale fallback when circuits open
    - Dynamic efSearch tuning based on candidate set size
    - Batch or per-request rate limiting
    """

    def __init__(
        self,
        postgres_client,
        faiss_index,
        redis_client: Redis,
        rate_limiter: Optional[RedisTokenBucket] = None,
        cache_ttl: Optional[int] = None,
    ):
        self.postgres = postgres_client
        self.faiss = faiss_index
        self.redis = redis_client
        self.rate_limiter = rate_limiter
        self.cache_ttl = cache_ttl or settings.CACHE_TTL

        self.postgres_resilience = ResilienceClient(
            name="postgres",
            fail_max=settings.POSTGRES_CIRCUIT_FAIL_MAX,
            reset_timeout=settings.POSTGRES_CIRCUIT_RESET_TIMEOUT,
            bulkhead_limit=20,
        )
        self.faiss_resilience = ResilienceClient(
            name="faiss",
            fail_max=settings.FAISS_CIRCUIT_FAIL_MAX,
            reset_timeout=settings.FAISS_CIRCUIT_RESET_TIMEOUT,
            bulkhead_limit=8,
        )

    def _make_cache_key(self, request: SearchRequest) -> str:
        vec_hash = hashlib.md5(
            np.asarray(request.query_vector, dtype=np.float32).tobytes()
        ).hexdigest()
        key_data = {
            "q": request.query,
            "vec": vec_hash,
            "filters": request.filters,
            "limit": request.limit,
            "ef": request.ef,
            "rerank": request.use_reranking,
        }
        digest = hashlib.md5(
            json.dumps(key_data, sort_keys=True, default=str).encode()
        ).hexdigest()
        return f"search:{digest}"

    def _tune_ef(self, request: SearchRequest, candidate_count: int) -> int:
        ef = request.ef
        if candidate_count > 5000:
            ef = min(ef * 2, 256)
        elif candidate_count < 500:
            ef = max(ef // 2, settings.DEFAULT_EF // 2)
        return ef

    async def batched_search(
        self,
        requests: List[SearchRequest],
        client_id: str = "default",
        per_request_rate_limit: bool = False,
    ) -> List[SearchResult]:
        start_time = time.time()

        with tracer.start_as_current_span("query_layer.batched_search"):
            if not requests:
                return []

            await self._enforce_rate_limit(
                requests,
                client_id=client_id,
                per_request=per_request_rate_limit,
            )

            results = await asyncio.gather(
                *[self._search_one(index, request) for index, request in enumerate(requests)]
            )

            duration = time.time() - start_time
            SEARCH_LATENCY_SECONDS.observe(duration)

            for result in results:
                if result.from_cache and result.degraded:
                    SEARCH_REQUESTS_TOTAL.labels(status="degraded").inc()
                elif result.from_cache:
                    SEARCH_REQUESTS_TOTAL.labels(status="cache_hit").inc()
                elif not result.results:
                    SEARCH_REQUESTS_TOTAL.labels(status="empty").inc()
                else:
                    SEARCH_REQUESTS_TOTAL.labels(status="success").inc()

            return list(results)

    async def _enforce_rate_limit(
        self,
        requests: List[SearchRequest],
        client_id: str,
        per_request: bool,
    ) -> None:
        if not self.rate_limiter:
            return

        refill_rate = settings.search_refill_rate
        capacity = settings.SEARCH_RATE_LIMIT_BURST

        if per_request:
            for index in range(len(requests)):
                allowed = await self.rate_limiter.allow_request(
                    f"{client_id}:{index}",
                    capacity=capacity,
                    refill_rate=refill_rate,
                )
                if not allowed:
                    RATE_LIMIT_HITS.labels(mode="per_request").inc()
                    raise RateLimitExceeded(
                        f"Rate limit exceeded for request {index}",
                        request_index=index,
                    )
        else:
            allowed = await self.rate_limiter.allow_request(
                client_id,
                capacity=capacity,
                refill_rate=refill_rate,
            )
            if not allowed:
                RATE_LIMIT_HITS.labels(mode="batch").inc()
                raise RateLimitExceeded("Rate limit exceeded for batch")

    async def _search_one(self, index: int, request: SearchRequest) -> SearchResult:
        cache_key = self._make_cache_key(request)

        cached = await self._try_cache_fallback(request)
        if cached is not None:
            return SearchResult(request_index=index, results=cached, from_cache=True)

        try:
            candidate_ids = await self.postgres_resilience.call(
                self.postgres.get_candidate_ids,
                request.filters,
            )
        except (CircuitBreakerError, BulkheadFull):
            cached = await self._try_cache_fallback(request)
            return SearchResult(
                request_index=index,
                results=cached or [],
                from_cache=bool(cached),
                degraded=True,
            )
        except Exception:
            logger.exception("Pre-filter failed for request %s", index)
            cached = await self._try_cache_fallback(request)
            if cached is not None:
                return SearchResult(
                    request_index=index,
                    results=cached,
                    from_cache=True,
                    degraded=True,
                )
            return SearchResult(request_index=index, results=[])

        if not candidate_ids:
            SEARCH_EMPTY_RESULTS_TOTAL.inc()
            return SearchResult(request_index=index, results=[])

        if len(candidate_ids) > settings.MAX_CANDIDATE_IDS:
            candidate_ids = candidate_ids[: settings.MAX_CANDIDATE_IDS]

        PRE_FILTER_CANDIDATES.observe(len(candidate_ids))
        ef = self._tune_ef(request, len(candidate_ids))
        allowed_ids = np.array(sorted(candidate_ids), dtype="int64")

        try:
            _distances, indices = await self.faiss_resilience.call(
                self.faiss.search_with_ids,
                query_vector=request.query_vector,
                allowed_ids=allowed_ids,
                k=request.limit,
                ef=ef,
            )

            valid_ids = indices[0][indices[0] != -1].tolist()
            if not valid_ids:
                SEARCH_EMPTY_RESULTS_TOTAL.inc()
                return SearchResult(request_index=index, results=[])

            assets = await self.postgres_resilience.call(
                self.postgres.get_assets_by_ids,
                valid_ids,
            )

            await self.redis.set(
                cache_key,
                json.dumps(assets),
                ex=self.cache_ttl,
            )
            return SearchResult(request_index=index, results=assets)

        except (CircuitBreakerError, BulkheadFull):
            cached = await self._try_cache_fallback(request)
            return SearchResult(
                request_index=index,
                results=cached or [],
                from_cache=bool(cached),
                degraded=True,
            )
        except Exception:
            logger.exception("Vector search failed for request %s", index)
            cached = await self._try_cache_fallback(request)
            if cached is not None:
                return SearchResult(
                    request_index=index,
                    results=cached,
                    from_cache=True,
                    degraded=True,
                )
            return SearchResult(request_index=index, results=[])

    async def _try_cache_fallback(
        self,
        request: SearchRequest,
    ) -> Optional[List[Dict[str, Any]]]:
        cache_key = self._make_cache_key(request)
        try:
            cached = await self.redis.get(cache_key)
            if not cached:
                return None
            return json.loads(cached)
        except Exception:
            logger.exception("Cache fallback read failed for key %s", cache_key)
            return None