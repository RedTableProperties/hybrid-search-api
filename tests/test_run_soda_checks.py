import json
import subprocess
import sys
from pathlib import Path


def test_run_soda_checks_cli_passes_normalized_data(tmp_path):
    input_path = tmp_path / "normalized.json"
    input_path.write_text(
        json.dumps([{"scene_id": "SCENE-001", "caption": "Pretoria East"}]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "data_quality/cli/run_soda_checks.py",
            "--dataset",
            "normalized_data",
            "--input",
            str(input_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["success"] is True


def test_run_soda_checks_cli_fails_on_bad_data(tmp_path):
    input_path = tmp_path / "normalized.json"
    input_path.write_text(
        json.dumps([{"caption": "missing scene id"}]),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            sys.executable,
            "data_quality/cli/run_soda_checks.py",
            "--dataset",
            "normalized_data",
            "--input",
            str(input_path),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["success"] is False