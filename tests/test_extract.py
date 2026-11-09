from pathlib import Path

import yaml

from apple_health_export.config import load_config
from apple_health_export.extract_cmd import extract_target, run_extract

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.xml"


def _config(tmp_path: Path, targets: list[dict]) -> Path:
    cfg = {
        "input": str(FIXTURE),
        "output": str(tmp_path / "output"),
        "targets": targets,
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(cfg, allow_unicode=True), encoding="utf-8")
    return path


def test_correlation_when_type_omitted(tmp_path: Path):
    path = _config(
        tmp_path,
        [
            {
                "source_name": "血圧ノート",
                "extraction_start": "2024-01-01",
                "csv_output": "bp.csv",
            }
        ],
    )
    config = load_config(path)
    rows = extract_target(config, config.targets[0])
    assert len(rows) == 1
    assert rows[0]["BloodPressureSystolic"] == "120"
    assert rows[0]["BloodPressureDiastolic"] == "80"
    assert "sourceName" not in rows[0]


def test_typed_record_extract(tmp_path: Path):
    path = _config(
        tmp_path,
        [
            {
                "source_name": "血圧ノート",
                "type": "HKQuantityTypeIdentifierBloodPressureSystolic",
                "csv_output": "sys.csv",
            }
        ],
    )
    config = load_config(path)
    rows = extract_target(config, config.targets[0])
    assert len(rows) == 2
    assert all("type" not in r for r in rows)
    assert {r["value"] for r in rows} == {"120", "130"}


def test_autosleep_value_filter_and_metadata(tmp_path: Path):
    path = _config(
        tmp_path,
        [
            {
                "source_name": "AutoSleep",
                "type": "HKCategoryTypeIdentifierSleepAnalysis",
                "value": "HKCategoryValueSleepAnalysisInBed",
                "csv_output": "as.csv",
            }
        ],
    )
    config = load_config(path)
    rows = extract_target(config, config.targets[0])
    assert len(rows) == 1
    assert rows[0]["Average RespRate"] == "17.5455"
    assert "value" not in rows[0]


def test_date_field_creation_date(tmp_path: Path):
    # startDate is 2024-03-09 but creationDate is 2024-03-10
    path = _config(
        tmp_path,
        [
            {
                "source_name": "AutoSleep",
                "type": "HKCategoryTypeIdentifierSleepAnalysis",
                "date_field": "creationDate",
                "extraction_start": "2024-03-10",
                "extraction_end": "2024-03-10",
                "csv_output": "as.csv",
            }
        ],
    )
    config = load_config(path)
    rows = extract_target(config, config.targets[0])
    assert len(rows) == 2


def test_run_extract_writes_csv(tmp_path: Path):
    path = _config(
        tmp_path,
        [
            {
                "source_name": "andantino190AppleWatch",
                "type": "HKQuantityTypeIdentifierHeartRate",
                "csv_output": "hr.csv",
            }
        ],
    )
    written = run_extract(path)
    assert len(written) == 1
    assert written[0].exists()
    text = written[0].read_text(encoding="utf-8")
    assert "72" in text
