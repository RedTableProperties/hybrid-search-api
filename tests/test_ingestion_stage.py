import pytest

from pipelines import IngestionStage, PipelineEvent


@pytest.mark.asyncio
async def test_ingestion_stage_returns_raw_data():
    stage = IngestionStage()
    event = PipelineEvent(
        event_id="evt-ingest-1",
        trace_id="trace-1",
        payload={"data": {"source": "stac", "item_id": "scene-42"}},
        timestamp="2026-06-16T15:00:00Z",
    )

    result = await stage.process(event)

    assert result == {
        "status": "ingested",
        "raw_data": {"source": "stac", "item_id": "scene-42"},
    }
    assert stage.name == "ingestion"