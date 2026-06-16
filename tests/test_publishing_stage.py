import pytest

from pipelines import PipelineEvent, PublishingStage


@pytest.mark.asyncio
async def test_publishing_stage_publishes_enriched_payload():
    stage = PublishingStage()
    event = PipelineEvent(
        event_id="evt-pub-1",
        trace_id="trace-1",
        payload={"embedding": [0.1] * 768, "status": "enriched"},
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "published"
    assert result["embedding_dims"] == 768


@pytest.mark.asyncio
async def test_publishing_stage_returns_degraded_without_embedding():
    stage = PublishingStage()
    event = PipelineEvent(
        event_id="evt-pub-2",
        trace_id="trace-1",
        payload={"status": "enriched"},
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "degraded"
    assert result["error_detail"]["error_type"] == "PublishingError"