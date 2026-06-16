import logging
from typing import Any, Dict

from pydantic import BaseModel

from observability.observability import record_red_metrics, traced
from pipelines.errors import BasePipelineError
from resilience.resilience import ResilienceClient

logger = logging.getLogger(__name__)


class PipelineEvent(BaseModel):
    event_id: str
    trace_id: str
    payload: Dict[str, Any]
    timestamp: str
    metadata: Dict[str, Any] = {}


class BasePipelineStage:
    def __init__(self, name: str):
        self.name = name
        self.resilience = ResilienceClient(name=name, bulkhead_limit=10)

    async def process(self, event: PipelineEvent):
        record_red_metrics(self.name)
        with traced(self.name):
            try:
                return await self.resilience.call(self._process, event)
            except Exception as e:
                logger.error("[%s] Processing failed", self.name, exc_info=True)
                return await self._handle_failure(event, e)

    async def _process(self, event: PipelineEvent):
        raise NotImplementedError

    async def _handle_failure(self, event: PipelineEvent, error: Exception):
        logger.warning("[%s] Triggering fallback due to: %s", self.name, error)
        result = {
            "status": "degraded",
            "stage": self.name,
            "event_id": event.event_id,
            "error": str(error),
        }
        if isinstance(error, BasePipelineError):
            result["error_detail"] = error.to_dict()
        return result