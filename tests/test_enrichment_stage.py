import pytest

from pipelines import EnrichmentStage, PipelineEvent


@pytest.mark.asyncio
async def test_enrichment_stage_returns_embedding():
    stage = EnrichmentStage()
    event = PipelineEvent(
        event_id="evt-enrich-1",
        trace_id="trace-1",
        payload={"text_for_embedding": "Pretoria East luxury estate"},
        timestamp="2026-06-16T15:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "enriched"
    assert len(result["embedding"]) == 768
    assert all(value == 0.0 for value in result["embedding"])
    assert stage.name == "enrichment"


@pytest.mark.asyncio
async def test_enrichment_stage_defaults_empty_text():
    stage = EnrichmentStage()
    event = PipelineEvent(
        event_id="evt-enrich-2",
        trace_id="trace-1",
        payload={},
        timestamp="2026-06-16T15:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "enriched"
    assert len(result["embedding"]) == 768