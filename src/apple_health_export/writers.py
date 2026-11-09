"""Write extracted rows to csv / excel / parquet / xml."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

import pandas as pd


DATE_COLUMNS = ("creationDate", "startDate", "endDate")


def rows_to_dataframe(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    for col in df.columns:
        if col in DATE_COLUMNS:
            df[col] = pd.to_datetime(df[col], errors="coerce", utc=False)
            continue
        if col.endswith("_unit"):
            continue
        # Try numeric conversion; leave non-numeric as-is.
        converted = pd.to_numeric(df[col], errors="coerce")
        if converted.notna().any() and converted.isna().sum() <= df[col].isna().sum():
            # Only adopt if we didn't create many new NaNs from non-numeric strings.
            original_non_null = df[col].notna()
            if (converted.isna() & original_non_null).sum() == 0:
                df[col] = converted
            else:
                # Mixed: keep object, but still convert pure-number-looking later if useful
                # Prefer leaving as string when mixed categories like SleepAnalysis values.
                pass
    return df


def write_outputs(
    rows: list[dict[str, Any]],
    output_dir: Path,
    outputs: dict[str, str],
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    df = rows_to_dataframe(rows)

    if "csv" in outputs:
        path = output_dir / outputs["csv"]
        df.to_csv(path, index=False)
        written.append(path)
    if "excel" in outputs:
        path = output_dir / outputs["excel"]
        df.to_excel(path, index=False)
        written.append(path)
    if "parquet" in outputs:
        path = output_dir / outputs["parquet"]
        df.to_parquet(path, index=False)
        written.append(path)
    if "xml" in outputs:
        path = output_dir / outputs["xml"]
        write_rows_xml(rows, path)
        written.append(path)
    return written


def write_rows_xml(rows: list[dict[str, Any]], path: Path) -> None:
    """Serialize flattened rows as simple Record-like XML for portability."""
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<HealthData locale="en_US">',
    ]
    for row in rows:
        attrs = []
        meta: list[tuple[str, str]] = []
        known = {
            "type",
            "unit",
            "value",
            "sourceName",
            "sourceVersion",
            "device",
            "creationDate",
            "startDate",
            "endDate",
        }
        for key, value in row.items():
            if value is None:
                continue
            text = str(value)
            if key in known:
                attrs.append(f'{key}="{escape(text, {"\"": "&quot;"})}"')
            else:
                meta.append((key, text))
        if meta:
            lines.append(f"  <Record {' '.join(attrs)}>")
            for key, value in meta:
                lines.append(
                    f'    <MetadataEntry key="{escape(key, {"\"": "&quot;"})}" '
                    f'value="{escape(value, {"\"": "&quot;"})}" />'
                )
            lines.append("  </Record>")
        else:
            lines.append(f"  <Record {' '.join(attrs)} />")
    lines.append("</HealthData>")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
