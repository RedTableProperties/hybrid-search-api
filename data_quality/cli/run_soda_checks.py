#!/usr/bin/env python3
"""
Soda Core CLI - Run Soda Data Quality Checks

Usage Examples:
    python -m data_quality.cli.run_soda_checks --checks normalized_data
    python -m data_quality.cli.run_soda_checks --checks normalized_data enriched_data --fail-on-error
    python -m data_quality.cli.run_soda_checks --checks normalized_data --cloud
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from soda.scan import Scan

from data_quality.pandas_sodacl import run_pandas_checks
from data_quality.soda_manager import SodaDataQualityManager
from observability.observability import traced

CHECKS_DIR = ROOT / "data_quality" / "checks"
FIXTURES_DIR = ROOT / "data_quality" / "fixtures"
SCAN_DEFINITION_NAME = "web_data_discovery_pipeline"


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


def _scan_failed_checks(scan: Scan) -> tuple[bool, list[Any]]:
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
    return has_failed, failed_checks if has_failed else []


def _normalize_failed_checks(failed_checks: list[Any]) -> list[dict[str, Any]]:
    normalized = []
    for check in failed_checks:
        if isinstance(check, dict):
            normalized.append(
                {
                    "check": check.get("check") or check.get("name") or "Unknown check",
                    "identity": check.get("identity"),
                    "definition": check.get("definition"),
                }
            )
        else:
            normalized.append({"check": str(check), "identity": None, "definition": None})
    return normalized


def _validate_with_scan(
    df: pd.DataFrame,
    dataset_name: str,
    check_path: Path,
    use_cloud: bool,
) -> dict[str, Any]:
    scan = Scan()
    scan.set_data_source_name("pandas")
    if use_cloud:
        scan.set_scan_definition_name(SCAN_DEFINITION_NAME)
    scan.add_configuration_yaml_str(
        """
data_source pandas:
  type: pandas
"""
    )
    scan.add_pandas_dataframe(dataset_name, df, data_source_name="pandas")
    scan.add_sodacl_yaml_files(str(check_path))
    scan.execute()

    has_failed, failed_checks = _scan_failed_checks(scan)
    return {
        "success": not has_failed,
        "results": scan.get_scan_results(),
        "failed_checks": _normalize_failed_checks(failed_checks),
    }


def _validate_check(
    check_name: str,
    df: pd.DataFrame,
    use_cloud: bool,
) -> dict[str, Any]:
    manager = SodaDataQualityManager(checks_path=str(CHECKS_DIR))
    check_path = CHECKS_DIR / f"{check_name}.yml"

    if manager._soda_pandas_supported():
        return _validate_with_scan(df, check_name, check_path, use_cloud)

    result = run_pandas_checks(df, check_name, [str(check_path)])
    result["failed_checks"] = _normalize_failed_checks(result.get("failed_checks", []))
    return result


def run_soda_checks(
    check_names: list[str],
    fail_on_error: bool = True,
    use_cloud: bool = False,
    input_path: Optional[Path] = None,
) -> bool:
    """
    Run Soda Core checks from the command line.

    Args:
        check_names: List of check file names (without .yml extension)
        fail_on_error: Exit with code 1 if any check fails
        use_cloud: Connect to Soda Cloud for notifications and history
        input_path: Optional CSV/JSON input (defaults to fixtures per check)
    """
    with traced("soda_cli_checks"):
        for check_name in check_names:
            check_file = CHECKS_DIR / f"{check_name}.yml"
            if not check_file.exists():
                print(f"❌ Check file not found: {check_file}")
                if fail_on_error:
                    sys.exit(1)
                return False
            print(f"📋 Loaded check file: {check_name}.yml")

        print(f"\n🔍 Running Soda checks: {', '.join(check_names)}")
        if use_cloud:
            print("☁️  Connected to Soda Cloud")

        run_summary: list[dict[str, Any]] = []
        all_failed_checks: list[dict[str, Any]] = []
        all_passed = True

        for check_name in check_names:
            try:
                df = _load_dataset(check_name, input_path)
            except (FileNotFoundError, ValueError) as exc:
                print(f"❌ {exc}")
                if fail_on_error:
                    sys.exit(1)
                return False

            result = _validate_check(check_name, df, use_cloud)
            run_summary.append(
                {"check": check_name, "success": result["success"], "result": result}
            )

            if not result["success"]:
                all_passed = False
                all_failed_checks.extend(result.get("failed_checks", []))
                print("Data quality checks failed:")
                for check in result.get("failed_checks", []):
                    print(f"   - {check.get('check', 'Unknown check')}")

        results_path = ROOT / "soda_results.json"
        results_path.write_text(json.dumps(run_summary, indent=2, default=str), encoding="utf-8")

        if all_passed:
            print("\n✅ All Soda checks passed successfully.")
            return True

        print("\n❌ Some checks failed:")
        for check in all_failed_checks:
            print(f"   - {check.get('check', 'Unknown check')}")

        if fail_on_error:
            sys.exit(1)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run Soda Core data quality checks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m data_quality.cli.run_soda_checks --checks normalized_data
  python -m data_quality.cli.run_soda_checks --checks normalized_data enriched_data --cloud
        """,
    )

    parser.add_argument(
        "--checks",
        nargs="+",
        required=True,
        help="One or more check files to run (without .yml extension)",
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
        help="Exit with error code if any check fails (default: True)",
    )
    parser.add_argument(
        "--cloud",
        action="store_true",
        default=False,
        help="Connect to Soda Cloud for notifications and history",
    )

    args = parser.parse_args()
    run_soda_checks(
        check_names=args.checks,
        fail_on_error=args.fail_on_error,
        use_cloud=args.cloud,
        input_path=args.input,
    )


if __name__ == "__main__":
    main()