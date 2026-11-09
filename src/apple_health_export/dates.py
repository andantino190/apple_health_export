"""Date parsing and range filtering for Apple Health timestamps."""

from __future__ import annotations

from datetime import datetime, time


def parse_health_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.strip()
    # Apple Health: "2023-10-14 11:35:23 +0900"
    for fmt in ("%Y-%m-%d %H:%M:%S %z", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def parse_boundary(value: str | None, *, is_end: bool) -> datetime | None:
    """Parse config boundary. Date-only end includes the whole day."""
    if not value:
        return None
    text = value.strip()
    dt = parse_health_datetime(text)
    if dt is None:
        raise ValueError(f"invalid date: {value!r}")

    if len(text) == 10 and is_end:
        # Inclusive end date: keep records through 23:59:59.999... of that day
        # by using < next day as comparison elsewhere, or max time here.
        if dt.tzinfo is not None:
            return datetime.combine(dt.date(), time(23, 59, 59), tzinfo=dt.tzinfo)
        return datetime.combine(dt.date(), time(23, 59, 59))
    return dt


def in_range(
    record_value: str | None,
    *,
    start: datetime | None,
    end: datetime | None,
) -> bool:
    if start is None and end is None:
        return True
    dt = parse_health_datetime(record_value)
    if dt is None:
        return False

    # If boundaries are naive/aware mismatched, compare without tz.
    def normalize(a: datetime, b: datetime) -> tuple[datetime, datetime]:
        if a.tzinfo is not None and b.tzinfo is None:
            return a.replace(tzinfo=None), b
        if a.tzinfo is None and b.tzinfo is not None:
            return a, b.replace(tzinfo=None)
        return a, b

    if start is not None:
        left, right = normalize(dt, start)
        if left < right:
            return False
    if end is not None:
        left, right = normalize(dt, end)
        if left > right:
            return False
    return True
