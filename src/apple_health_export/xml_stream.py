"""Streaming iteration over Apple Health export.xml elements."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Iterator
from pathlib import Path
from typing import Literal

ElementKind = Literal["Record", "Correlation"]


def iter_top_level_elements(
    path: str | Path,
    *,
    kinds: tuple[ElementKind, ...] = ("Record", "Correlation"),
) -> Iterator[tuple[ElementKind, ET.Element]]:
    """Yield top-level Record/Correlation elements (skip Correlation children).

    Important: only clear yielded top-level elements. Clearing every end-event
    would destroy MetadataEntry / nested Record children before the parent is read.
    """
    kind_set = set(kinds)
    path_stack: list[str] = []
    root: ET.Element | None = None

    context = ET.iterparse(path, events=("start", "end"))
    for event, elem in context:
        tag = elem.tag
        if event == "start":
            path_stack.append(tag)
            if tag == "HealthData":
                root = elem
            continue

        # end
        if (
            tag in kind_set
            and len(path_stack) >= 2
            and path_stack[-2] == "HealthData"
        ):
            yield tag, elem  # type: ignore[misc]
            # Free this element and detach finished children from the document root.
            elem.clear()
            if root is not None:
                root.clear()

        if path_stack and path_stack[-1] == tag:
            path_stack.pop()


def child_record_types(correlation: ET.Element) -> set[str]:
    types: set[str] = set()
    for child in correlation:
        if child.tag == "Record":
            t = child.attrib.get("type")
            if t:
                types.add(t)
    return types
