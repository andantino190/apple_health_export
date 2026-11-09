"""YAML config loading and validation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DATE_FIELDS = frozenset({"startDate", "creationDate"})
OUTPUT_KEYS = ("csv_output", "excel_output", "parquet_output", "xml_output")


@dataclass(frozen=True)
class TargetConfig:
    source_name: str
    type: str | None = None
    value: str | None = None
    date_field: str = "startDate"
    extraction_start: str | None = None
    extraction_end: str | None = None
    csv_output: str | None = None
    excel_output: str | None = None
    parquet_output: str | None = None
    xml_output: str | None = None

    def output_files(self) -> dict[str, str]:
        mapping = {
            "csv": self.csv_output,
            "excel": self.excel_output,
            "parquet": self.parquet_output,
            "xml": self.xml_output,
        }
        return {k: v for k, v in mapping.items() if v}


@dataclass(frozen=True)
class AppConfig:
    input: Path
    output: Path
    targets: tuple[TargetConfig, ...]


class ConfigError(ValueError):
    pass


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None or value == "":
        return None
    return str(value)


def _parse_target(raw: dict[str, Any], index: int) -> TargetConfig:
    if not isinstance(raw, dict):
        raise ConfigError(f"targets[{index}] must be a mapping")

    source_name = raw.get("source_name")
    if not source_name:
        raise ConfigError(f"targets[{index}].source_name is required")

    # Accept legacy alias from early notes.
    type_name = _optional_str(raw, "type") or _optional_str(raw, "record_type")
    date_field = raw.get("date_field", "startDate") or "startDate"
    if date_field not in DATE_FIELDS:
        raise ConfigError(
            f"targets[{index}].date_field must be one of {sorted(DATE_FIELDS)}"
        )

    target = TargetConfig(
        source_name=str(source_name),
        type=type_name,
        value=_optional_str(raw, "value"),
        date_field=str(date_field),
        extraction_start=_optional_str(raw, "extraction_start"),
        extraction_end=_optional_str(raw, "extraction_end"),
        csv_output=_optional_str(raw, "csv_output"),
        excel_output=_optional_str(raw, "excel_output"),
        parquet_output=_optional_str(raw, "parquet_output"),
        xml_output=_optional_str(raw, "xml_output"),
    )
    if not target.output_files():
        raise ConfigError(
            f"targets[{index}] must specify at least one of: {', '.join(OUTPUT_KEYS)}"
        )
    return target


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    with config_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ConfigError("config root must be a mapping")

    input_path = data.get("input")
    output_path = data.get("output", "output")
    if not input_path:
        raise ConfigError("input is required")

    targets_raw = data.get("targets")
    if not isinstance(targets_raw, list) or not targets_raw:
        raise ConfigError("targets must be a non-empty list")

    # Resolve relative paths against the config file directory.
    base = config_path.parent
    input_resolved = Path(input_path)
    if not input_resolved.is_absolute():
        input_resolved = (base / input_resolved).resolve()
    output_resolved = Path(output_path)
    if not output_resolved.is_absolute():
        output_resolved = (base / output_resolved).resolve()

    targets = tuple(_parse_target(item, i) for i, item in enumerate(targets_raw))
    return AppConfig(input=input_resolved, output=output_resolved, targets=targets)
