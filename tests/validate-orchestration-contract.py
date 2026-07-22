#!/usr/bin/env python3
"""Validate the repository's static documentation-sub-agent orchestration contract."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def require_text(path: Path, text: str) -> None:
    if text not in path.read_text(encoding="utf-8"):
        raise ValueError(f"{path.relative_to(ROOT)}: missing {text!r}")


def main() -> None:
    policy = ROOT / "AGENTS.md"
    prompt = ROOT / "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md"
    runtime = ROOT / "docs/current/00 - Onboarding/5. Model Runtime Instructions.md"
    contract = ROOT / "docs/templates/2. Documentation Subagent Contract.md"
    matrix = ROOT / "V4_ACCEPTANCE_MATRIX.md"

    for text in [
        "creating specialized sub-agents is mandatory before any documentation write",
        "source discovery; architecture/API; product/BA; and QA/traceability",
        "Fact / Assumption / Unknown",
        "If the host has no delegation capability",
    ]:
        require_text(policy, text)
    for text in [
        "capabilities actually available in the active host",
        "review, security, test/QA, or architecture",
        "explicit ownership",
        "Fact / Assumption / Unknown",
        "test or validation and review proportionate to their risk",
    ]:
        require_text(policy, text)
    for text in ["BẮT BUỘC tạo các sub-agent phù hợp", "không nói rằng đã tạo sub-agent"]:
        require_text(prompt, text)
    for text in ["Codex-compatible host", "Claude Code", "Antigravity CLI", "Qwen Code", "Gemma/custom harness"]:
        require_text(runtime, text)
    for text in ["## Roles", "## Required handoff", "## Coordinator completion gate"]:
        require_text(contract, text)
    for text in ["Mandatory delegation", "Unsupported host fallback"]:
        require_text(matrix, text)
    print("PASS: documentation sub-agent orchestration contract")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
