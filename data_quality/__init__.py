from .gx_manager import GreatExpectationsManager
from .soda_manager import SodaDataQualityManager

__all__ = ["DataQualityStage", "GreatExpectationsManager", "SodaDataQualityManager"]


def __getattr__(name: str):
    if name == "DataQualityStage":
        from .quality_stage import DataQualityStage

        return DataQualityStage
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")