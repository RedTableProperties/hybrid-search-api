from enum import Enum
from typing import Any, Dict, Optional


class ErrorSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class BasePipelineError(Exception):
    """Base exception for all pipeline errors."""

    def __init__(
        self,
        message: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        correlation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.message = message
        self.severity = severity
        self.correlation_id = correlation_id
        self.context = context or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "context": self.context,
        }


class TransientError(BasePipelineError):
    """Errors that may resolve on retry (network, timeout, rate limit)."""

    pass


class PermanentError(BasePipelineError):
    """Errors that require manual intervention or data fixes."""

    pass


class ValidationError(PermanentError):
    """Schema or data validation failures."""

    pass


class IngestionError(TransientError):
    """Failures during data ingestion."""

    pass


class EnrichmentError(TransientError):
    """Failures during data enrichment."""

    pass


class PublishingError(PermanentError):
    """Failures during data publishing."""

    pass