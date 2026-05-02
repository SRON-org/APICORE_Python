from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

from apicore.errors import APICoreError
from apicore.parser import load


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate APICORE configuration files")
    parser.add_argument(
        "path", type=Path, help="Path to the APICORE configuration file"
    )
    parser.add_argument(
        "--version", choices=("v1", "v2"), help="Force a specific APICORE version"
    )
    parser.add_argument(
        "--format",
        choices=("json", "yaml", "toml"),
        help="Override input format detection",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        document = load(args.path, version=args.version, format=args.format)
    except APICoreError as exc:
        print(f"Validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Valid APICORE {document.apicore_version} file: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
