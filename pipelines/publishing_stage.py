from pipelines.base_stage import BasePipelineStage, PipelineEvent
from pipelines.errors import PublishingError


class PublishingStage(BasePipelineStage):
    def __init__(self):
        super().__init__(name="publishing")

    async def _process(self, event: PipelineEvent):
        embedding = event.payload.get("embedding")
        if embedding is None:
            raise PublishingError(
                "missing embedding for publish",
                correlation_id=event.event_id,
            )

        return {
            "status": "published",
            "event_id": event.event_id,
            "embedding_dims": len(embedding),
        }