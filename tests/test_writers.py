from pathlib import Path

import pandas as pd

from apple_health_export.writers import rows_to_dataframe, write_outputs


def test_excel_strips_timezone(tmp_path: Path):
    rows = [
        {
            "value": "72",
            "startDate": "2024-03-10 11:00:00 +0900",
            "endDate": "2024-03-10 11:00:00 +0900",
            "creationDate": "2024-03-10 11:01:00 +0900",
        }
    ]
    written = write_outputs(rows, tmp_path, {"excel": "out.xlsx"})
    assert written == [tmp_path / "out.xlsx"]
    assert written[0].exists()

    df = pd.read_excel(written[0])
    assert list(df["startDate"].astype(str))[0].startswith("2024-03-10 11:00:00")


def test_rows_to_dataframe_keeps_tz_aware_dates():
    rows = [{"startDate": "2024-03-10 11:00:00 +0900", "value": "1"}]
    df = rows_to_dataframe(rows)
    assert isinstance(df["startDate"].dtype, pd.DatetimeTZDtype)
