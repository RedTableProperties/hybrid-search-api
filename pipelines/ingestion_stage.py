from pipelines.base_stage import BasePipelineStage, PipelineEvent


class IngestionStage(BasePipelineStage):
    def __init__(self):
        super().__init__(name="ingestion")

    async def _process(self, event: PipelineEvent):
        # Fetch from STAC / Planet / Airbus / etc.
        payload = event.payload
        # Add actual client calls here (with resilience already applied via base)
        return {"status": "ingested", "raw_data": payload.get("data")}