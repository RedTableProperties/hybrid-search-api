import pytest

from pipelines.base_stage import PipelineEvent
from pipelines.enrichment_stage import EnrichmentStage
from pipelines.ingestion_stage import IngestionStage
from pipelines.publishing_stage import PublishingStage
from pipelines.runner import _next_event


@pytest.mark.asyncio
async def test_end_to_end_pipeline_with_sample_data():
    event = PipelineEvent(
        event_id="test-e2e-001",
        trace_id="trace-123",
        payload={
            "source": "test",
            "data": {"scene_id": "SCENE-001", "caption": "Pretoria East"},
            "text_for_embedding": "Pretoria East satellite scene",
        },
        timestamp="2026-06-16T20:00:00Z",
    )

    stages = [IngestionStage(), EnrichmentStage(), PublishingStage()]

    current = event
    last_result = {}
    for stage in stages:
        stage_input = current if isinstance(current, PipelineEvent) else _next_event(event, last_result)
        last_result = await stage.process(stage_input)
        assert last_result.get("status") != "degraded"
        current = last_result

    assert current.get("status") == "published"
    assert current.get("event_id") == "test-e2e-001"
    assert current.get("embedding_dims") == 768