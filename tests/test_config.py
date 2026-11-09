from pathlib import Path

import pytest
import yaml

from apple_health_export.config import ConfigError, load_config


def test_load_config_ok(tmp_path: Path):
    cfg = {
        "input": "export.xml",
        "output": "out",
        "targets": [
            {
                "source_name": "AutoSleep",
                "type": "HKCategoryTypeIdentifierSleepAnalysis",
                "csv_output": "a.csv",
            }
        ],
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    (tmp_path / "export.xml").write_text("<HealthData/>", encoding="utf-8")

    loaded = load_config(path)
    assert loaded.input == tmp_path / "export.xml"
    assert loaded.targets[0].source_name == "AutoSleep"
    assert loaded.targets[0].date_field == "startDate"


def test_source_name_required(tmp_path: Path):
    cfg = {"input": "export.xml", "targets": [{"csv_output": "a.csv"}]}
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    with pytest.raises(ConfigError, match="source_name"):
        load_config(path)


def test_record_type_alias(tmp_path: Path):
    cfg = {
        "input": "export.xml",
        "targets": [
            {
                "source_name": "Watch",
                "record_type": "HKQuantityTypeIdentifierHeartRate",
                "csv_output": "hr.csv",
            }
        ],
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    loaded = load_config(path)
    assert loaded.targets[0].type == "HKQuantityTypeIdentifierHeartRate"
