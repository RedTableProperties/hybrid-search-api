import pytest

from observability import REQUESTS
from pipelines import BasePipelineStage, PipelineEvent


def _sample_event() -> PipelineEvent:
    return PipelineEvent(
        event_id="evt-1",
        trace_id="trace-1",
        payload={"query": "pretoria"},
        timestamp="2026-06-16T15:00:00Z",
    )


class EchoStage(BasePipelineStage):
    async def _process(self, event: PipelineEvent):
        return {"status": "ok", "event_id": event.event_id, "payload": event.payload}


class FailingStage(BasePipelineStage):
    async def _process(self, event: PipelineEvent):
        raise RuntimeError("stage exploded")


@pytest.mark.asyncio
async def test_pipeline_stage_returns_process_result():
    stage = EchoStage("echo")
    result = await stage.process(_sample_event())
    assert result == {
        "status": "ok",
        "event_id": "evt-1",
        "payload": {"query": "pretoria"},
    }


@pytest.mark.asyncio
async def test_pipeline_stage_returns_degraded_fallback_on_failure():
    stage = FailingStage("failing")
    result = await stage.process(_sample_event())
    assert result["status"] == "degraded"
    assert result["stage"] == "failing"
    assert result["event_id"] == "evt-1"
    assert "stage exploded" in result["error"]


@pytest.mark.asyncio
async def test_pipeline_stage_records_red_metrics():
    before = REQUESTS.labels(stage="echo-metrics")._value.get()
    stage = EchoStage("echo-metrics")
    await stage.process(_sample_event())
    after = REQUESTS.labels(stage="echo-metrics")._value.get()
    assert after == before + 1