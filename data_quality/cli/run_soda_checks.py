#!/usr/bin/env python3
"""
Soda Core CLI Automation Script

Usage:
    python -m data_quality.cli.run_soda_checks --checks normalized_data
    python -m data_quality.cli.run_soda_checks --checks normalized_data enriched_data --fail-on-error
    python -m data_quality.cli.run_soda_checks --checks normalized_data --input ./records.json
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from data_quality.soda_manager import SodaDataQualityManager

CHECKS_DIR = ROOT / "data_quality" / "checks"
FIXTURES_DIR = ROOT / "data_quality" / "fixtures"


def _load_dataframe(input_path: Path) -> pd.DataFrame:
    suffix = input_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(input_path)
    if suffix == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return pd.DataFrame(payload)
        if isinstance(payload, dict):
            records = payload.get("records")
            if isinstance(records, list):
                return pd.DataFrame(records)
            return pd.DataFrame([payload])
    raise ValueError(f"Unsupported input format: {input_path}")


def _load_dataset(check_name: str, input_path: Optional[Path]) -> pd.DataFrame:
    if input_path is not None:
        return _load_dataframe(input_path)

    fixture_path = FIXTURES_DIR / f"{check_name}.json"
    if not fixture_path.exists():
        raise FileNotFoundError(
            f"No fixture found for '{check_name}'. Provide --input or add {fixture_path}"
        )
    return _load_dataframe(fixture_path)


def run_soda_checks(
    check_names: list[str],
    fail_on_error: bool = True,
    input_path: Optional[Path] = None,
) -> bool:
    """Run Soda Core checks from the command line."""
    manager = SodaDataQualityManager(checks_path=str(CHECKS_DIR))
    all_passed = True
    run_summary = []

    for check_name in check_names:
        check_file = CHECKS_DIR / f"{check_name}.yml"
        if not check_file.exists():
            print(f"Check file not found: {check_file}")
            all_passed = False
            continue

        print(f"Running Soda checks: {check_name}")
        df = _load_dataset(check_name, input_path)
        result = manager.validate(
            df=df,
            dataset_name=check_name,
            check_files=[f"{check_name}.yml"],
        )
        run_summary.append({"check": check_name, "success": result["success"], "result": result})

        if not result["success"]:
            all_passed = False
            print("Data quality checks failed:")
            for check in result.get("failed_checks", []):
                label = check.get("check") or check.get("name") or "Unknown check"
                print(f"   - {label}")
        else:
            print(f"All Soda checks passed for {check_name}.")

    results_path = ROOT / "soda_results.json"
    results_path.write_text(json.dumps(run_summary, indent=2, default=str), encoding="utf-8")

    if all_passed:
        print("All Soda checks passed successfully.")
        return True

    if fail_on_error:
        sys.exit(1)
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Soda Core data quality checks")
    parser.add_argument(
        "--checks",
        nargs="+",
        required=True,
        help="List of check files to run (without .yml extension)",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Optional CSV or JSON input file (defaults to data_quality/fixtures/<check>.json)",
    )
    parser.add_argument(
        "--fail-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Exit with error code if checks fail",
    )

    args = parser.parse_args()
    run_soda_checks(args.checks, args.fail_on_error, args.input)


if __name__ == "__main__":
    main()