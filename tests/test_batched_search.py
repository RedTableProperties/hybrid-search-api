import pytest

from query_layer import RateLimitExceeded, SearchRequest


@pytest.mark.asyncio
async def test_batched_search_returns_filtered_results(search_service, sample_vector):
    requests = [
        SearchRequest(
            query="pretoria homes",
            query_vector=sample_vector,
            filters={"city": "Pretoria"},
            limit=2,
        )
    ]

    results = await search_service.batched_search(requests)

    assert len(results) == 1
    assert results[0].request_index == 0
    assert len(results[0].results) == 2
    assert all(item["city"] == "Pretoria" for item in results[0].results)
    assert results[0].from_cache is False


@pytest.mark.asyncio
async def test_batched_search_uses_cache_on_second_call(search_service, sample_vector):
    request = SearchRequest(query="cached", query_vector=sample_vector, limit=3)
    requests = [request]

    first = await search_service.batched_search(requests)
    second = await search_service.batched_search(requests)

    assert len(first[0].results) == 3
    assert second[0].from_cache is True
    assert len(second[0].results) == 3


@pytest.mark.asyncio
async def test_batched_search_rate_limit_blocks_batch(search_service, sample_vector):
    requests = [
        SearchRequest(query="a", query_vector=sample_vector),
        SearchRequest(query="b", query_vector=sample_vector),
    ]

    for _ in range(50):
        await search_service.batched_search(requests, client_id="limited-client")

    with pytest.raises(RateLimitExceeded):
        await search_service.batched_search(requests, client_id="limited-client")


@pytest.mark.asyncio
async def test_batched_search_rejects_invalid_vector_dimension(sample_vector):
    with pytest.raises(ValueError):
        SearchRequest(query="bad", query_vector=sample_vector[:100])