#!/usr/bin/env python3
"""Portable validation installed with a downstream project."""

import argparse
import sys
from pathlib import Path

# The installed validator must not leave generated files in a project merely
# because CI or a developer ran a documentation check.
sys.dont_write_bytecode = True

from docs_validation import (
    validate_clarify_gate,
    validate_feature_specs,
    validate_links,
    validate_mermaid,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CURRENT = DOCS / "current"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate downstream project documentation links, Mermaid diagrams, Clarify Gate, and Cross-Spec traceability."
    )
    parser.add_argument(
        "--require-tasks",
        action="store_true",
        help="Require 4. Tasks.md on every approved feature folder.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if not CURRENT.is_dir():
        raise ValueError("docs/current is missing")
    files = sorted(CURRENT.rglob("*.md"))
    if not files:
        raise ValueError("docs/current has no Markdown documents")
    validate_links(ROOT, DOCS, files)
    validate_mermaid(ROOT, files)
    validate_clarify_gate(ROOT, files)
    warnings = validate_feature_specs(
        ROOT,
        CURRENT / "05 - Product Features",
        require_tasks=args.require_tasks,
    )
    for warning in warnings:
        print(f"WARN: {warning}", file=sys.stderr)
    print("PASS: downstream documentation links and Mermaid structure")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
