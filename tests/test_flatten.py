from pathlib import Path
import xml.etree.ElementTree as ET

from apple_health_export.flatten import correlation_to_row, record_to_row, short_type_name

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.xml"


def test_short_type_name():
    assert short_type_name("HKQuantityTypeIdentifierHeartRate") == "HeartRate"
    assert short_type_name("HKCategoryTypeIdentifierSleepAnalysis") == "SleepAnalysis"


def test_autosleep_metadata_flatten():
    root = ET.parse(FIXTURE).getroot()
    record = root.find("./Record[@sourceName='AutoSleep']")
    assert record is not None
    row = record_to_row(record)
    assert row["value"] == "HKCategoryValueSleepAnalysisInBed"
    assert row["Average RespRate"] == "17.5455"
    assert row["Recharge"] == "43"


def test_correlation_flatten():
    root = ET.parse(FIXTURE).getroot()
    corr = root.find("./Correlation")
    assert corr is not None
    row = correlation_to_row(corr)
    assert row["BloodPressureSystolic"] == "120"
    assert row["BloodPressureDiastolic"] == "80"
    assert row["BloodPressureSystolic_unit"] == "mmHg"
