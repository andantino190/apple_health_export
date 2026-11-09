from pathlib import Path

from apple_health_export.inspect_cmd import inspect_export

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.xml"


def test_inspect_counts():
    result = inspect_export(FIXTURE)
    assert result["source_counts"]["血圧ノート"] == 6  # 4 records + 2 correlations
    assert result["source_counts"]["AutoSleep"] == 2
    assert result["correlation_counts"]["血圧ノート"] == 2


def test_inspect_headers_include_metadata():
    result = inspect_export(FIXTURE, source="AutoSleep")
    headers = result["headers_by_source_type"][
        ("AutoSleep", "HKCategoryTypeIdentifierSleepAnalysis")
    ]
    assert "Average RespRate" in headers
    assert "Recharge" in headers


def test_split_xml(tmp_path: Path):
    out = tmp_path / "by_source"
    inspect_export(FIXTURE, split_xml=out)
    files = list(out.glob("*.xml"))
    assert files
    bp = out / "血圧ノート.xml"
    assert bp.exists()
    content = bp.read_text(encoding="utf-8")
    assert "Correlation" in content
    assert content.strip().endswith("</HealthData>")
