import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Optional

import pandas as pd

from common.exceptions import ErrorSeverity, ValidationError
from data_quality.gx_manager import GreatExpectationsManager
from data_quality.soda_manager import SodaDataQualityManager
from pipelines.base_stage import BasePipelineStage, PipelineEvent

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[1]


class DataQualityStage(BasePipelineStage):
    """
    Primary data quality stage using Soda Core.
    Supports Python SDK (default) or CLI subprocess execution.
    """

    def __init__(
        self,
        check_files: List[str],
        dataset_name: str = "normalized_data",
        payload_key: Optional[str] = None,
        use_cli: bool = False,
        enable_cloud_alerts: bool = False,
        use_gx: bool = False,
        gx_expectation_suite: Optional[str] = None,
    ):
        super().__init__("data_quality")
        self.soda = SodaDataQualityManager()
        self.check_files = check_files
        self.dataset_name = dataset_name
        self.payload_key = payload_key or dataset_name
        self.use_cli = use_cli
        self.enable_cloud_alerts = enable_cloud_alerts
        self.use_gx = use_gx
        self.gx = GreatExpectationsManager() if use_gx else None
        self.gx_expectation_suite = gx_expectation_suite

    async def _process(self, event: PipelineEvent):
        data = event.payload.get(self.payload_key, {})
        df = pd.DataFrame([data]) if isinstance(data, dict) else pd.DataFrame(data)

        if self.use_cli:
            soda_results = self._run_cli_checks(event, data)
        else:
            soda_results = self.soda.validate(
                df=df,
                dataset_name=self.dataset_name,
                check_files=self.check_files,
            )

        if not soda_results["success"]:
            raise ValidationError(
                message="Data quality validation failed (Soda Core)",
                severity=ErrorSeverity.HIGH,
                correlation_id=event.trace_id,
                context={"failed_checks": soda_results.get("failed_checks", [])},
            )

        if self.enable_cloud_alerts:
            self._emit_cloud_alert(event, soda_results)

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
            "dataset_name": self.dataset_name,
            "soda_results": soda_results,
            "used_cli": self.use_cli,
            "used_gx": self.use_gx,
            "cloud_alerts_enabled": self.enable_cloud_alerts,
        }

    def _run_cli_checks(self, event: PipelineEvent, data) -> dict:
        check_names = [name.replace(".yml", "") for name in self.check_files]
        records = data if isinstance(data, list) else [data]

        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(records, handle)
            input_path = handle.name

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "data_quality.cli.run_soda_checks",
                    "--checks",
                    *check_names,
                    "--input",
                    input_path,
                    "--fail-on-error",
                ],
                capture_output=True,
                text=True,
                cwd=PROJECT_ROOT,
                check=False,
            )
        finally:
            Path(input_path).unlink(missing_ok=True)

        if result.returncode != 0:
            return {
                "success": False,
                "results": {"stdout": result.stdout, "stderr": result.stderr},
                "failed_checks": [{"check": "cli_execution", "output": result.stdout}],
            }

        return {
            "success": True,
            "results": {"stdout": result.stdout, "engine": "soda-cli"},
            "failed_checks": [],
        }

    def _emit_cloud_alert(self, event: PipelineEvent, soda_results: dict) -> None:
        logger.info(
            "[%s] Cloud alerts enabled for trace_id=%s checks=%s",
            self.name,
            event.trace_id,
            self.check_files,
        )