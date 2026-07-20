#!/usr/bin/env python3
"""Structural and semantic validation for this template repository."""

import json
import posixpath
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CURRENT = DOCS / "current"
TEMPLATES = DOCS / "templates"
SAMPLE = TEMPLATES / "examples/ai-support-agent"
VERSION = "0.3.1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def markdown_files() -> list[Path]:
    return [path for path in DOCS.rglob("*.md") if "internal" not in path.relative_to(DOCS).parts]


def validate_links(files: list[Path]) -> None:
    relative_paths = {path.relative_to(DOCS).with_suffix("").as_posix() for path in files}
    stems: dict[str, list[Path]] = {}
    for path in files:
        stems.setdefault(path.stem, []).append(path)

    wiki = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    markdown = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in files:
        content = read(path)
        for match in wiki.finditer(content):
            target = match.group(1).strip().replace("\\", "/")
            relative = posixpath.normpath((path.parent.relative_to(DOCS) / target).as_posix())
            current = f"current/{target}"
            if target in relative_paths or relative in relative_paths or current in relative_paths:
                continue
            require(len(stems.get(target, [])) == 1, f"{path.relative_to(ROOT)}: unresolved or ambiguous link [[{target}]]")
        for match in markdown.finditer(content):
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
        blocks = block.findall(content)
        require(content.count("```mermaid") == len(blocks), f"{path.relative_to(ROOT)}: malformed or unclosed Mermaid fence")
        for diagram in blocks:
            require(bool(diagram.strip()), f"{path.relative_to(ROOT)}: empty Mermaid diagram")
            require(bool(re.match(r"[A-Za-z][A-Za-z0-9_-]*", diagram.lstrip())), f"{path.relative_to(ROOT)}: Mermaid diagram has no type")


def require_text(path: Path, text: str) -> str:
    content = read(path)
    require(text in content, f"{path.relative_to(ROOT)}: missing {text!r}")
    return content


def main() -> None:
    require(json.loads((ROOT / "template-manifest.json").read_text())["version"] == VERSION, "template manifest version is not 0.3.1")
    require_text(ROOT / "README.md", "Current release: `0.3.1`.")
    require_text(ROOT / "CHANGELOG.md", "## 0.3.1 — 2026-07-20")
    require_text(ROOT / "V3_1_ACCEPTANCE_MATRIX.md", "Release target: `0.3.1`")
    require_text(ROOT / "GEMINI.md", "AGENTS.md")
    require_text(ROOT / "QWEN.md", "AGENTS.md")
    require_text(CURRENT / "00 - Onboarding/5. Model Runtime Instructions.md", "A file in the repository is **not** a system prompt.")
    require_text(TEMPLATES / "agent-system-prompt-template.md", "Prompting alone cannot enforce permissions")
    require_text(CURRENT / "05 - Product Features/README.md", "docs/templates/feature-spec-template/")

    for path in [*CURRENT.rglob("*.md"), *TEMPLATES.rglob("*.md")]:
        require("*Khởi tạo:" not in read(path) and "*Changelog:" not in read(path), f"{path.relative_to(ROOT)}: inherited template-repository changelog text")

    product = require_text(SAMPLE / "1. Product Spec.md", "## Traceability")
    tech = read(SAMPLE / "2. Tech Spec.md")
    qa = read(SAMPLE / "3. QA Spec.md")
    for ac in ["AC-01", "AC-02", "AC-03"]:
        require(re.search(rf"^\| {ac} \|", tech, re.M), f"sample Tech Spec: missing mapping row for {ac}")
        require(re.search(rf"\| QA-\d+ \| {ac} \|", qa), f"sample QA Spec: missing mapping row for {ac}")
    require(re.search(r"^\| BG-01:.*\| ST-01 / UC-01 / BR-01 \| AC-01, AC-02 \|", product, re.M), "sample Product Spec: missing grounded-support traceability row")
    require(re.search(r"^\| BG-01:.*\| UC-01 / BR-02 \| AC-03 \|", product, re.M), "sample Product Spec: missing safety-boundary traceability row")

    files = markdown_files()
    validate_links(files)
    validate_mermaid(files)
    print("PASS: template documentation, links, Mermaid structure, and traceability")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
