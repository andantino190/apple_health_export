"""inspect subcommand: summarize sources/types/headers and emit YAML stubs."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, TextIO
from xml.etree.ElementTree import tostring

import yaml

from apple_health_export.flatten import metadata_entries, short_type_name
from apple_health_export.xml_stream import iter_top_level_elements


def inspect_export(
    input_path: str | Path,
    *,
    source: str | None = None,
    split_xml: str | Path | None = None,
) -> dict:
    source_counts: Counter[str] = Counter()
    types_by_source: dict[str, Counter[str]] = defaultdict(Counter)
    values_by_source_type: dict[tuple[str, str], Counter[str]] = defaultdict(Counter)
    headers_by_source_type: dict[tuple[str, str], set[str]] = defaultdict(set)
    correlation_counts: Counter[str] = Counter()

    split_handles: dict[str, TextIO] = {}
    split_dir = Path(split_xml) if split_xml else None
    if split_dir:
        split_dir.mkdir(parents=True, exist_ok=True)

    try:
        for kind, elem in iter_top_level_elements(input_path):
            src = elem.attrib.get("sourceName", "")
            if source is not None and src != source:
                continue

            if split_dir is not None and src:
                _append_split(split_handles, split_dir, src, elem)

            if kind == "Correlation":
                correlation_counts[src] += 1
                type_name = elem.attrib.get("type", "")
                types_by_source[src][type_name] += 1
                source_counts[src] += 1
                key = (src, type_name)
                headers_by_source_type[key].update(elem.attrib.keys())
                headers_by_source_type[key].update(metadata_entries(elem).keys())
                for child in elem:
                    if child.tag == "Record":
                        short = short_type_name(child.attrib.get("type"))
                        headers_by_source_type[key].add(short)
                        if "unit" in child.attrib:
                            headers_by_source_type[key].add(f"{short}_unit")
                continue

            source_counts[src] += 1
            type_name = elem.attrib.get("type", "")
            types_by_source[src][type_name] += 1
            value = elem.attrib.get("value")
            if value is not None:
                values_by_source_type[(src, type_name)][value] += 1

            key = (src, type_name)
            headers_by_source_type[key].update(elem.attrib.keys())
            headers_by_source_type[key].update(metadata_entries(elem).keys())
    finally:
        for fh in split_handles.values():
            fh.write("</HealthData>\n")
            fh.close()

    return {
        "source_counts": source_counts,
        "types_by_source": types_by_source,
        "values_by_source_type": values_by_source_type,
        "headers_by_source_type": headers_by_source_type,
        "correlation_counts": correlation_counts,
    }


def _safe_filename(source_name: str) -> str:
    return (
        source_name.replace("/", "_")
        .replace("\\", "_")
        .replace(" ", "_")
        .replace("\xa0", "_")
    )


def _append_split(handles: dict[str, TextIO], split_dir: Path, src: str, elem: Any) -> None:
    if src not in handles:
        path = split_dir / f"{_safe_filename(src)}.xml"
        fh = path.open("w", encoding="utf-8")
        fh.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        fh.write('<HealthData locale="en_US">\n')
        handles[src] = fh
    fh = handles[src]
    # Serialize while children still exist (iter_top_level_elements clears after yield).
    xml = tostring(elem, encoding="unicode")
    fh.write(xml)
    if not xml.endswith("\n"):
        fh.write("\n")


def print_inspect_report(result: dict, *, source: str | None = None) -> None:
    source_counts: Counter[str] = result["source_counts"]
    types_by_source = result["types_by_source"]
    values_by_source_type = result["values_by_source_type"]
    headers_by_source_type = result["headers_by_source_type"]
    correlation_counts: Counter[str] = result["correlation_counts"]

    print("== sources ==")
    for src, count in source_counts.most_common():
        corr = correlation_counts.get(src, 0)
        extra = f" (correlations={corr})" if corr else ""
        print(f"{count:8d}  {src!r}{extra}")

    print("\n== types by source ==")
    for src in sorted(types_by_source, key=lambda s: -sum(types_by_source[s].values())):
        if source is not None and src != source:
            continue
        print(f"\n[{src!r}]")
        for type_name, count in types_by_source[src].most_common():
            print(f"  {count:8d}  {type_name}")
            headers = sorted(headers_by_source_type.get((src, type_name), []))
            print(f"           headers: {', '.join(headers)}")
            value_counts = values_by_source_type.get((src, type_name))
            if value_counts and len(value_counts) <= 12:
                top = ", ".join(f"{v!r}:{c}" for v, c in value_counts.most_common())
                print(f"           values: {top}")

    print("\n== yaml stub ==")
    stub = {
        "input": "export.xml",
        "output": "output",
        "targets": [],
    }
    for src, _ in source_counts.most_common():
        if source is not None and src != source:
            continue
        # One stub target per source (type omitted -> correlation-aware extract)
        stub["targets"].append(
            {
                "source_name": src,
                "date_field": "startDate",
                # "type": None,
                # "value": None,
                # "extraction_start": "2024-01-01",
                "csv_output": f"{_safe_filename(src)}.csv",
            }
        )
        # Also emit typed stubs for the top few types
        for type_name, _count in types_by_source[src].most_common(3):
            if type_name.startswith("HKCorrelationTypeIdentifier"):
                continue
            stub["targets"].append(
                {
                    "source_name": src,
                    "type": type_name,
                    "date_field": "startDate",
                    "csv_output": f"{_safe_filename(src)}__{short_type_name(type_name)}.csv",
                }
            )
    print(yaml.safe_dump(stub, allow_unicode=True, sort_keys=False))


def run_inspect(
    input_path: str | Path,
    *,
    source: str | None = None,
    split_xml: str | Path | None = None,
) -> dict:
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"input not found: {path}")
    result = inspect_export(path, source=source, split_xml=split_xml)
    print_inspect_report(result, source=source)
    return result
