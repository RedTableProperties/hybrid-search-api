import pytest

from pipelines.base_stage import PipelineEvent
from data_quality import DataQualityStage


@pytest.mark.asyncio
async def test_data_quality_stage_passes_valid_normalized_data():
    stage = DataQualityStage(check_files=["normalized_data.yml"])
    event = PipelineEvent(
        event_id="evt-dq-1",
        trace_id="trace-dq-1",
        payload={
            "normalized_data": {
                "scene_id": "SCENE-001",
                "caption": "Pretoria East",
            }
        },
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "quality_passed"
    assert result["used_cli"] is False
    assert result["used_gx"] is False
    assert result["soda_results"]["success"] is True


@pytest.mark.asyncio
async def test_data_quality_stage_returns_degraded_on_soda_failure():
    stage = DataQualityStage(check_files=["normalized_data.yml"])
    event = PipelineEvent(
        event_id="evt-dq-2",
        trace_id="trace-dq-2",
        payload={"normalized_data": {"caption": "missing scene id"}},
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "degraded"
    assert result["error_detail"]["error_type"] == "ValidationError"
    assert "failed_checks" in result["error_detail"]["context"]


@pytest.mark.asyncio
async def test_data_quality_stage_runs_great_expectations_when_enabled():
    stage = DataQualityStage(
        check_files=["normalized_data.yml"],
        use_gx=True,
        gx_expectation_suite="normalized_data",
    )
    event = PipelineEvent(
        event_id="evt-dq-3",
        trace_id="trace-dq-3",
        payload={
            "normalized_data": {
                "scene_id": "SCENE-003",
                "caption": "Centurion",
            }
        },
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "quality_passed"
    assert result["used_gx"] is True


@pytest.mark.asyncio
async def test_data_quality_stage_cli_mode_passes():
    stage = DataQualityStage(check_files=["normalized_data.yml"], use_cli=True)
    event = PipelineEvent(
        event_id="evt-dq-4",
        trace_id="trace-dq-4",
        payload={
            "normalized_data": {
                "scene_id": "SCENE-004",
                "caption": "Pretoria East",
            }
        },
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "quality_passed"
    assert result["used_cli"] is True
    assert result["soda_results"]["success"] is True


@pytest.mark.asyncio
async def test_data_quality_stage_cli_mode_returns_degraded_on_failure():
    stage = DataQualityStage(check_files=["normalized_data.yml"], use_cli=True)
    event = PipelineEvent(
        event_id="evt-dq-5",
        trace_id="trace-dq-5",
        payload={"normalized_data": {"caption": "missing scene id"}},
        timestamp="2026-06-16T20:00:00Z",
    )

    result = await stage.process(event)

    assert result["status"] == "degraded"
    assert result["error_detail"]["error_type"] == "ValidationError"