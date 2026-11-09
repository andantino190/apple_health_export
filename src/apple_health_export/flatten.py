"""Flatten Record / Correlation elements into row dictionaries."""

from __future__ import annotations

import xml.etree.ElementTree as ET

TYPE_PREFIXES = (
    "HKQuantityTypeIdentifier",
    "HKCategoryTypeIdentifier",
    "HKCorrelationTypeIdentifier",
    "HKDataType",
)


def short_type_name(type_name: str | None) -> str:
    if not type_name:
        return "unknown"
    for prefix in TYPE_PREFIXES:
        if type_name.startswith(prefix):
            return type_name[len(prefix) :]
    return type_name


def metadata_entries(elem: ET.Element) -> dict[str, str]:
    result: dict[str, str] = {}
    for child in elem:
        if child.tag == "MetadataEntry":
            key = child.attrib.get("key")
            if key:
                result[key] = child.attrib.get("value", "")
    return result


def record_to_row(elem: ET.Element) -> dict[str, str]:
    row = dict(elem.attrib)
    row.update(metadata_entries(elem))
    return row


def correlation_to_row(elem: ET.Element) -> dict[str, str]:
    row = dict(elem.attrib)
    row.update(metadata_entries(elem))

    child_types: set[str] = set()
    for child in elem:
        if child.tag != "Record":
            continue
        child_type = child.attrib.get("type", "")
        short = short_type_name(child_type)
        child_types.add(child_type)

        if "value" in child.attrib:
            row[short] = child.attrib["value"]
        if "unit" in child.attrib:
            row[f"{short}_unit"] = child.attrib["unit"]

        for key, value in metadata_entries(child).items():
            row[f"{short}__{key}"] = value

    row["_correlation_child_types"] = ",".join(sorted(child_types))
    return row


def drop_filter_columns(
    row: dict[str, str],
    *,
    source_name: str | None,
    type_name: str | None,
    value: str | None,
) -> dict[str, str]:
    out = dict(row)
    out.pop("_correlation_child_types", None)
    if source_name:
        out.pop("sourceName", None)
    if type_name:
        out.pop("type", None)
    if value:
        out.pop("value", None)
    return out
