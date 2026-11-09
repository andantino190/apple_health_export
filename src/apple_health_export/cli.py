"""Command-line interface for apple-health-export."""

from __future__ import annotations

import argparse
import sys

from apple_health_export import __version__
from apple_health_export.config import ConfigError
from apple_health_export.extract_cmd import run_extract
from apple_health_export.inspect_cmd import run_inspect


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="health-export",
        description="Extract subsets of Apple Health export.xml into analysis-friendly formats.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    inspect_p = sub.add_parser(
        "inspect",
        help="Summarize sources, types, headers, and emit a YAML stub",
    )
    inspect_p.add_argument("--input", required=True, help="Path to export.xml")
    inspect_p.add_argument("--source", help="Limit to a single sourceName")
    inspect_p.add_argument(
        "--split-xml",
        help="Write per-source XML files into this directory",
    )

    extract_p = sub.add_parser(
        "extract",
        help="Extract rows using a YAML config file",
    )
    extract_p.add_argument("--config", required=True, help="Path to YAML config")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "inspect":
            run_inspect(args.input, source=args.source, split_xml=args.split_xml)
            return 0
        if args.command == "extract":
            run_extract(args.config)
            return 0
        parser.error(f"unknown command: {args.command}")
        return 2
    except (ConfigError, FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
