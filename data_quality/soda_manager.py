from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from soda.scan import Scan

from data_quality.pandas_sodacl import run_pandas_checks


class SodaDataQualityManager:
    def __init__(self, checks_path: str = "data_quality/checks"):
        self.checks_path = checks_path

    def validate(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        check_files: List[str],
    ) -> Dict[str, Any]:
        check_paths = [str(Path(self.checks_path) / check_file) for check_file in check_files]

        if self._soda_pandas_supported():
            return self._validate_with_soda(df, dataset_name, check_paths)

        return run_pandas_checks(df, dataset_name, check_paths)

    def _soda_pandas_supported(self) -> bool:
        try:
            import dask_sql  # noqa: F401
        except ImportError:
            return False
        return True

    def _validate_with_soda(
        self,
        df: pd.DataFrame,
        dataset_name: str,
        check_paths: List[str],
    ) -> Dict[str, Any]:
        scan = Scan()
        scan.set_data_source_name("pandas")
        scan.add_configuration_yaml_str(
            """
data_source pandas:
  type: pandas
"""
        )
        scan.add_pandas_dataframe(dataset_name, df, data_source_name="pandas")

        for check_path in check_paths:
            scan.add_sodacl_yaml_files(check_path)

        scan.execute()

        has_failed = (
            scan.has_failed_checks()
            if hasattr(scan, "has_failed_checks")
            else scan.has_check_fails()
        )
        failed_checks = (
            scan.get_failed_checks()
            if hasattr(scan, "get_failed_checks")
            else scan.get_checks_fail()
        )

        return {
            "success": not has_failed,
            "results": scan.get_scan_results(),
            "failed_checks": failed_checks if has_failed else [],
        }