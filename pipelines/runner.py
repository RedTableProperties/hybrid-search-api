from typing import Iterable

from pipelines.base_stage import BasePipelineStage, PipelineEvent


def _next_event(root: PipelineEvent, stage_result: dict) -> PipelineEvent:
    return PipelineEvent(
        event_id=root.event_id,
        trace_id=root.trace_id,
        payload={**root.payload, **stage_result},
        timestamp=root.timestamp,
        metadata=root.metadata,
    )


async def run_pipeline(
    event: PipelineEvent,
    stages: Iterable[BasePipelineStage],
) -> dict:
    last_result: dict = {}
    for stage in stages:
        stage_input = event if not last_result else _next_event(event, last_result)
        last_result = await stage.process(stage_input)
        if last_result.get("status") == "degraded":
            return last_result
    return last_result