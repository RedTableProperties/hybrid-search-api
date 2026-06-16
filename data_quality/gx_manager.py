import json
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

_SUITE_ROOT = Path(__file__).resolve().parent / "gx_suites"


class GreatExpectationsManager:
    def __init__(self, suite_root: str | Path = _SUITE_ROOT):
        self.suite_root = Path(suite_root)

    def validate(
        self,
        df: pd.DataFrame,
        expectation_suite_name: str,
    ) -> Dict[str, Any]:
        suite_path = self.suite_root / f"{expectation_suite_name}.json"
        expectations = self._load_suite(suite_path)
        results = [self._run_expectation(df, expectation) for expectation in expectations]
        failed = [result for result in results if not result["success"]]

        return {
            "success": not failed,
            "results": results,
            "failed_expectations": failed,
            "suite": expectation_suite_name,
        }

    def _load_suite(self, suite_path: Path) -> List[Dict[str, Any]]:
        payload = json.loads(suite_path.read_text(encoding="utf-8"))
        return payload.get("expectations", [])

    def _run_expectation(self, df: pd.DataFrame, expectation: Dict[str, Any]) -> Dict[str, Any]:
        expectation_type = expectation["expectation_type"]
        kwargs = expectation.get("kwargs", {})

        if expectation_type == "expect_table_row_count_to_be_between":
            actual = len(df)
            min_value = kwargs.get("min_value", 0)
            max_value = kwargs.get("max_value")
            passed = actual >= min_value and (max_value is None or actual <= max_value)
            return {
                "expectation_type": expectation_type,
                "success": passed,
                "result": {"observed_value": actual},
            }

        if expectation_type == "expect_column_values_to_not_be_null":
            column = kwargs["column"]
            if column not in df.columns:
                return {
                    "expectation_type": expectation_type,
                    "success": False,
                    "result": {"observed_value": "missing_column"},
                }
            null_count = int(df[column].isna().sum())
            return {
                "expectation_type": expectation_type,
                "success": null_count == 0,
                "result": {"observed_value": null_count},
            }

        raise ValueError(f"Unsupported expectation type: {expectation_type}")