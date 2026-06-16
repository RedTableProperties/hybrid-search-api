import json
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_run_soda_checks_module_passes_with_fixture():
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_quality.cli.run_soda_checks",
            "--checks",
            "normalized_data",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "All Soda checks passed successfully." in result.stdout


def test_run_soda_checks_module_fails_on_bad_input(tmp_path):
    input_path = tmp_path / "normalized.json"
    input_path.write_text(
        json.dumps([{"caption": "missing scene id"}]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_quality.cli.run_soda_checks",
            "--checks",
            "normalized_data",
            "--input",
            str(input_path),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "Data quality checks failed:" in result.stdout


def test_run_soda_checks_no_fail_on_error_returns_success_exit(tmp_path):
    input_path = tmp_path / "normalized.json"
    input_path.write_text(
        json.dumps([{"caption": "missing scene id"}]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "data_quality.cli.run_soda_checks",
            "--checks",
            "normalized_data",
            "--input",
            str(input_path),
            "--no-fail-on-error",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "Data quality checks failed:" in result.stdout