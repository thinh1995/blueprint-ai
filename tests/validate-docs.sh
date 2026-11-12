#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

require_text() {
    local file="$1"
    local text="$2"

    grep -Fq -- "$text" "$ROOT_DIR/$file" || {
        echo "Missing '$text' in $file" >&2
        exit 1
    }
}

for file in \
    "docs/templates/feature-spec-template/1. Product Spec.md" \
    "docs/templates/feature-spec-template/2. Tech Spec.md" \
    "docs/templates/feature-spec-template/3. QA Spec.md" \
    "docs/templates/feature-spec-template/4. Tasks.md"; do
    require_text "$file" "approved_by:"
    require_text "$file" "approved_at:"
    require_text "$file" "approval_evidence:"
    require_text "$file" "source_revision:"
done

require_text "docs/templates/3. Task Evidence Template.md" "Acceptance criteria and validation"
require_text "docs/templates/3. Task Evidence Template.md" "output_artifact_path:"
require_text "AGENTS.md" "Never invent file/line references"
require_text "AGENTS.md" "untrusted data"
require_text "AGENTS.md" "Do not introduce speculative abstractions"
require_text "AGENTS.md" "Make surgical changes"
require_text "docs/current/00 - Onboarding/3. AI Agent Workflow.md" "Simplicity first"
require_text "docs/current/00 - Onboarding/3. AI Agent Workflow.md" "Surgical changes"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified: false"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified_at:"

require_text "docs/current/01 - Overview/BA Foundation.md" "Stakeholders and RACI"
require_text "docs/current/01 - Overview/BA Foundation.md" "Business rules catalogue"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" "Mermaid is the official diagram format"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" '```mermaid'
require_text "docs/templates/feature-spec-template/1. Product Spec.md" "Stakeholder, user stories, and use cases"
require_text "docs/templates/feature-spec-template/1. Product Spec.md" "## Traceability"
require_text "docs/templates/feature-spec-template/2. Tech Spec.md" "Tool permissions, timeout, retry, fallback"
require_text "docs/templates/feature-spec-template/3. QA Spec.md" "prompt injection"
for file in \
    "docs/templates/examples/ai-support-agent/1. Product Spec.md" \
    "docs/templates/examples/ai-support-agent/2. Tech Spec.md" \
    "docs/templates/examples/ai-support-agent/3. QA Spec.md" \
    "docs/templates/examples/ai-support-agent/4. Tasks.md"; do
    require_text "$file" "status: example"
done
require_text "AGENTS.md" "NEEDS CLARIFICATION"
require_text "AGENTS.md" "Owned paths"
require_text "docs/current/00 - Onboarding/3. AI Agent Workflow.md" "Spec-Driven Feature Prompts"
require_text "docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md" "tools/validate-docs.py --require-tasks"
require_text "docs/internal/acceptance-matrices/V5_ACCEPTANCE_MATRIX.md" 'Release target: `0.5.0`'
require_text "docs/internal/acceptance-matrices/V5_1_ACCEPTANCE_MATRIX.md" 'Release target: `0.5.1`'
require_text "docs/templates/examples/ai-support-agent/1. Product Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "sequenceDiagram"
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "stateDiagram-v2"
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "docs/templates"
require_text "docs/internal/acceptance-matrices/V3_ACCEPTANCE_MATRIX.md" 'Release target: `0.3.0`'
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "tools/validate-docs.py"
require_text ".github/workflows/ai-template-validation.yml" "fetch-depth: 0"
require_text ".github/workflows/ai-template-validation.yml" "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020"
require_text ".github/workflows/ai-template-validation.yml" "node-version: 22.14.0"
require_text "README.md" "--dry-run --update"
require_text "docs/current/00 - Onboarding/1. Setup Guide.md" "RECOVERY.md"
python3 -B "$ROOT_DIR/tests/validate-template-docs.py"
python3 -B "$ROOT_DIR/tests/validate-skills-contract.py"
python3 -B "$ROOT_DIR/tests/validate-skills-contract.py" --self-test
python3 -B "$ROOT_DIR/tests/validate-orchestration-contract.py"
python3 -B "$ROOT_DIR/tests/validate-runtime-delegation-fixture.py"
python3 -B "$ROOT_DIR/tests/validate-antigravity-conformance-fixture.py"

