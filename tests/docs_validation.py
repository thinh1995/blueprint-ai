"""Shared, portable Markdown validation for repository and installed docs."""

import posixpath
import re
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def validate_links(root: Path, docs_root: Path, files: list[Path]) -> None:
    relative_paths = {path.relative_to(docs_root).with_suffix("").as_posix() for path in files}
    stems: dict[str, list[Path]] = {}
    for path in files:
        stems.setdefault(path.stem, []).append(path)

    wiki = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    markdown = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in files:
        content = read(path)
        for match in wiki.finditer(content):
            target = match.group(1).strip().replace("\\", "/")
            relative = posixpath.normpath((path.parent.relative_to(docs_root) / target).as_posix())
            current = f"current/{target}"
            if target in relative_paths or relative in relative_paths or current in relative_paths:
                continue
            require(len(stems.get(target, [])) == 1, f"{path.relative_to(root)}: unresolved or ambiguous link [[{target}]]")
        for match in markdown.finditer(content):
            target = match.group(1).split("#", 1)[0]
            require(not target.lower().startswith("file:"), f"{path.relative_to(root)}: unsupported Markdown URI scheme file:")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            candidate = (path.parent / target).resolve()
            require(candidate.is_relative_to(root), f"{path.relative_to(root)}: Markdown link target escapes project root {target}")
            require(candidate.is_file(), f"{path.relative_to(root)}: missing Markdown link target {target}")


def validate_mermaid(root: Path, files: list[Path]) -> None:
    block = re.compile(r"(?ms)^```mermaid[ \t]*\n(.*?)^```[ \t]*$")
    for path in files:
        content = read(path)
        diagrams = block.findall(content)
        require(content.count("```mermaid") == len(diagrams), f"{path.relative_to(root)}: malformed or unclosed Mermaid fence")
        for diagram in diagrams:
            require(bool(diagram.strip()), f"{path.relative_to(root)}: empty Mermaid diagram")
            require(bool(re.match(r"[A-Za-z][A-Za-z0-9_-]*", diagram.lstrip())), f"{path.relative_to(root)}: Mermaid diagram has no type")
