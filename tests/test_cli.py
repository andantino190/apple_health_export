from pathlib import Path

from apple_health_export.cli import main

FIXTURE = Path(__file__).parent / "fixtures" / "sample_export.xml"


def test_cli_inspect(capsys):
    code = main(["inspect", "--input", str(FIXTURE), "--source", "AutoSleep"])
    assert code == 0
    out = capsys.readouterr().out
    assert "AutoSleep" in out
    assert "yaml stub" in out


def test_cli_extract(tmp_path: Path, capsys):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(
        f"""
input: {FIXTURE}
output: {tmp_path / "out"}
targets:
  - source_name: andantino190AppleWatch
    type: HKQuantityTypeIdentifierHeartRate
    csv_output: hr.csv
""",
        encoding="utf-8",
    )
    code = main(["extract", "--config", str(cfg)])
    assert code == 0
    assert (tmp_path / "out" / "hr.csv").exists()