python3 -B - "$ROOT_DIR/tests" <<'PY'
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
tests_dir = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(tests_dir))

from docs_validation import (
    validate_clarify_gate,
    validate_feature_folder,
    validate_feature_specs,
    validate_links,
)


def expect_fail(fn, label: str, expected_substr: str = "") -> None:
    try:
        fn()
    except ValueError as exc:
        if expected_substr and expected_substr.lower() not in str(exc).lower():
            raise AssertionError(f"{label}: expected '{expected_substr}' in '{exc}'") from exc
        return
    raise AssertionError(f"{label}: expected ValueError, got success")


APPROVED_FM = (
    "---\n"
    "status: approved\n"
    "owner: engineering\n"
    "approved_by: lead-eng\n"
    "approved_at: 2026-11-12\n"
    "approval_evidence: PR-42\n"
    "source_revision: b8b83557c19217002b0586c052b68e2684706057\n"
    "---\n"
)

DRAFT_FM = (
    "---\n"
    "status: draft\n"
    "owner: engineering\n"
    "approved_by:\n"
    "approved_at:\n"
    "approval_evidence:\n"
    "source_revision:\n"
    "---\n"
)


def write_valid_pack(
    feat: Path,
    fm: str = APPROVED_FM,
    five_col_qa: bool = False,
    with_tasks: bool = True,
    tasks_rows: str | None = None,
) -> None:
    feat.mkdir(parents=True, exist_ok=True)
    (feat / "1. Product Spec.md").write_text(
        fm
        + "# Product\n\n## Acceptance criteria\n\n"
        + "| ID | Scenario | Expected result |\n|---|---|---|\n"
        + "| AC-01 | Valid login | Session issued |\n"
        + "| AC-02 | Invalid token | 401 returned |\n\n"
        + "## Open decisions\n\n- [x] Resolved.\n",
        encoding="utf-8",
    )
    (feat / "2. Tech Spec.md").write_text(
        fm
        + "# Tech\n\n## Acceptance-criteria mapping\n\n"
        + "| Product AC | Implementation approach | Automated validation |\n|---|---|---|\n"
        + "| AC-01 | Session service | `pytest -k login \\| tee log.txt` |\n"
        + "| AC-02 | Auth middleware | `pytest -k unauthorized` |\n\n"
        + "## Risks and open decisions\n\n- [x] Mitigated.\n",
        encoding="utf-8",
    )
    if five_col_qa:
        trace_table = (
            "| Business goal / rule | Product AC | QA case(s) | Automated test location / command | Owner |\n"
            "|---|---|---|---|---|\n"
            "| BR-01 | AC-01 | QA-01 | `pytest tests/test_auth.py \\| cat` | qa |\n"
            "| BR-02 | AC-02 | QA-02 | `pytest tests/test_auth.py` | qa |\n"
        )
    else:
        trace_table = (
            "| Product AC | QA case(s) | Automated test location / command | Owner |\n"
            "|---|---|---|---|\n"
            "| AC-01 | QA-01 | `pytest tests/test_auth.py \\| cat` | qa |\n"
            "| AC-02 | QA-02 | `pytest tests/test_auth.py` | qa |\n"
        )
    (feat / "3. QA Spec.md").write_text(
        fm
        + "# QA\n\n## Coverage\n\n"
        + "| ID | Acceptance criterion | Preconditions | Steps | Expected result | Automated? |\n"
        + "|---|---|---|---|---|---|\n"
        + "| QA-01 | AC-01 | User exists | Login | 200 OK | yes |\n"
        + "| QA-02 | AC-02 | Bad token | Call API | 401 | yes |\n\n"
        + "## Traceability and test ownership\n\n"
        + trace_table,
        encoding="utf-8",
    )
    if with_tasks:
        rows = tasks_rows or (
            "| T-01 | done | yes | - | AC-01 | `src/api` | Build API | `pytest tests/api \\| head -n 5` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/api_v2/users.py` | Build v2 | `pytest tests/api_v2` |\n"
        )
        (feat / "4. Tasks.md").write_text(
            fm
            + "# Tasks — Auth\n\n## Pre-implementation readiness checklist\n\n"
            + "- [x] AGENTS.md Constitution check passed.\n\n"
            + "## Execution tasks\n\n"
            + "| Task ID | Status | [P] | Depends on | Related AC | Owned paths | Summary | Verification |\n"
            + "|---|---|---|---|---|---|---|---|\n"
            + rows,
            encoding="utf-8",
        )


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    docs = root / "docs"
    current = docs / "current"
    features = current / "05 - Product Features"
    features.mkdir(parents=True)

    # 1. Code-stripped link validation vs real broken link
    note = current / "prompts.md"
    note.write_text(
        "---\nstatus: active\nowner: eng\n---\n"
        "Inline `[[1. Product Spec]]` and ``[missing](nope.md)`` are code.\n\n"
        "```markdown\n[[Unresolved Wiki]] and [broken](missing-file.md)\n```\n",
        encoding="utf-8",
    )
    validate_links(root, docs, [note])
    broken = current / "broken.md"
    broken.write_text("Real broken [link](does-not-exist.md)\n", encoding="utf-8")
    expect_fail(lambda: validate_links(root, docs, [note, broken]), "broken link outside code", "missing Markdown link")
    broken.unlink()

    # 2. Draft <=3 clarify tags pass; >3 fail
    draft_note = current / "draft-spec.md"
    draft_note.write_text(
        DRAFT_FM
        + "[NEEDS CLARIFICATION: q1]\n[NEEDS CLARIFICATION: q2]\n[NEEDS CLARIFICATION: q3]\n"
        + "`[NEEDS CLARIFICATION: ignored-in-code]`\n",
        encoding="utf-8",
    )
    validate_clarify_gate(root, [draft_note])
    draft_note.write_text(
        DRAFT_FM + "\n".join(f"[NEEDS CLARIFICATION: q{i}]" for i in range(4)) + "\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [draft_note]), ">3 clarify tags in draft", "3")
    draft_note.unlink()

    # 3. Domain note with status: approved and no approved_by passes; numbered spec fails on clarify/checkbox/placeholder
    overview = current / "Overview.md"
    overview.write_text("---\nstatus: approved\nowner: architecture\n---\n# Overview\n", encoding="utf-8")
    validate_clarify_gate(root, [overview])

    feat_ok = features / "001-auth"
    write_valid_pack(feat_ok, fm=APPROVED_FM, five_col_qa=False, with_tasks=True)
    write_valid_pack(features / "002-five-col", fm=APPROVED_FM, five_col_qa=True, with_tasks=True)
    all_files = sorted(current.rglob("*.md"))
    validate_clarify_gate(root, all_files)
    assert validate_feature_specs(root, features, require_tasks=True) == []

    # Clarify marker in approved spec fails
    bad_clarify = features / "003-bad"
    write_valid_pack(bad_clarify)
    (bad_clarify / "1. Product Spec.md").write_text(
        (bad_clarify / "1. Product Spec.md").read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: leak]\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Product Spec.md"]), "clarify in approved")

    # Open checkbox in readiness checklist fails
    write_valid_pack(bad_clarify)
    (bad_clarify / "4. Tasks.md").write_text(
        (bad_clarify / "4. Tasks.md").read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "4. Tasks.md"]), "unchecked readiness box")

    # Placeholder approved_by: todo fails on numbered spec
    for bad_token in ("todo", "tbd", "draft", ""):
        write_valid_pack(bad_clarify)
        (bad_clarify / "2. Tech Spec.md").write_text(
            (bad_clarify / "2. Tech Spec.md")
            .read_text(encoding="utf-8")
            .replace("approved_by: lead-eng", f"approved_by: {bad_token}"),
            encoding="utf-8",
        )
        expect_fail(
            lambda: validate_clarify_gate(root, [bad_clarify / "2. Tech Spec.md"]),
            f"placeholder approved_by={bad_token!r}",
        )

    # 4. Mixed draft/approved sibling specs fail pack-level consistency
    write_valid_pack(bad_clarify, fm=APPROVED_FM)
    (bad_clarify / "2. Tech Spec.md").write_text(
        (bad_clarify / "2. Tech Spec.md").read_text(encoding="utf-8").replace("status: approved", "status: draft"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "mixed draft/approved pack")

    # 5. Ghost AC-99 fails even in draft
    write_valid_pack(bad_clarify, fm=DRAFT_FM)
    (bad_clarify / "4. Tasks.md").write_text(
        (bad_clarify / "4. Tasks.md").read_text(encoding="utf-8").replace("AC-02", "AC-99"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "ghost AC-99 in draft", "AC-99")

    # 6. Missing AC-02 coverage in approved fails; legacy 3-file approved warns without --require-tasks and fails with it
    write_valid_pack(bad_clarify, fm=APPROVED_FM)
    (bad_clarify / "2. Tech Spec.md").write_text(
        "\n".join(
            line
            for line in (bad_clarify / "2. Tech Spec.md").read_text(encoding="utf-8").splitlines()
            if "AC-02" not in line
        )
        + "\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "missing AC-02 in Tech", "AC-02")

    legacy_3 = features / "004-legacy"
    write_valid_pack(legacy_3, fm=APPROVED_FM, with_tasks=False)
    warns = validate_feature_folder(root, legacy_3, require_tasks=False)
    assert len(warns) == 1 and "4. Tasks.md" in warns[0], f"expected legacy 3-file warning, got {warns}"
    expect_fail(lambda: validate_feature_folder(root, legacy_3, require_tasks=True), "legacy 3-file with --require-tasks", "4. Tasks.md")

    # 7. Invalid Status, cycle, glob in Owned paths, and overlapping [P] Owned paths
    write_valid_pack(
        bad_clarify,
        fm=DRAFT_FM,
        tasks_rows="| T-01 |bogus| no | - | AC-01 | `src/a` | Bad status | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "invalid task Status", "status")

    write_valid_pack(
        bad_clarify,
        fm=DRAFT_FM,
        tasks_rows=(
            "| T-01 | todo | no | T-02 | AC-01 | `src/a` | A | `pytest` |\n"
            "| T-02 | todo | no | T-01 | AC-02 | `src/b` | B | `pytest` |\n"
        ),
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "task dependency cycle", "cycle")

    write_valid_pack(
        bad_clarify,
        fm=DRAFT_FM,
        tasks_rows="| T-01 | todo | no | - | AC-01 | `src/*` | Glob | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "glob in Owned paths", "glob")

    write_valid_pack(
        bad_clarify,
        fm=DRAFT_FM,
        tasks_rows=(
            "| T-01 | todo | yes | - | AC-01 | `src/api/` | Parent | `pytest` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/other, src/api/users.py` | Child | `pytest` |\n"
        ),
    )
    expect_fail(lambda: validate_feature_folder(root, bad_clarify), "overlapping [P] Owned paths", "overlap")

    # CLI check for validate-project-docs.py --require-tasks on clean pack
    bad_clarify_files = list(bad_clarify.glob("*"))
    for f in bad_clarify_files:
        f.unlink()
    bad_clarify.rmdir()
    for f in legacy_3.glob("*"):
        f.unlink()
    legacy_3.rmdir()
    tools = root / "tools"
    tools.mkdir()
    (tools / "docs_validation.py").write_text((tests_dir / "docs_validation.py").read_text(encoding="utf-8"), encoding="utf-8")
    (tools / "validate-docs.py").write_text((tests_dir / "validate-project-docs.py").read_text(encoding="utf-8"), encoding="utf-8")
    subprocess.run([sys.executable, "-B", str(tools / "validate-docs.py"), "--require-tasks"], check=True, stdout=subprocess.DEVNULL)

print("PASS: semantic Clarify gate, cross-spec traceability, and [P] concurrency fixtures")
PY

echo "PASS: documentation guardrail validation"
