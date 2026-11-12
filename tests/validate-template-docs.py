#!/usr/bin/env python3
"""Structural and semantic validation for this template repository."""

import json
import re
import sys
from pathlib import Path

# Validation is read-only; avoid creating __pycache__ artifacts in the template.
sys.dont_write_bytecode = True

from docs_validation import (
    read,
    validate_clarify_gate,
    validate_feature_folder,
    validate_links,
    validate_mermaid,
)

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"
CURRENT = DOCS / "current"
TEMPLATES = DOCS / "templates"
SAMPLE = TEMPLATES / "examples/ai-support-agent"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def markdown_files() -> list[Path]:
    return [path for path in DOCS.rglob("*.md") if "internal" not in path.relative_to(DOCS).parts]


def require_text(path: Path, text: str) -> str:
    content = read(path)
    require(text in content, f"{path.relative_to(ROOT)}: missing {text!r}")
    return content


def main() -> None:
    version = json.loads((ROOT / "template-manifest.json").read_text())["version"]
    major, minor, patch = version.split(".")
    if major == "0" and patch == "0":
        matrix_tag = minor
    elif major == "0":
        matrix_tag = f"{minor}_{patch}"
    else:
        matrix_tag = f"{major}_{minor}_{patch}"
    matrix = DOCS / "internal/acceptance-matrices" / f"V{matrix_tag}_ACCEPTANCE_MATRIX.md"
    require_text(ROOT / "README.md", f"Current release: `{version}`.")
    changelog = read(ROOT / "CHANGELOG.md")
    require(
        bool(re.search(rf"^## \[{re.escape(version)}\] - \d{{4}}-\d{{2}}-\d{{2}}$", changelog, re.M)),
        f"CHANGELOG.md: missing dated heading for [{version}]",
    )
    require_text(matrix, f"Release target: `{version}`")
    require_text(ROOT / "GEMINI.md", "Antigravity CLI Project Instructions")
    require_text(ROOT / "QWEN.md", "AGENTS.md")
    runtime_instructions = require_text(
        CURRENT / "00 - Onboarding/5. Model Runtime Instructions.md",
        "A file in the repository is **not** a system prompt.",
    )
    require(
        "https://antigravity.google/docs/cli-subagents/" in runtime_instructions,
        "00 - Onboarding/5. Model Runtime Instructions.md: missing expected text: https://antigravity.google/docs/cli-subagents/",
    )
    require(
        "https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/" in runtime_instructions,
        "00 - Onboarding/5. Model Runtime Instructions.md: missing expected text: https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/",
    )
    require_text(TEMPLATES / "1. Agent System Prompt Template.md", "Prompting alone cannot enforce permissions")
    require_text(TEMPLATES / "2. Documentation Subagent Contract.md", "## Coordinator completion gate")
    require_text(TEMPLATES / "4. Runtime Delegation Evidence Template.md", "# Runtime Delegation Evidence")
    require_text(CURRENT / "00 - Onboarding/4. Whole-Project Documentation Update Prompt.md", "BẮT BUỘC tạo")
    require(
        "Documentation sub-agent contract" in runtime_instructions,
        "00 - Onboarding/5. Model Runtime Instructions.md: missing expected text: Documentation sub-agent contract",
    )
    require_text(CURRENT / "05 - Product Features/README.md", "docs/templates/feature-spec-template/")
    sdd_prompts = read(CURRENT / "00 - Onboarding/6. Spec-Driven Feature Prompts.md")
    for stage in ("Specify", "Clarify", "Plan", "Tasks", "Analyze", "Implement"):
        require(
            bool(re.search(rf"^##\s+\d+\.\s+{stage}\b", sdd_prompts, re.M)),
            f"6. Spec-Driven Feature Prompts.md: missing canonical stage heading for {stage}",
        )
    require_text(TEMPLATES / "feature-spec-template/4. Tasks.md", "AGENTS.md Constitution check")

    for path in [*CURRENT.rglob("*.md"), *TEMPLATES.rglob("*.md")]:
        content = read(path)
        require("*Khởi tạo:" not in content and "*Changelog:" not in content, f"{path.relative_to(ROOT)}: inherited template-repository changelog text")

    product = require_text(SAMPLE / "1. Product Spec.md", "## Traceability")
    tech = read(SAMPLE / "2. Tech Spec.md")
    qa = read(SAMPLE / "3. QA Spec.md")
    for ac in ["AC-01", "AC-02", "AC-03"]:
        require(re.search(rf"^\| {ac} \|", tech, re.M), f"sample Tech Spec: missing mapping row for {ac}")
        require(re.search(rf"\| QA-\d+ \| {ac} \|", qa), f"sample QA Spec: missing mapping row for {ac}")
    require(re.search(r"^\| BG-01:.*\| ST-01 / UC-01 / BR-01 \| AC-01, AC-02 \|", product, re.M), "sample Product Spec: missing grounded-support traceability row")
    require(re.search(r"^\| BG-01:.*\| UC-01 / BR-02 \| AC-03 \|", product, re.M), "sample Product Spec: missing safety-boundary traceability row")

    files = markdown_files()
    validate_links(ROOT, DOCS, files)
    validate_mermaid(ROOT, files)
    validate_clarify_gate(ROOT, files)
    validate_feature_folder(ROOT, SAMPLE, require_tasks=True)
    print("PASS: template documentation, links, Mermaid structure, and traceability")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
