import time

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from config.settings import settings
from query_layer import (
    AsyncBatchedQueryService,
    RateLimitExceeded,
    SearchRequest,
    SearchResult,
)


class BatchSearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(default="default")
    per_request_rate_limit: bool = Field(default=False)


class SearchParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(default="default")


class SearchResponse(BaseModel):
    results: list[dict]
    from_cache: bool = False
    degraded: bool = False


def _coerce_bool(value: str) -> bool:
    normalized = value.lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise ValueError(f"Invalid boolean value: {value}")


def get_search_params(request: Request) -> SearchParams:
    return _parse_query_params(SearchParams, request)


def get_batch_search_params(request: Request) -> BatchSearchParams:
    return _parse_query_params(BatchSearchParams, request)


def _parse_query_params(model: type[BaseModel], request: Request) -> BaseModel:
    try:
        raw = dict(request.query_params)
        if "per_request_rate_limit" in raw:
            raw["per_request_rate_limit"] = _coerce_bool(raw["per_request_rate_limit"])
        return model.model_validate(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=[
                {
                    "type": "value_error",
                    "loc": ["query"],
                    "msg": str(exc),
                }
            ],
        ) from exc


def _apply_rate_limit_headers(response: Response) -> None:
    response.headers["X-RateLimit-Limit"] = str(
        int(settings.search_refill_rate * 60)
    )
    response.headers["X-RateLimit-Remaining"] = str(settings.SEARCH_RATE_LIMIT_BURST)
    response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 60)


def create_search_router(service: AsyncBatchedQueryService) -> APIRouter:
    router = APIRouter(tags=["Search"])

    @router.post(
        "/search",
        response_model=SearchResponse,
        operation_id="search-data",
        summary="Perform hybrid search across satellite and geospatial data",
        description=(
            "Executes a hybrid search across satellite and geospatial datasets. "
            "Rate limit: 300 requests per minute per client."
        ),
    )
    async def search_data(
        request: SearchRequest,
        response: Response,
        params: SearchParams = Depends(get_search_params),
    ) -> SearchResponse:
        _apply_rate_limit_headers(response)
        try:
            results = await service.batched_search(
                [request],
                client_id=params.client_id,
            )
            item = results[0]
            return SearchResponse(
                results=item.results,
                from_cache=item.from_cache,
                degraded=item.degraded,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=exc.message) from exc

    @router.post(
        "/search/batch",
        response_model=list[SearchResult],
        operation_id="batch-search",
        summary="Execute batched hybrid search",
        description=(
            "Runs multiple search requests in parallel. "
            "Rate limit: 300 requests per minute per client."
        ),
    )
    async def batch_search(
        requests: list[SearchRequest],
        response: Response,
        params: BatchSearchParams = Depends(get_batch_search_params),
    ) -> list[SearchResult]:
        _apply_rate_limit_headers(response)
        try:
            return await service.batched_search(
                requests,
                client_id=params.client_id,
                per_request_rate_limit=params.per_request_rate_limit,
            )
        except RateLimitExceeded as exc:
            raise HTTPException(status_code=429, detail=exc.message) from exc

    return router