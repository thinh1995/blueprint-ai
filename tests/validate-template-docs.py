#!/usr/bin/env python3
"""Structural and semantic validation for this template repository."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# Validation is read-only; avoid creating __pycache__ artifacts in the template.
sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from docs_validation import (  # noqa: E402
    read,
    validate_clarify_gate,
    validate_feature_folder,
    validate_links,
    validate_mermaid,
)

DOCS = ROOT / "docs"
CURRENT = DOCS / "current"
TEMPLATES = DOCS / "templates"
SAMPLE = TEMPLATES / "examples/ai-support-agent"
MAX_COMBINED_CONTEXT_BYTES = 19000


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def markdown_files(docs_root: Path = DOCS) -> list[Path]:
    return [
        path
        for path in docs_root.rglob("*.md")
        if not path.is_symlink() and "internal" not in path.relative_to(docs_root).parts
    ]


def require_text(path: Path, text: str) -> str:
    content = read(path)
    require(text in content, f"{path.relative_to(ROOT)}: missing {text!r}")
    return content


def main() -> None:
    version = json.loads((ROOT / "template-manifest.json").read_text(encoding="utf-8"))["version"]
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
    require_text(ROOT / "CLAUDE.md", "@AGENTS.md")
    require_text(ROOT / "GEMINI.md", "Antigravity CLI Project Instructions")
    require_text(ROOT / "QWEN.md", "AGENTS.md")
    require_text(ROOT / "adapters/cursor-agents.mdc", "alwaysApply: true")
    require_text(ROOT / "adapters/copilot-instructions.md", "AGENTS.md")

    for adapter_rel in (
        "CLAUDE.md",
        "GEMINI.md",
        "QWEN.md",
        "adapters/copilot-instructions.md",
        "adapters/cursor-agents.mdc",
    ):
        adapter_text = read(ROOT / adapter_rel)
        require(
            "3. AI Agent Workflow.md" not in adapter_text,
            f"{adapter_rel}: startup context diet forbids '3. AI Agent Workflow.md'",
        )

    agents_bytes = len((ROOT / "AGENTS.md").read_bytes())
    skill_sizes = [len(p.read_bytes()) for p in sorted((ROOT / "skills").glob("sdd-*/SKILL.md")) if not p.is_symlink()]
    require(bool(skill_sizes), "skills: expected canonical sdd-*/SKILL.md files")
    peak_context_bytes = agents_bytes + max(skill_sizes)
    require(
        peak_context_bytes <= MAX_COMBINED_CONTEXT_BYTES,
        f"startup context budget exceeded: AGENTS.md ({agents_bytes} B) + max SKILL.md ({max(skill_sizes)} B) "
        f"= {peak_context_bytes} B > {MAX_COMBINED_CONTEXT_BYTES} B",
    )

    runtime_instructions = require_text(
        CURRENT / "00 - Onboarding/5. Model Runtime Instructions.md",
        "không bao giờ tự trở thành system prompt",
    )
    for expected_url in (
        "https://agentskills.io/specification",
        "https://code.claude.com/docs/en/skills",
        "https://antigravity.google/docs/cli-subagents/",
        "https://qwenlm.github.io/qwen-code-docs/en/users/features/sub-agents/",
        "https://opencode.ai/docs/rules/",
        "https://developers.openai.com/codex/guides/agents-md",
        "https://cursor.com/docs/context/rules",
        "https://docs.github.com/en/copilot/customizing-copilot/adding-repository-custom-instructions-for-github-copilot",
    ):
        require(
            expected_url in runtime_instructions,
            f"00 - Onboarding/5. Model Runtime Instructions.md: missing expected URL: {expected_url}",
        )
    require(
        "## Documentation sub-agent contract" in runtime_instructions,
        "00 - Onboarding/5. Model Runtime Instructions.md: missing ## Documentation sub-agent contract heading",
    )
    require(
        "--without-skills" in runtime_instructions
        and "--set-models" in runtime_instructions
        and ".agents/skills/" in runtime_instructions,
        "00 - Onboarding/5. Model Runtime Instructions.md: missing --set-models, --without-skills, or .agents/skills/ guidance",
    )

    require_text(TEMPLATES / "1. Agent System Prompt Template.md", "Prompting alone cannot enforce permissions")
    require_text(TEMPLATES / "2. Documentation Subagent Contract.md", "## Coordinator completion gate")
    require_text(TEMPLATES / "4. Runtime Delegation Evidence Template.md", "# Runtime Delegation Evidence")
    require_text(TEMPLATES / "mini-spec-template/1. Mini Spec.md", "## Acceptance criteria")
    require_text(TEMPLATES / "mini-spec-template/1. Mini Spec.md", "## Execution tasks")
    require_text(TEMPLATES / "mini-spec-template/1. Mini Spec.md", "contract_sha256")
    require_text(TEMPLATES / "feature-spec-template/README.md", "contract_sha256")
    require_text(CURRENT / "00 - Onboarding/4. Whole-Project Documentation Update Prompt.md", "BẮT BUỘC tạo")
    require_text(CURRENT / "05 - Product Features/README.md", "docs/templates/feature-spec-template/")
    require_text(CURRENT / "05 - Product Features/README.md", "docs/templates/mini-spec-template/")
    require_text(CURRENT / "05 - Product Features/README.md", "## Anti-fragmentation and supersession lifecycle")
    require_text(CURRENT / "05 - Product Features/README.md", "contract_sha256")
    require_text(CURRENT / "02 - Architecture/Architecture.md", "## Brownfield security and tech-debt triage")
    require_text(
        CURRENT / "06 - Infrastructure & Deployment/Infrastructure Spec.md",
        "Secrets management and security scanning",
    )
    require_text(ROOT / "AGENTS.md", "--supersede")
    require_text(ROOT / "AGENTS.md", "superseded_by")
    require_text(ROOT / "AGENTS.md", "contract_sha256")
    require_text(ROOT / "AGENTS.md", "Markdown H1/H2/H3 headings")
    require("Markdown ## headings" not in read(ROOT / "AGENTS.md"), "AGENTS.md: stale 'Markdown ## headings' remains")

    task_evidence_note = require_text(CURRENT / "00 - Onboarding/2. Task Evidence.md", "source_revision: self")
    require(
        "vẫn cần `tools/stamp-spec.py --amend`" not in task_evidence_note,
        "00 - Onboarding/2. Task Evidence.md: stale post-Squash-Merge 'vẫn cần `tools/stamp-spec.py --amend`' prose remains",
    )

    setup_guide = require_text(CURRENT / "00 - Onboarding/1. Setup Guide.md", "--without-skills")
    for setup_token in (
        "9 lệnh tắt Agent Skills",
        "/sdd-review",
        "tools/_sdd_core.py",
        "tools/stamp-spec.py",
        "tools/record-evidence.py",
        "--check-owned-paths",
        "source_revision: self",
        "contract_sha256",
    ):
        require(setup_token in setup_guide, f"00 - Onboarding/1. Setup Guide.md: missing {setup_token!r}")
    require(
        "8 lệnh tắt Agent Skills" not in setup_guide,
        "00 - Onboarding/1. Setup Guide.md: stale '8 lệnh tắt Agent Skills' remains",
    )

    vault_moc = require_text(CURRENT / "Vault Index MOC.md", "/sdd-review")
    require("contract_sha256" in vault_moc, "Vault Index MOC.md: missing 'contract_sha256'")
    require("8 giai đoạn" in vault_moc, "Vault Index MOC.md: missing '8 giai đoạn'")
    require("7 giai đoạn" not in vault_moc, "Vault Index MOC.md: stale '7 giai đoạn' remains")

    require_text(CURRENT / "00 - Onboarding/4. Whole-Project Documentation Update Prompt.md", "/sdd-docs")

    for readme_token in (
        "/sdd-docs",
        "/sdd-specify",
        "/sdd-fix",
        "/sdd-review",
        "--without-skills",
        "--set-models",
        "security-hardening",
        "tools/_sdd_core.py",
        "stamp-spec.py",
        "record-evidence.py",
        "--check-owned-paths",
        "contract_sha256",
    ):
        require_text(ROOT / "README.md", readme_token)

    sdd_prompts = require_text(CURRENT / "00 - Onboarding/6. Spec-Driven Feature Prompts.md", "contract_sha256")
    for slash_cmd in (
        "/sdd-specify",
        "/sdd-clarify",
        "/sdd-plan",
        "/sdd-tasks",
        "/sdd-analyze",
        "/sdd-implement",
        "/sdd-fix",
        "/sdd-review",
    ):
        require(slash_cmd in sdd_prompts, f"6. Spec-Driven Feature Prompts.md: missing {slash_cmd} shortcut")
    for stage in ("Specify", "Clarify", "Plan", "Tasks", "Analyze", "Implement", "Fix", "Review"):
        require(
            bool(re.search(rf"^##\s+\d+\.\s+{stage}\b", sdd_prompts, re.M)),
            f"6. Spec-Driven Feature Prompts.md: missing canonical stage heading for {stage}",
        )
    require_text(TEMPLATES / "feature-spec-template/4. Tasks.md", "AGENTS.md Constitution check")

    for path in [*CURRENT.rglob("*.md"), *TEMPLATES.rglob("*.md")]:
        if path.is_symlink():
            continue
        content = read(path)
        require(
            "*Khởi tạo:" not in content and "*Changelog:" not in content,
            f"{path.relative_to(ROOT)}: inherited template-repository changelog text",
        )

    product = require_text(SAMPLE / "1. Product Spec.md", "## Traceability")
    tech = read(SAMPLE / "2. Tech Spec.md")
    qa = read(SAMPLE / "3. QA Spec.md")
    for ac in ["AC-01", "AC-02", "AC-03"]:
        require(re.search(rf"^\| {ac} \|", tech, re.M), f"sample Tech Spec: missing mapping row for {ac}")
        require(re.search(rf"\| QA-\d+ \| {ac} \|", qa), f"sample QA Spec: missing mapping row for {ac}")
    require(
        re.search(r"^\| BG-01:.*\| ST-01 / UC-01 / BR-01 \| AC-01, AC-02 \|", product, re.M),
        "sample Product Spec: missing grounded-support traceability row",
    )
    require(
        re.search(r"^\| BG-01:.*\| UC-01 / BR-02 \| AC-03 \|", product, re.M),
        "sample Product Spec: missing safety-boundary traceability row",
    )

    files = markdown_files()
    validate_links(ROOT, DOCS, files)
    validate_mermaid(ROOT, files)
    validate_clarify_gate(ROOT, files, strict=True)
    validate_feature_folder(ROOT, SAMPLE, require_tasks=True, strict=True)
    print("PASS: template documentation, links, Mermaid structure, and traceability")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
