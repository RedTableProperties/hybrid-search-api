#!/usr/bin/env python3
"""Build Great Expectations data docs, with a lightweight HTML fallback."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GX_CONFIG = ROOT / "great_expectations" / "great_expectations.yml"
DOCS_DIR = ROOT / "great_expectations" / "uncommitted" / "data_docs" / "local_site"


def _run(command: list[str]) -> int:
    completed = subprocess.run(command, cwd=ROOT, check=False)
    return completed.returncode


def main() -> int:
    if not GX_CONFIG.exists():
        init_code = _run([sys.executable, "-m", "great_expectations", "init", "--no-view"])
        if init_code != 0:
            print("Great Expectations init failed; using lightweight report fallback.")

    build_code = _run(
        [sys.executable, "-m", "great_expectations", "docs", "build", "--site-name", "local_site"]
    )
    if build_code == 0 and (DOCS_DIR / "index.html").exists():
        print(f"Great Expectations data docs built at {DOCS_DIR}")
        return 0

    print("Falling back to lightweight quality report HTML.")
    fallback = ROOT / "data_quality" / "cli" / "generate_quality_reports.py"
    return _run([sys.executable, str(fallback)])


if __name__ == "__main__":
    sys.exit(main())