#!/usr/bin/env python3
"""Portable validation installed with a downstream project."""

import sys
from pathlib import Path

# The installed validator must not leave generated files in a project merely
# because CI or a developer ran a documentation check.
sys.dont_write_bytecode = True

from docs_validation import validate_links, validate_mermaid

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CURRENT = DOCS / "current"


def main() -> None:
    if not CURRENT.is_dir():
        raise ValueError("docs/current is missing")
    files = list(CURRENT.rglob("*.md"))
    if not files:
        raise ValueError("docs/current has no Markdown documents")
    validate_links(ROOT, DOCS, files)
    validate_mermaid(ROOT, files)
    print("PASS: downstream documentation links and Mermaid structure")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
