from datetime import datetime

from apple_health_export.dates import in_range, parse_boundary, parse_health_datetime


def test_parse_health_datetime():
    dt = parse_health_datetime("2024-03-10 11:00:00 +0900")
    assert dt is not None
    assert dt.year == 2024
    assert dt.month == 3


def test_inclusive_end_date():
    end = parse_boundary("2024-03-10", is_end=True)
    assert end is not None
    assert end.hour == 23
    assert in_range(
        "2024-03-10 11:00:00 +0900",
        start=parse_boundary("2024-03-10", is_end=False),
        end=end,
    )
    assert not in_range(
        "2024-03-11 00:00:00 +0900",
        start=None,
        end=end,
    )
