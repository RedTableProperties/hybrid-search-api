from typing import List, Optional

import pandas as pd

from common.exceptions import ErrorSeverity, ValidationError
from data_quality.gx_manager import GreatExpectationsManager
from data_quality.soda_manager import SodaDataQualityManager
from pipelines.base_stage import BasePipelineStage, PipelineEvent


class DataQualityStage(BasePipelineStage):
    """
    Primary data quality stage using Soda Core.
    Can optionally run Great Expectations for complex cases.
    """

    def __init__(
        self,
        check_files: List[str],
        use_gx: bool = False,
        gx_expectation_suite: Optional[str] = None,
    ):
        super().__init__("data_quality")
        self.soda = SodaDataQualityManager()
        self.check_files = check_files
        self.use_gx = use_gx
        self.gx = GreatExpectationsManager() if use_gx else None
        self.gx_expectation_suite = gx_expectation_suite

    async def _process(self, event: PipelineEvent):
        data = event.payload.get("normalized_data", {})
        df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)

        soda_results = self.soda.validate(
            df=df,
            dataset_name="normalized_data",
            check_files=self.check_files,
        )

        if not soda_results["success"]:
            raise ValidationError(
                message="Data quality validation failed (Soda Core)",
                severity=ErrorSeverity.HIGH,
                correlation_id=event.trace_id,
                context={"failed_checks": soda_results["failed_checks"]},
            )

        if self.use_gx and self.gx_expectation_suite:
            gx_results = self.gx.validate(
                df=df,
                expectation_suite_name=self.gx_expectation_suite,
            )
            if not gx_results["success"]:
                raise ValidationError(
                    message="Data quality validation failed (Great Expectations)",
                    severity=ErrorSeverity.HIGH,
                    correlation_id=event.trace_id,
                    context={"failed_expectations": gx_results["failed_expectations"]},
                )

        return {
            "status": "quality_passed",
            "soda_results": soda_results,
            "used_gx": self.use_gx,
        }