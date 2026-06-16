import pandas as pd
import pytest

from data_quality import SodaDataQualityManager


@pytest.fixture
def manager():
    return SodaDataQualityManager(checks_path="data_quality/checks")


def test_validate_passes_clean_satellite_scenes(manager):
    df = pd.DataFrame(
        {
            "scene_id": ["SCENE-001", "SCENE-002"],
            "caption": ["Pretoria East", "Centurion"],
        }
    )

    result = manager.validate(df, "satellite_scenes", ["satellite_scenes.yml"])

    assert result["success"] is True
    assert result["failed_checks"] == []
    assert result["results"]["checks_run"] == 2


def test_validate_fails_when_required_column_missing(manager):
    df = pd.DataFrame({"caption": ["Pretoria East"]})

    result = manager.validate(df, "satellite_scenes", ["satellite_scenes.yml"])

    assert result["success"] is False
    assert len(result["failed_checks"]) == 1
    assert result["failed_checks"][0]["check"] == "missing_count(scene_id) = 0"


def test_validate_enrichment_vectors(manager):
    df = pd.DataFrame({"embedding_dims": [768, 768]})

    result = manager.validate(df, "enrichment_vectors", ["enrichment_vectors.yml"])

    assert result["success"] is True