#!/usr/bin/env python3
"""Portable validation installed with a downstream project."""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CURRENT = DOCS / "current"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def validate_wikilinks(files: list[Path]) -> None:
    by_relative = {path.relative_to(DOCS).with_suffix("").as_posix() for path in files}
    by_stem: dict[str, list[Path]] = {}
    for path in files:
        by_stem.setdefault(path.stem, []).append(path)

    pattern = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    for path in files:
        for match in pattern.finditer(read(path)):
            target = match.group(1).strip().replace("\\", "/")
            relative = (path.parent.relative_to(DOCS) / target).as_posix()
            current = f"current/{target}"
            if target in by_relative or relative in by_relative or current in by_relative:
                continue
            matches = by_stem.get(target, [])
            require(len(matches) == 1, f"{path.relative_to(ROOT)}: unresolved or ambiguous Obsidian link [[{target}]]")


def validate_markdown_links(files: list[Path]) -> None:
    pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in files:
        for match in pattern.finditer(read(path)):
            target = match.group(1).split("#", 1)[0]
            require(not target.lower().startswith("file:"), f"{path.relative_to(ROOT)}: unsupported Markdown URI scheme file:")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            candidate = (path.parent / target).resolve()
            require(candidate.is_relative_to(ROOT), f"{path.relative_to(ROOT)}: Markdown link target escapes project root {target}")
            require(candidate.is_file(), f"{path.relative_to(ROOT)}: missing Markdown link target {target}")


def validate_mermaid(files: list[Path]) -> None:
    block = re.compile(r"(?ms)^```mermaid[ \t]*\n(.*?)^```[ \t]*$")
    for path in files:
        content = read(path)
        require(content.count("```mermaid") == len(block.findall(content)), f"{path.relative_to(ROOT)}: malformed or unclosed Mermaid fence")
        for diagram in block.findall(content):
            require(bool(diagram.strip()), f"{path.relative_to(ROOT)}: empty Mermaid diagram")
            require(bool(re.match(r"[A-Za-z][A-Za-z0-9_-]*", diagram.lstrip())), f"{path.relative_to(ROOT)}: Mermaid diagram has no type")


def main() -> None:
    require(CURRENT.is_dir(), "docs/current is missing")
    files = list(CURRENT.rglob("*.md"))
    require(files, "docs/current has no Markdown documents")
    validate_wikilinks(files)
    validate_markdown_links(files)
    validate_mermaid(files)
    print("PASS: downstream documentation links and Mermaid structure")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
