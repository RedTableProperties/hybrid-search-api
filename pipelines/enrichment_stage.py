from pipelines.base_stage import BasePipelineStage, PipelineEvent
from resilience.resilience import ResilienceClient


class EnrichmentStage(BasePipelineStage):
    def __init__(self):
        super().__init__("enrichment")
        self.embedding_client = ResilienceClient(name="embedding", bulkhead_limit=5)

    async def _process(self, event: PipelineEvent):
        text = event.payload.get("text_for_embedding", "")
        embedding = await self.embedding_client.call(self._generate_embedding, text)
        return {"status": "enriched", "embedding": embedding}

    async def _generate_embedding(self, text: str):
        # Replace with actual embedding model
        return [0.0] * 768