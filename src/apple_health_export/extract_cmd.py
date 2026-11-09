"""extract subcommand: filter export.xml using YAML config."""

from __future__ import annotations

from pathlib import Path

from apple_health_export.config import AppConfig, TargetConfig, load_config
from apple_health_export.dates import in_range, parse_boundary
from apple_health_export.flatten import (
    correlation_to_row,
    drop_filter_columns,
    record_to_row,
)
from apple_health_export.writers import write_outputs
from apple_health_export.xml_stream import child_record_types, iter_top_level_elements


def extract_target(config: AppConfig, target: TargetConfig) -> list[dict[str, str]]:
    start = parse_boundary(target.extraction_start, is_end=False)
    end = parse_boundary(target.extraction_end, is_end=True)

    correlation_rows: list[dict[str, str]] = []
    record_candidates: list[dict[str, str]] = []
    excluded_types: set[str] = set()

    kinds = ("Record", "Correlation") if target.type is None else ("Record",)

    for kind, elem in iter_top_level_elements(config.input, kinds=kinds):
        attrib = elem.attrib
        if attrib.get("sourceName") != target.source_name:
            continue
        if not in_range(attrib.get(target.date_field), start=start, end=end):
            continue

        if kind == "Correlation":
            # Only used when type is omitted.
            excluded_types |= child_record_types(elem)
            row = correlation_to_row(elem)
            correlation_rows.append(
                drop_filter_columns(
                    row,
                    source_name=target.source_name,
                    type_name=target.type,
                    value=target.value,
                )
            )
            continue

        record_type = attrib.get("type")
        if target.type is not None and record_type != target.type:
            continue
        if target.value is not None and attrib.get("value") != target.value:
            continue

        row = record_to_row(elem)
        cleaned = drop_filter_columns(
            row,
            source_name=target.source_name,
            type_name=target.type,
            value=target.value,
        )
        if target.type is None:
            # Defer exclusion until all correlations for this source are known.
            cleaned["_record_type"] = record_type or ""
            record_candidates.append(cleaned)
        else:
            record_candidates.append(cleaned)

    if target.type is None:
        rows = list(correlation_rows)
        for row in record_candidates:
            record_type = row.pop("_record_type", "")
            if record_type in excluded_types:
                continue
            rows.append(row)
        return rows

    return record_candidates


def run_extract(config_path: str | Path) -> list[Path]:
    config = load_config(config_path)
    if not config.input.exists():
        raise FileNotFoundError(f"input not found: {config.input}")

    written: list[Path] = []
    for target in config.targets:
        rows = extract_target(config, target)
        paths = write_outputs(rows, config.output, target.output_files())
        written.extend(paths)
        label = target.source_name + (f" / {target.type}" if target.type else "")
        print(f"[{label}] {len(rows)} rows -> " + ", ".join(str(p) for p in paths))
    return written
