import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml

_ROW_COUNT = re.compile(r"^row_count\s*(>=|>|<=|<|=)\s*(\d+)$")
_MISSING_COUNT = re.compile(r"^missing_count\(([^)]+)\)\s*=\s*(\d+)$")


def _parse_checks(content: str, dataset_name: str) -> List[str]:
    parsed = yaml.safe_load(content) or {}
    key = f"checks for {dataset_name}"
    checks = parsed.get(key, [])
    return [str(check).strip() for check in checks]


def _evaluate_check(df: pd.DataFrame, check: str) -> Dict[str, Any]:
    row_count_match = _ROW_COUNT.match(check)
    if row_count_match:
        operator, raw_value = row_count_match.groups()
        actual = len(df)
        expected = int(raw_value)
        passed = {
            ">": actual > expected,
            ">=": actual >= expected,
            "<": actual < expected,
            "<=": actual <= expected,
            "=": actual == expected,
        }[operator]
        return {
            "check": check,
            "passed": passed,
            "actual": actual,
            "expected": expected,
        }

    missing_match = _MISSING_COUNT.match(check)
    if missing_match:
        column, raw_value = missing_match.groups()
        actual = int(df[column].isna().sum()) if column in df.columns else len(df)
        expected = int(raw_value)
        return {
            "check": check,
            "passed": actual == expected,
            "actual": actual,
            "expected": expected,
            "column": column,
        }

    raise ValueError(f"Unsupported SodaCL check: {check}")


def run_pandas_checks(
    df: pd.DataFrame,
    dataset_name: str,
    check_paths: List[str],
) -> Dict[str, Any]:
    evaluations: List[Dict[str, Any]] = []

    for check_path in check_paths:
        content = Path(check_path).read_text(encoding="utf-8")
        for check in _parse_checks(content, dataset_name):
            evaluations.append(_evaluate_check(df, check))

    failed_checks = [result for result in evaluations if not result["passed"]]
    return {
        "success": not failed_checks,
        "results": {
            "dataset": dataset_name,
            "checks_run": len(evaluations),
            "checks": evaluations,
            "engine": "pandas-sodacl",
        },
        "failed_checks": failed_checks,
    }