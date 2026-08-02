from __future__ import annotations

"""Repository CLI for validating APICORE configuration files."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from apicore import APICoreError, load


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser used by the repository validator."""
    parser = argparse.ArgumentParser(description="Validate APICORE configuration files")
    parser.add_argument(
        "path", type=Path, help="Path to the APICORE configuration file"
    )
    parser.add_argument(
        "--version",
        choices=("v1", "1.0", "v2", "2.0", "2.1", "v2.1"),
        help="Force an APICORE version family or exact specification version",
    )
    parser.add_argument(
        "--format",
        choices=("json", "yaml", "toml"),
        help="Override input format detection",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the validator and return a process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        document = load(args.path, version=args.version, format=args.format)
    except (APICoreError, OSError) as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Valid APICORE {document.apicore_version} file: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
