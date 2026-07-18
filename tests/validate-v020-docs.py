#!/usr/bin/env python3
"""Structural validation for the v0.2.0 BA and Mermaid documentation pack."""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs/current"
SAMPLE = DOCS / "05 - Product Features/Example AI Support Agent"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def require_text(path: Path, text: str) -> str:
    content = read(path)
    require(text in content, f"{path.relative_to(ROOT)}: missing {text!r}")
    return content


def extract_ids(text: str, prefix: str) -> set[str]:
    return set(re.findall(rf"\b{prefix}-\d+\b", text))


def validate_wikilinks() -> None:
    markdown_files = list(DOCS.rglob("*.md"))
    targets = set()
    for path in markdown_files:
        relative = path.relative_to(DOCS).with_suffix("").as_posix()
        targets.add(relative)
        targets.add(path.stem)

    pattern = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    missing = []
    for path in markdown_files:
        for match in pattern.finditer(read(path)):
            target = match.group(1).strip().replace("\\", "/")
            relative_target = (path.parent.relative_to(DOCS) / target).as_posix()
            if target not in targets and relative_target not in targets:
                missing.append(f"{path.relative_to(ROOT)} -> [[{target}]]")
    require(not missing, "unresolved Obsidian links:\n" + "\n".join(missing))


def validate_mermaid() -> None:
    for path in DOCS.rglob("*.md"):
        content = read(path)
        require(content.count("```mermaid") == content.count("```mermaid\n"), f"{path.relative_to(ROOT)}: malformed Mermaid fence")
        if "```mermaid" in content:
            blocks = re.findall(r"```mermaid\n(.*?)```", content, re.S)
            require(blocks, f"{path.relative_to(ROOT)}: Mermaid block is not closed")
            for block in blocks:
                first = block.strip().splitlines()[0] if block.strip() else ""
                require(first in {"flowchart TD", "flowchart LR", "sequenceDiagram", "stateDiagram-v2"}, f"{path.relative_to(ROOT)}: unsupported or empty Mermaid diagram start {first!r}")


def main() -> None:
    version = json.loads((ROOT / "template-manifest.json").read_text())["version"]
    require(version == "0.2.0", f"template-manifest.json: expected 0.2.0, got {version}")
    require_text(ROOT / "README.md", "Current release: `0.2.0`")
    require_text(ROOT / "CHANGELOG.md", "## 0.2.0 — 2026-07-18")
    require_text(ROOT / "V2_ACCEPTANCE_MATRIX.md", "Release target: `0.2.0`")

    foundation = ROOT / "docs/current/01 - Overview/BA Foundation.md"
    for section in ["Product scope", "Assumptions and constraints", "Authority and sources", "Decision log", "Stakeholders and RACI"]:
        require_text(foundation, section)

    product = SAMPLE / "1. Product Spec.md"
    tech = SAMPLE / "2. Tech Spec.md"
    qa = SAMPLE / "3. QA Spec.md"
    product_text = require_text(product, "## Traceability")
    tech_text = read(tech)
    qa_text = read(qa)
    expected_acs = {"AC-01", "AC-02", "AC-03"}
    for path, content in [(product, product_text), (tech, tech_text), (qa, qa_text)]:
        require(expected_acs <= extract_ids(content, "AC"), f"{path.relative_to(ROOT)}: every sample AC must be mapped")
    require({"BG-01", "ST-01", "UC-01", "BR-01", "BR-02"} <= extract_ids(product_text, "BG") | extract_ids(product_text, "ST") | extract_ids(product_text, "UC") | extract_ids(product_text, "BR"), "sample Product Spec: missing BA traceability IDs")
    require_text(product, "Account-changing request?")
    require_text(tech, "HandoffUnavailable")
    for path in [product, tech]:
        require_text(path, "Scope:")
        require_text(path, "Assumptions:")
        require_text(path, "Linked requirements:")
    for diagram_type in ["flowchart TD", "sequenceDiagram", "stateDiagram-v2", "flowchart LR"]:
        require(diagram_type in product_text or diagram_type in tech_text, f"sample: missing {diagram_type}")

    validate_wikilinks()
    validate_mermaid()
    print("PASS: v0.2.0 BA, link, version, and Mermaid-structure validation")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
