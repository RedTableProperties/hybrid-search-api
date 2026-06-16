#!/usr/bin/env python3
"""Run Great Expectations JSON suites against fixture data."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from data_quality.gx_manager import GreatExpectationsManager

FIXTURES_DIR = ROOT / "data_quality" / "fixtures"
SUITES_DIR = ROOT / "data_quality" / "gx_suites"


def main() -> int:
    manager = GreatExpectationsManager()
    all_passed = True
    summary = []

    for suite_path in sorted(SUITES_DIR.glob("*.json")):
        suite_name = suite_path.stem
        fixture_path = FIXTURES_DIR / f"{suite_name}.json"
        if not fixture_path.exists():
            print(f"Skipping {suite_name}: no fixture at {fixture_path}")
            continue

        df = pd.read_json(fixture_path)
        result = manager.validate(df=df, expectation_suite_name=suite_name)
        summary.append({"suite": suite_name, "success": result["success"]})

        if result["success"]:
            print(f"Great Expectations suite passed: {suite_name}")
        else:
            all_passed = False
            print(f"Great Expectations suite failed: {suite_name}")
            for failure in result.get("failed_expectations", []):
                print(f"   - {failure.get('expectation_type')}")

    results_path = ROOT / "gx_results.json"
    results_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    if all_passed:
        print("All Great Expectations suites passed successfully.")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())