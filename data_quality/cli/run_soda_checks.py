#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from data_quality.soda_manager import SodaDataQualityManager

CHECKS_BY_DATASET = {
    "normalized_data": ["normalized_data.yml"],
    "enriched_data": ["enriched_data.yml"],
    "published_data": ["published_data.yml"],
}


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Soda Core checks against a dataset file")
    parser.add_argument("--dataset", required=True, choices=sorted(CHECKS_BY_DATASET))
    parser.add_argument(
        "--checks",
        nargs="+",
        help="Check YAML filenames (defaults to the dataset preset)",
    )
    parser.add_argument("--input", required=True, type=Path, help="CSV or JSON input file")
    parser.add_argument(
        "--checks-path",
        default="data_quality/checks",
        help="Directory containing SodaCL YAML files",
    )
    args = parser.parse_args()

    check_files = args.checks or CHECKS_BY_DATASET[args.dataset]
    df = _load_dataframe(args.input)

    manager = SodaDataQualityManager(checks_path=args.checks_path)
    result = manager.validate(
        df=df,
        dataset_name=args.dataset,
        check_files=check_files,
    )

    print(json.dumps(result, indent=2, default=str))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())