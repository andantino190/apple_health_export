"""Backward-compatible entry; prefer apple_health_export.cli:main."""

from apple_health_export.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
