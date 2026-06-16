import pytest

from pipelines import (
    BasePipelineStage,
    EnrichmentError,
    ErrorSeverity,
    IngestionError,
    PermanentError,
    PipelineEvent,
    TransientError,
    ValidationError,
)


def test_base_pipeline_error_to_dict():
    error = IngestionError(
        "STAC timeout",
        severity=ErrorSeverity.HIGH,
        correlation_id="evt-99",
        context={"source": "planet"},
    )

    assert error.to_dict() == {
        "error_type": "IngestionError",
        "message": "STAC timeout",
        "severity": "high",
        "correlation_id": "evt-99",
        "context": {"source": "planet"},
    }


@pytest.mark.asyncio
async def test_base_stage_includes_pipeline_error_detail():
    class BrokenStage(BasePipelineStage):
        async def _process(self, event: PipelineEvent):
            raise EnrichmentError(
                "embedding service unavailable",
                correlation_id=event.event_id,
            )

    stage = BrokenStage("enrichment")
    event = PipelineEvent(
        event_id="evt-err-1",
        trace_id="trace-1",
        payload={},
        timestamp="2026-06-16T15:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "degraded"
    assert result["error_detail"]["error_type"] == "EnrichmentError"
    assert result["error_detail"]["correlation_id"] == "evt-err-1"


@pytest.mark.asyncio
async def test_base_stage_omits_error_detail_for_generic_exceptions():
    class BrokenStage(BasePipelineStage):
        async def _process(self, event: PipelineEvent):
            raise RuntimeError("unexpected")

    result = await BrokenStage("broken").process(
        PipelineEvent(
            event_id="evt-err-2",
            trace_id="trace-1",
            payload={},
            timestamp="2026-06-16T15:00:00Z",
        )
    )

    assert "error_detail" not in result


def test_error_hierarchy():
    assert issubclass(ValidationError, PermanentError)
    assert issubclass(IngestionError, TransientError)
    assert issubclass(EnrichmentError, TransientError)