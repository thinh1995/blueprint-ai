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
    "docs/templates/mini-spec-template/1. Mini Spec.md" \
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
require_text "AGENTS.md" "3-Tier SDD Routing"
require_text "AGENTS.md" "Spec Amendment"
require_text "AGENTS.md" "Contract Language Rule"
require_text "adapters/cursor-agents.mdc" "alwaysApply: true"
require_text "adapters/copilot-instructions.md" "AGENTS.md"
require_text "docs/current/00 - Onboarding/3. AI Agent Workflow.md" "Simplicity first"
require_text "docs/current/00 - Onboarding/3. AI Agent Workflow.md" "Surgical changes"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified: false"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified_at:"

require_text "docs/current/01 - Overview/BA Foundation.md" "Stakeholders and RACI"
require_text "docs/current/01 - Overview/BA Foundation.md" "Business rules catalogue"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" "diagram_format: mermaid"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" "**Mermaid** là định dạng sơ đồ chuẩn duy nhất"
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
require_text "docs/internal/acceptance-matrices/V6_ACCEPTANCE_MATRIX.md" 'Release target: `0.6.0`'
require_text "docs/internal/acceptance-matrices/V6_1_ACCEPTANCE_MATRIX.md" 'Release target: `0.6.1`'
require_text "docs/internal/acceptance-matrices/V7_ACCEPTANCE_MATRIX.md" 'Release target: `0.7.0`'
require_text "AGENTS.md" "stamp-spec.py"
require_text "AGENTS.md" "--check-owned-paths"
require_text "AGENTS.md" "/sdd-review"
require_text "docs/current/00 - Onboarding/2. Task Evidence.md" "source_revision: self"
require_text "docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md" "## 8. Review"
require_text "docs/current/02 - Architecture/Architecture.md" "## Brownfield security and tech-debt triage"
require_text "docs/current/05 - Product Features/README.md" "## Anti-fragmentation and supersession lifecycle"
require_text "docs/current/06 - Infrastructure & Deployment/Infrastructure Spec.md" "Secrets management and security scanning"
require_text "docs/templates/examples/ai-support-agent/1. Product Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "sequenceDiagram"
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "stateDiagram-v2"
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "docs/templates"
require_text "docs/internal/acceptance-matrices/V3_ACCEPTANCE_MATRIX.md" 'Release target: `0.3.0`'
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "tools/validate-docs.py"
require_text ".github/workflows/ai-template-validation.yml" "fetch-depth: 0"
require_text ".github/workflows/ai-template-validation.yml" "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
require_text ".github/workflows/ai-template-validation.yml" "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1"
require_text ".github/workflows/ai-template-validation.yml" "node-version: 22.14.0"
require_text ".github/workflows/ai-template-validation.yml" "workflow_dispatch:"
require_text ".github/workflows/ai-template-validation.yml" "concurrency:"
require_text ".github/workflows/ai-template-validation.yml" "bash setup.sh --doctor"
require_text ".github/workflows/ai-template-validation.yml" "tools/validate-task-evidence.py"
require_text "README.md" "--dry-run --update"
require_text "docs/current/00 - Onboarding/1. Setup Guide.md" "RECOVERY.md"
python3 -B "$ROOT_DIR/tests/validate-template-docs.py"
python3 -B "$ROOT_DIR/tests/validate-skills-contract.py"
python3 -B "$ROOT_DIR/tests/validate-skills-contract.py" --self-test
python3 -B "$ROOT_DIR/tests/validate-orchestration-contract.py"
python3 -B "$ROOT_DIR/tests/validate-runtime-delegation-fixture.py"
python3 -B "$ROOT_DIR/tests/validate-antigravity-conformance-fixture.py"

python3 -B - "$ROOT_DIR/tools" "$ROOT_DIR" <<'PY'
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
tools_src_dir = Path(sys.argv[1]).resolve()
repo_root = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(tools_src_dir))

from docs_validation import (
    validate_clarify_gate,
    validate_feature_folder,
    validate_feature_specs,
    validate_links,
    validate_mermaid,
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


def write_mini_spec(feat: Path, fm: str = APPROVED_FM, rows: str | None = None) -> None:
    feat.mkdir(parents=True, exist_ok=True)
    exec_rows = rows or (
        "| T-01 | todo | no | - | - | `src/config.py` | Prep config | `pytest tests/test_cfg.py` |\n"
        "| T-02 | todo | yes | T-01 | AC-01 | `src/login.py` | Login endpoint | `pytest tests/test_login.py` |\n"
        "| T-03 | todo | yes | T-01 | AC-02 | `src/guard.py` | Reject bad token | `pytest tests/test_guard.py` |\n"
    )
    (feat / "1. Mini Spec.md").write_text(
        fm
        + "# Mini Spec — Quick Auth\n\n"
        + "## Acceptance criteria\n\n"
        + "| ID | Scenario | Expected result |\n|---|---|---|\n"
        + "| AC-01 | Valid login | 200 OK |\n"
        + "| AC-02 | Invalid token | 401 Unauthorized |\n\n"
        + "## Pre-implementation readiness checklist\n\n"
        + "- [x] AGENTS.md Constitution check passed.\n\n"
        + "## Execution tasks\n\n"
        + "| Task ID | Status | [P] | Depends on | Related AC | Owned paths | Summary | Verification |\n"
        + "|---|---|---|---|---|---|---|---|\n"
        + exec_rows,
        encoding="utf-8",
    )


with tempfile.TemporaryDirectory() as tmp:
    root = Path(tmp).resolve()
    docs = root / "docs"
    current = docs / "current"
    features = current / "05 - Product Features"
    features.mkdir(parents=True)

    # 1. Code-stripped link validation, pre-unquote URI checks, %20 links, docs/current/ wikilinks, and Obsidian embeds
    (current / "Target Note.md").write_text("---\nstatus: active\nowner: eng\n---\n# Target\n\n## Sec\n", encoding="utf-8")
    (current / "diagram.png").write_bytes(b"\x89PNG\r\n")
    note = current / "prompts.md"
    note.write_text(
        "---\nstatus: active\nowner: eng\ntags: [moc, docs]\nsource_paths: [AGENTS.md]\n---\n"
        "Inline `[[1. Product Spec]]` and ``[missing](nope.md)`` are code.\n\n"
        "Valid [spaced](./Target%20Note.md), [[docs/current/Target Note#Sec|Alias]], and ![[diagram.png|600]].\n\n"
        "```markdown\n[[Unresolved Wiki]] and [broken](missing-file.md)\n```\n",
        encoding="utf-8",
    )
    target_note = current / "Target Note.md"
    validate_links(root, docs, [note, target_note])
    validate_clarify_gate(root, [note, target_note], strict=True)

    broken = current / "broken.md"
    broken.write_text("Real broken [link](does-not-exist.md)\n", encoding="utf-8")
    expect_fail(lambda: validate_links(root, docs, [note, target_note, broken]), "broken link outside code", "missing Markdown link")

    for bad_uri in ("file%3A///etc/passwd", "javascript:alert(1)"):
        broken.write_text(f"Blocked [uri]({bad_uri})\n", encoding="utf-8")
        expect_fail(lambda: validate_links(root, docs, [broken]), f"bad uri {bad_uri}", "unsupported Markdown URI scheme")

    broken.write_text("Traversal embed ![[../../etc/passwd]]\n", encoding="utf-8")
    expect_fail(lambda: validate_links(root, docs, [broken]), "embed traversal")
    broken.unlink()

    # Mermaid %%{init:...}%% directive and 4-backtick outer fence support
    mermaid_note = current / "mermaid-test.md"
    mermaid_note.write_text(
        "```mermaid\n%%{init: {'theme': 'neutral'}}%%\nflowchart LR\n  A[\"Start\"] --> B[\"End\"]\n```\n\n"
        "````markdown\nNested example:\n```mermaid\nnot-a-diagram-inside-outer-fence\n```\n````\n",
        encoding="utf-8",
    )
    validate_mermaid(root, [mermaid_note])
    mermaid_note.unlink()

    # 2. Draft <=3 clarify tags pass; >3 fail; fail-closed status enum vs superseded/archived
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

    draft_note.write_text("---\nstatus: archived\nowner: eng\n---\n# Old\n", encoding="utf-8")
    validate_clarify_gate(root, [draft_note])
    validate_clarify_gate(root, [draft_note], strict=True)

    draft_note.write_text("---\nstatus: superseded\nowner: eng\n---\n# Orphan Superseded\n", encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [draft_note], strict=False), "superseded without superseded_by (non-strict)", "superseded_by")
    expect_fail(lambda: validate_clarify_gate(root, [draft_note], strict=True), "superseded without superseded_by (strict)", "superseded_by")

    for valid_sup_target in ('"Target Note.md"', '"[[Target Note]]"', '"[[docs/current/Target Note#Sec|Alias]]"'):
        draft_note.write_text(
            f"---\nstatus: superseded\nsuperseded_by: {valid_sup_target}\ntags: [moc, docs]\nsource_paths: [AGENTS.md]\n---\n# Replaced\n",
            encoding="utf-8",
        )
        validate_clarify_gate(root, [draft_note], strict=True)

    draft_note.write_text("---\nstatus: approve\nowner: eng\n---\n# Typo\n", encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [draft_note]), "status typo approve", "status")
    draft_note.unlink()

    # 3. Standard 4-file & 1-file Mini-Spec packs
    overview = current / "Overview.md"
    overview.write_text("---\nstatus: approved\nowner: architecture\n---\n# Overview\n", encoding="utf-8")
    validate_clarify_gate(root, [overview])

    feat_ok = features / "001-auth"
    write_valid_pack(feat_ok, fm=APPROVED_FM, five_col_qa=False, with_tasks=True)
    write_valid_pack(features / "002-five-col", fm=APPROVED_FM, five_col_qa=True, with_tasks=True)
    mini_ok = features / "005-mini-auth"
    write_mini_spec(mini_ok, fm=APPROVED_FM)
    mini_draft = features / "006-mini-draft"
    write_mini_spec(mini_draft, fm=DRAFT_FM)

    all_files = sorted(current.rglob("*.md"))
    validate_clarify_gate(root, all_files)
    assert validate_feature_specs(root, features, require_tasks=True) == []

    # Duplicate NNN- prefix rejection
    dup_feat = features / "001-duplicate"
    write_mini_spec(dup_feat, fm=DRAFT_FM)
    expect_fail(lambda: validate_feature_specs(root, features), "duplicate 001- prefix", "001")
    shutil.rmtree(dup_feat)

    # Mini-Spec negative cases: missing AC-02, 0% aggregate coverage with '-', and mixed 1. Mini Spec.md + 1. Product Spec.md
    bad_mini = features / "007-bad-mini"
    write_mini_spec(
        bad_mini,
        fm=APPROVED_FM,
        rows="| T-01 | todo | no | - | AC-01 | `src/a.py` | Only AC-01 | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_mini), "mini-spec missing AC-02", "AC-02")

    write_mini_spec(
        bad_mini,
        fm=APPROVED_FM,
        rows="| T-01 | todo | no | - | - | `src/a.py` | Chore only, 0% AC | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_mini), "mini-spec 0% AC with '-'", "AC-01")

    write_valid_pack(bad_mini, fm=DRAFT_FM)
    expect_fail(lambda: validate_feature_folder(root, bad_mini), "mixed Mini Spec + Product Spec", "Mini Spec")
    shutil.rmtree(bad_mini)

    # 4. Clarify, readiness checkbox, placeholder provenance, short/zero source_revision
    bad_clarify = features / "003-bad"
    write_valid_pack(bad_clarify)
    (bad_clarify / "1. Product Spec.md").write_text(
        (bad_clarify / "1. Product Spec.md").read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: leak]\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Product Spec.md"]), "clarify in approved")

    write_valid_pack(bad_clarify)
    (bad_clarify / "4. Tasks.md").write_text(
        (bad_clarify / "4. Tasks.md").read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "4. Tasks.md"]), "unchecked readiness box")

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

    # All-zero 40-hex fails; short 7-hex warns when strict=False and fails when strict=True
    write_mini_spec(bad_clarify, fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "0" * 40))
    expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"]), "all-zero source_revision", "source_revision")

    write_mini_spec(bad_clarify, fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "b8b8355"))
    short_warns = validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"], strict=False)
    assert any("b8b8355" in w for w in short_warns), f"expected short-SHA warning, got {short_warns}"
    expect_fail(
        lambda: validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"], strict=True),
        "short SHA under --strict",
        "40-char",
    )
    shutil.rmtree(bad_clarify)

    # 5. Legacy 3-file warning vs --require-tasks, invalid Status, cycle, glob, and [P] overlap
    legacy_3 = features / "004-legacy"
    write_valid_pack(legacy_3, fm=APPROVED_FM, with_tasks=False)
    warns = validate_feature_folder(root, legacy_3, require_tasks=False)
    assert len(warns) == 1 and "4. Tasks.md" in warns[0], f"expected legacy 3-file warning, got {warns}"
    expect_fail(lambda: validate_feature_folder(root, legacy_3, require_tasks=True), "legacy 3-file with --require-tasks", "4. Tasks.md")
    shutil.rmtree(legacy_3)

    bad_tasks = features / "008-bad-tasks"
    write_valid_pack(
        bad_tasks,
        fm=DRAFT_FM,
        tasks_rows="| T-01 |bogus| no | - | AC-01 | `src/a` | Bad status | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_tasks), "invalid task Status", "status")

    write_valid_pack(
        bad_tasks,
        fm=DRAFT_FM,
        tasks_rows=(
            "| T-01 | todo | no | T-02 | AC-01 | `src/a` | A | `pytest` |\n"
            "| T-02 | todo | no | T-01 | AC-02 | `src/b` | B | `pytest` |\n"
        ),
    )
    expect_fail(lambda: validate_feature_folder(root, bad_tasks), "task dependency cycle", "cycle")

    write_valid_pack(
        bad_tasks,
        fm=DRAFT_FM,
        tasks_rows="| T-01 | todo | no | - | AC-01 | `src/*` | Glob | `pytest` |\n",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_tasks), "glob in Owned paths", "glob")

    write_valid_pack(
        bad_tasks,
        fm=DRAFT_FM,
        tasks_rows=(
            "| T-01 | todo | yes | - | AC-01 | `src/api/` | Parent | `pytest` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/other, src/api/users.py` | Child | `pytest` |\n"
        ),
    )
    expect_fail(lambda: validate_feature_folder(root, bad_tasks), "overlapping [P] Owned paths", "overlap")
    shutil.rmtree(bad_tasks)

    # 5b. v0.6.1 superseded_by, supersedes, governance YAML, triage schema/secret guard, and export-tasks refusal
    # Positive: Mini-Spec -> 4-file pack -> 4-file pack (2-hop chain A -> B -> C where C is approved)
    sup_mini_fm = APPROVED_FM.replace(
        "status: approved\n",
        'status: superseded\nsuperseded_by: "05 - Product Features/009-auth-full/1. Product Spec.md"\n',
    )
    sup_mid_fm = APPROVED_FM.replace(
        "status: approved\n",
        'status: superseded\nsupersedes: "05 - Product Features/005-mini-auth"\n'
        'superseded_by: "05 - Product Features/010-auth-next/1. Product Spec.md"\n',
    )
    sup_final_fm = APPROVED_FM.replace(
        "status: approved\n",
        'status: approved\nsupersedes: "05 - Product Features/009-auth-full"\n',
    )
    write_mini_spec(mini_ok, fm=sup_mini_fm)
    feat_mid = features / "009-auth-full"
    feat_final = features / "010-auth-next"
    write_valid_pack(feat_mid, fm=sup_mid_fm)
    write_valid_pack(feat_final, fm=sup_final_fm)
    validate_clarify_gate(root, sorted(current.rglob("*.md")), strict=True)
    assert validate_feature_specs(root, features, require_tasks=True, strict=True) == []

    # export-tasks.py unconditionally refuses status: superseded (printing superseded_by) and status: archived even with --allow-draft
    tools = root / "tools"
    tools.mkdir()
    for tool_name in ("docs_validation.py", "validate-docs.py", "export-tasks.py"):
        (tools / tool_name).write_text((tools_src_dir / tool_name).read_text(encoding="utf-8"), encoding="utf-8")
    export_script = tools / "export-tasks.py"
    res_exp_sup = subprocess.run(
        [sys.executable, "-B", str(export_script), str(mini_ok), "--allow-draft"],
        capture_output=True,
        text=True,
    )
    assert res_exp_sup.returncode != 0 and "009-auth-full" in res_exp_sup.stderr, (
        f"expected superseded export refusal with superseded_by hint, got: {res_exp_sup.stderr}"
    )
    arch_mini = features / "011-arch-mini"
    write_mini_spec(arch_mini, fm=APPROVED_FM.replace("status: approved\n", "status: archived\n"))
    res_exp_arch = subprocess.run(
        [sys.executable, "-B", str(export_script), str(arch_mini), "--allow-draft"],
        capture_output=True,
        text=True,
    )
    assert res_exp_arch.returncode != 0 and "archived" in res_exp_arch.stderr.lower(), (
        f"expected archived export refusal, got: {res_exp_arch.stderr}"
    )
    shutil.rmtree(arch_mini)

    # Negative governance YAML, superseded_by, and supersedes cases
    gov_bad = current / "gov-bad.md"
    for bad_fm_body, label, substr in (
        ("status: superseded\nsuperseded_by: [[Target Note]]\n", "unquoted [[...]] superseded_by", "quoted"),
        ("status: [approved]\n", "unquoted [...] status", "quoted"),
        ('status: superseded\nsuperseded_by: "Target Note.md"\nsuperseded_by: "Overview.md"\n', "duplicate superseded_by", "duplicate"),
        ('status: superseded\nsuperseded_by: "Target Note.md\n', "unclosed quote", "quote"),
        ('status: superseded\nsuperseded_by: "Target\\Note.md"\n', "raw backslash in quote", "\\"),
        ("status: |\n  superseded\n", "block-scalar status spoofing", "plain or quoted scalar"),
        ("status: superseded\nsuperseded_by: # comment-only\n", "comment-only superseded_by", "superseded_by"),
        ('status: superseded\nsuperseded_by: "tbd"\n', "placeholder tbd", "placeholder"),
        ('status: superseded\nsuperseded_by: "none"\n', "placeholder none", "placeholder"),
        ('status: superseded\nsuperseded_by: "-"\n', "placeholder dash", "placeholder"),
        ('status: superseded\nsuperseded_by: "../outside.md"\n', "parent traversal", ".."),
        ('status: superseded\nsuperseded_by: "%2e%2e/outside.md"\n', "percent-encoded traversal", "%"),
        ('status: superseded\nsuperseded_by: "gov-bad.md"\n', "self-reference", "itself"),
    ):
        gov_bad.write_text(f"---\n{bad_fm_body}---\n# Bad\n", encoding="utf-8")
        expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), label, substr)

    # Unquoted supersedes and comment-only approved_by on feature spec
    bad_sup_pack = features / "012-bad-sup"
    write_mini_spec(
        bad_sup_pack,
        fm=APPROVED_FM.replace("approved_by: lead-eng", "approved_by: # waiting for review"),
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_sup_pack / "1. Mini Spec.md"], strict=True), "comment-only approved_by", "approved_by")
    write_mini_spec(
        bad_sup_pack,
        fm=DRAFT_FM.replace("status: draft\n", "status: draft\nsupersedes: [[005-mini-auth]]\n"),
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_sup_pack / "1. Mini Spec.md"], strict=True), "unquoted supersedes", "quoted")
    shutil.rmtree(bad_sup_pack)

    # README.md inside 05 - Product Features forbidden as superseded_by target
    (features / "README.md").write_text("---\nstatus: active\nowner: eng\n---\n# Features\n", encoding="utf-8")
    gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "05 - Product Features/README.md"\n---\n# Bad\n', encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "05 - Product Features/README.md target", "spec file")
    (features / "README.md").unlink()

    # Intra-repo symlink target refused lexically before resolve()
    sym_target = current / "Sym Target.md"
    sym_target.symlink_to(current / "Target Note.md")
    gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "Sym Target.md"\n---\n# Bad\n', encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "intra-repo symlink target", "symlink")
    sym_target.unlink()

    # Cycle (A -> B -> A) and dead archived terminal target
    cycle_b = current / "cycle-b.md"
    gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "cycle-b.md"\n---\n# A\n', encoding="utf-8")
    cycle_b.write_text('---\nstatus: superseded\nsuperseded_by: "gov-bad.md"\n---\n# B\n', encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [gov_bad, cycle_b], strict=True), "superseded_by cycle", "cycle")
    cycle_b.write_text("---\nstatus: archived\nowner: eng\n---\n# Dead\n", encoding="utf-8")
    expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "archived terminal target", "archived")
    cycle_b.unlink()
    gov_bad.unlink()

    # Intra-pack target, divergent 4-file superseded_by / supersedes, formerly approved -> draft under --strict, and approved supersedes -> still-approved old pack under --strict
    bad_pack_sup = features / "013-bad-pack"
    write_valid_pack(
        bad_pack_sup,
        fm=APPROVED_FM.replace(
            "status: approved\n",
            'status: superseded\nsuperseded_by: "05 - Product Features/013-bad-pack/2. Tech Spec.md"\n',
        ),
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Product Spec.md"], strict=True), "intra-pack target", "same feature folder")

    write_valid_pack(
        bad_pack_sup,
        fm=APPROVED_FM.replace(
            "status: approved\n",
            'status: superseded\nsuperseded_by: "05 - Product Features/010-auth-next/1. Product Spec.md"\n',
        ),
    )
    (bad_pack_sup / "2. Tech Spec.md").write_text(
        (bad_pack_sup / "2. Tech Spec.md")
        .read_text(encoding="utf-8")
        .replace("010-auth-next", "001-auth"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_pack_sup, strict=True), "divergent 4-file superseded_by", "same replacement")

    write_valid_pack(
        bad_pack_sup,
        fm=DRAFT_FM.replace(
            "status: draft\n",
            'status: draft\nsupersedes: "05 - Product Features/001-auth"\n',
        ),
    )
    (bad_pack_sup / "3. QA Spec.md").write_text(
        (bad_pack_sup / "3. QA Spec.md")
        .read_text(encoding="utf-8")
        .replace("001-auth", "002-five-col"),
        encoding="utf-8",
    )
    expect_fail(lambda: validate_feature_folder(root, bad_pack_sup, strict=True), "divergent 4-file supersedes", "divergent 'supersedes'")

    # Formerly approved spec superseded by draft fails under --strict
    write_mini_spec(
        bad_pack_sup,
        fm=APPROVED_FM.replace(
            "status: approved\n",
            'status: superseded\nsuperseded_by: "05 - Product Features/006-mini-draft/1. Mini Spec.md"\n',
        ),
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Mini Spec.md"], strict=True), "formerly approved -> draft under --strict", "approved")

    # Approved replacement pack with supersedes pointing to still-approved 001-auth fails under --strict
    write_mini_spec(
        bad_pack_sup,
        fm=APPROVED_FM.replace(
            "status: approved\n",
            'status: approved\nsupersedes: "05 - Product Features/001-auth"\n',
        ),
    )
    expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Mini Spec.md"], strict=True), "approved supersedes still-approved old pack", "superseded")
    shutil.rmtree(bad_pack_sup)
    shutil.rmtree(feat_mid)
    shutil.rmtree(feat_final)
    write_mini_spec(mini_ok, fm=APPROVED_FM)

    # Triage table & secret-guard tests (both Evidence and Evidence (`file:line`), blank starter cell, status enum, duplicate ID, leaked secrets)
    arch_note = current / "Architecture.md"
    for ev_hdr in ("Evidence (`file:line`)", "Evidence"):
        arch_note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Arch\n\n"
            "## Brownfield security and tech-debt triage\n\n"
            f"| ID | Category | Severity | {ev_hdr} | Risk / debt summary | Remediation route | Target spec or evidence | Status |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| SEC-01 | auth | high |  | Starter blank evidence row | Tier S (`/sdd-fix`) |  | Open |\n"
            "| SEC-02 | secrets | medium | `src/cfg.py:12` | Redacted env check (`postgres://user:pass@localhost/db`) | Spec Amendment | `05 - Product Features/001-auth` | In Progress |\n"
            "| SEC-03 | deps | low | `package.json:4` | Pinned dep | `/sdd-fix` | `task-evidence/fix.md` | Mitigated |\n"
            "| SEC-04 | debt | low | `src/old.py:1` | Deferred | Accepted | - | Accepted Risk |\n",
            encoding="utf-8",
        )
        validate_clarify_gate(root, [arch_note], strict=True)

    # Missing column
    arch_note.write_text(
        "---\nstatus: active\nowner: eng\n---\n# Arch\n\n"
        "## Brownfield security and tech-debt triage\n\n"
        "| ID | Category | Severity | Risk / debt summary | Status |\n"
        "|---|---|---|---|---|\n"
        "| SEC-01 | auth | high | Missing cols | Open |\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "triage missing columns", "missing required column")

    # Duplicate SEC-01
    arch_note.write_text(
        "---\nstatus: active\nowner: eng\n---\n# Arch\n\n"
        "## Brownfield security and tech-debt triage\n\n"
        "| ID | Category | Severity | Evidence | Risk / debt summary | Remediation route | Target spec or evidence | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| SEC-01 | auth | high | `a.py:1` | One | `/sdd-fix` | - | Open |\n"
        "| SEC-01 | auth | low | `b.py:2` | Dup | `/sdd-fix` | - | Open |\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "duplicate SEC-01", "duplicate triage ID")

    # Invalid Status
    arch_note.write_text(
        "---\nstatus: active\nowner: eng\n---\n# Arch\n\n"
        "## Brownfield security and tech-debt triage\n\n"
        "| ID | Category | Severity | Evidence | Risk / debt summary | Remediation route | Target spec or evidence | Status |\n"
        "|---|---|---|---|---|---|---|---|\n"
        "| SEC-01 | auth | high | `a.py:1` | Bad status | `/sdd-fix` | - | Resolved |\n",
        encoding="utf-8",
    )
    expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "invalid triage Status", "invalid Status")

    # Secret leak detector (constructed dynamically so test script never embeds literal secret tokens)
    fake_aws = "AKIA" + "IOSFODNN7EXAMPLE"
    fake_ghp = "ghp_" + ("A1b2C3d4E5f6" * 3)
    fake_fgpat = "github_pat_" + ("11AABBCCDD" * 3)
    fake_pem = "-----BEGIN " + "PRIVATE KEY-----"
    for leaked_tok, tok_label in (
        (fake_aws, "AWS key leak"),
        (fake_ghp, "GitHub PAT leak"),
        (fake_fgpat, "GitHub fine-grained PAT leak"),
        (fake_pem, "PEM private key leak"),
    ):
        arch_note.write_text(
            f"---\nstatus: active\nowner: eng\n---\n# Arch\n\nLeaked: {leaked_tok}\n",
            encoding="utf-8",
        )
        expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), tok_label, "secret")
    arch_note.unlink()

    # CLI check for tools/validate-docs.py --require-tasks
    subprocess.run([sys.executable, "-B", str(tools / "validate-docs.py"), "--require-tasks"], check=True, stdout=subprocess.DEVNULL)

# 6. Git-backed earliest-approved-commit tampering check + validate-task-evidence.py security unit tests
with tempfile.TemporaryDirectory() as git_tmp:
    groot = Path(git_tmp).resolve()
    gfeatures = groot / "docs/current/05 - Product Features"
    gfeatures.mkdir(parents=True)
    subprocess.run(["git", "-C", str(groot), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(groot), "config", "user.email", "test@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(groot), "config", "user.name", "Test"], check=True)

    gmini = gfeatures / "001-git-mini"
    write_mini_spec(gmini, fm=DRAFT_FM)
    (groot / "artifact.txt").write_text("v1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(groot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(groot), "commit", "-qm", "draft commit"], check=True)
    draft_sha = subprocess.check_output(["git", "-C", str(groot), "rev-parse", "HEAD"], text=True).strip()

    # Newly approved spec stamped against draft HEAD passes BEFORE committing the approval!
    stamped_fm = APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", draft_sha)
    write_mini_spec(gmini, fm=stamped_fm)
    validate_clarify_gate(groot, [gmini / "1. Mini Spec.md"], strict=True)
    assert validate_feature_folder(groot, gmini, require_tasks=True, strict=True) == []

    # Commit the approved spec
    subprocess.run(["git", "-C", str(groot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(groot), "commit", "-qm", "approve mini spec"], check=True)
    approved_sha = subprocess.check_output(["git", "-C", str(groot), "rev-parse", "HEAD"], text=True).strip()

    # Converging task Status todo -> done preserves source_revision and passes!
    mini_path = gmini / "1. Mini Spec.md"
    converged_text = mini_path.read_text(encoding="utf-8").replace("| todo |", "| done |")
    mini_path.write_text(converged_text, encoding="utf-8")
    assert validate_feature_folder(groot, gmini, require_tasks=True, strict=True) == []

    # Tampering with Acceptance criteria or Owned paths after approval WITHOUT refreshing source_revision fails!
    mini_path.write_text(converged_text.replace("src/login.py", "src/hacked.py"), encoding="utf-8")
    expect_fail(
        lambda: validate_feature_folder(groot, gmini, require_tasks=True, strict=True),
        "post-approval Owned paths tampering",
        "Owned paths",
    )
    mini_path.write_text(converged_text.replace("200 OK", "201 Created"), encoding="utf-8")
    expect_fail(
        lambda: validate_feature_folder(groot, gmini, require_tasks=True, strict=True),
        "post-approval AC tampering",
        "Acceptance criteria",
    )
    mini_path.write_text(converged_text, encoding="utf-8")

    # Historical AC tampering on a status: superseded spec in Git repo fails!
    gfull = gfeatures / "002-git-full"
    gfull_fm = stamped_fm.replace(
        "status: approved\n",
        'status: approved\nsupersedes: "05 - Product Features/001-git-mini"\n',
    )
    write_valid_pack(gfull, fm=gfull_fm)
    superseded_mini_text = converged_text.replace(
        "status: approved\n",
        'status: superseded\nsuperseded_by: "05 - Product Features/002-git-full/1. Product Spec.md"\n',
    )
    mini_path.write_text(superseded_mini_text, encoding="utf-8")
    validate_clarify_gate(groot, [mini_path, *sorted(gfull.glob("*.md"))], strict=True)
    mini_path.write_text(superseded_mini_text.replace("200 OK", "201 Tampered"), encoding="utf-8")
    expect_fail(
        lambda: validate_clarify_gate(groot, [mini_path], strict=True),
        "tampered historical AC on superseded spec",
        "Acceptance criteria",
    )
    mini_path.write_text(converged_text, encoding="utf-8")
    shutil.rmtree(gfull)

    # validate-task-evidence.py: \r\n + quoted status, --allow-working-tree draft-only, symlinks, scoped corrections
    gtools = groot / "tools"
    gtools.mkdir()
    ev_validator = gtools / "validate-task-evidence.py"
    ev_validator.write_text((tools_src_dir / "validate-task-evidence.py").read_text(encoding="utf-8"), encoding="utf-8")
    ev_dir = groot / "task-evidence"
    ev_dir.mkdir()
    art_sha = hashlib.sha256((groot / "artifact.txt").read_bytes()).hexdigest()

    # Draft evidence with --allow-working-tree passes; fails with --require-completed
    draft_ev = ev_dir / "01-draft.md"
    draft_ev.write_text(
        "---\r\n"
        'status: "draft"\r\n'
        "task_id: t-draft\r\n"
        "recorded_at: 2026-11-13\r\n"
        "recorded_by: tester\r\n"
        "source_revision: working-tree\r\n"
        "environment: local/dev\r\n"
        f"output_artifact_sha256: {art_sha}\r\n"
        "output_artifact_path: artifact.txt\r\n"
        "---\r\n"
        "# Draft Evidence\r\n\r\n"
        "| AC-01 | Check | cmd | Pass / 0 |\r\n",
        encoding="utf-8",
    )
    subprocess.run([sys.executable, "-B", str(ev_validator), "--allow-working-tree"], check=True, stdout=subprocess.DEVNULL)
    res_combo = subprocess.run(
        [sys.executable, "-B", str(ev_validator), "--allow-working-tree", "--require-completed"],
        capture_output=True,
        text=True,
    )
    assert res_combo.returncode != 0, "expected --allow-working-tree --require-completed to fail"
    draft_ev.unlink()

    # Completed evidence with \r\n and quoted status: "completed" passes
    comp_ev = ev_dir / "02-completed.md"
    comp_ev.write_bytes(
        (
            "---\r\n"
            'status: "completed"\r\n'
            "task_id: t-comp\r\n"
            "recorded_at: 2026-11-13\r\n"
            "recorded_by: tester\r\n"
            f"source_revision: {approved_sha}\r\n"
            "completed_at: 2026-11-13\r\n"
            "reviewer: lead\r\n"
            "environment: local/dev\r\n"
            f"output_artifact_sha256: {art_sha}\r\n"
            "output_artifact_path: artifact.txt\r\n"
            "---\r\n"
            "# Completed Evidence\r\n\r\n"
            "| AC-01 | Check | cmd | Pass / 0 |\r\n"
        ).encode("utf-8")
    )
    subprocess.run([sys.executable, "-B", str(ev_validator), "--require-completed"], check=True, stdout=subprocess.DEVNULL)

    # Completed evidence with source_revision: working-tree fails even with --allow-working-tree
    bad_wt = ev_dir / "03-bad-wt.md"
    bad_wt.write_text(
        comp_ev.read_text(encoding="utf-8").replace(approved_sha, "working-tree"),
        encoding="utf-8",
    )
    res_wt = subprocess.run([sys.executable, "-B", str(ev_validator), "--allow-working-tree"], capture_output=True, text=True)
    assert res_wt.returncode != 0, "completed evidence must reject working-tree even with --allow-working-tree"
    bad_wt.unlink()

    # Scoped evidence-corrections.json ignored in downstream task-evidence/
    bogus_rev = "1" * 40
    comp_ev.write_text(comp_ev.read_text(encoding="utf-8").replace(approved_sha, bogus_rev), encoding="utf-8")
    (ev_dir / "evidence-corrections.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "corrections": {
                    "task-evidence/02-completed.md": {
                        "source_revision": approved_sha,
                        "reason": "spoof attempt in downstream dir",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    res_spoof = subprocess.run([sys.executable, "-B", str(ev_validator), "--require-completed"], capture_output=True, text=True)
    assert res_spoof.returncode != 0, "downstream evidence-corrections.json must be ignored"
    (ev_dir / "evidence-corrections.json").unlink()
    comp_ev.write_text(comp_ev.read_text(encoding="utf-8").replace(bogus_rev, approved_sha), encoding="utf-8")

    # Symlinked evidence file rejected
    outside_ev = Path(git_tmp) / "outside.md"
    outside_ev.write_text(comp_ev.read_text(encoding="utf-8"), encoding="utf-8")
    sym_ev = ev_dir / "99-symlink.md"
    sym_ev.symlink_to(outside_ev)
    res_sym = subprocess.run([sys.executable, "-B", str(ev_validator)], capture_output=True, text=True)
    assert res_sym.returncode != 0, "symlinked evidence file must fail"

# 7. v0.7.0 stamp-spec.py, validate-docs.py --check-owned-paths, and record-evidence.py fixtures
from docs_validation import parse_frontmatter  # noqa: E402

with tempfile.TemporaryDirectory() as v7_tmp:
    v7_base = Path(v7_tmp).resolve()

    def init_repo(path: Path) -> Path:
        path.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "-C", str(path), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(path), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.email", "v7@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(path), "config", "user.name", "V7 Test"], check=True)
        tdir = path / "tools"
        tdir.mkdir()
        for tname in (
            "docs_validation.py",
            "validate-docs.py",
            "stamp-spec.py",
            "validate-task-evidence.py",
            "record-evidence.py",
        ):
            (tdir / tname).write_text((tools_src_dir / tname).read_text(encoding="utf-8"), encoding="utf-8")
        return path

    # 7A. stamp-spec.py: draft->approved, non-amend refusal, --amend with PR #42, atomic supersedes, wikilink preserve, archived/hijacked refusal, staged --dry-run, and rollback
    sroot = init_repo(v7_base / "stamp-repo")
    sfeatures = sroot / "docs/current/05 - Product Features"
    sfeatures.mkdir(parents=True)
    smini = sfeatures / "001-stamp-mini"
    write_mini_spec(smini, fm=DRAFT_FM)
    subprocess.run(["git", "-C", str(sroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "draft mini"], check=True)
    s_draft_sha = subprocess.check_output(["git", "-C", str(sroot), "rev-parse", "HEAD"], text=True).strip()

    stamp_bin = sroot / "tools/stamp-spec.py"
    vdocs_bin = sroot / "tools/validate-docs.py"

    # Source-template protection (must fail without --dry-run on repo_root)
    res_src_guard = subprocess.run(
        [sys.executable, "-B", str(repo_root / "tools/stamp-spec.py"), "001-x", "--by", "a", "--evidence", "b", "--root", str(repo_root)],
        capture_output=True,
        text=True,
    )
    assert res_src_guard.returncode != 0 and "source ai-project-template" in res_src_guard.stderr, res_src_guard.stderr

    # Initial draft -> approved
    subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "001-stamp-mini", "--by", "lead eng", "--evidence", "PR #42", "--at", "2026-11-18", "--root", str(sroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    smini_raw = (smini / "1. Mini Spec.md").read_text(encoding="utf-8")
    assert 'approval_evidence: "PR #42"' in smini_raw, smini_raw
    smini_fm = parse_frontmatter(smini_raw)
    assert smini_fm["status"] == "approved"
    assert smini_fm["approved_by"] == "lead eng"
    assert smini_fm["approved_at"] == "2026-11-18"
    assert smini_fm["approval_evidence"] == "PR #42"
    assert smini_fm["source_revision"] == s_draft_sha
    subprocess.run([sys.executable, "-B", str(vdocs_bin), "--require-tasks", "--strict", "--root", str(sroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(sroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "approve mini"], check=True)

    # Refusal on already-approved without --amend
    res_no_amend = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "001-stamp-mini", "--by", "lead eng", "--evidence", "PR #43", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_no_amend.returncode != 0 and "--amend" in res_no_amend.stderr, res_no_amend.stderr

    # --amend updating source_revision + approved_at with quoted "PR #42"
    (sroot / "README.md").write_text("amend target\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(sroot), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "advance head"], check=True)
    s_adv_sha = subprocess.check_output(["git", "-C", str(sroot), "rev-parse", "HEAD"], text=True).strip()
    (smini / "1. Mini Spec.md").write_text(
        (smini / "1. Mini Spec.md").read_text(encoding="utf-8").replace("200 OK", "200 JSON"),
        encoding="utf-8",
    )
    subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "001-stamp-mini", "--by", "lead eng", "--evidence", "PR #42", "--at", "2026-11-19", "--amend", "--root", str(sroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    amended_fm = parse_frontmatter((smini / "1. Mini Spec.md").read_text(encoding="utf-8"))
    assert amended_fm["source_revision"] == s_adv_sha
    assert amended_fm["approved_at"] == "2026-11-19"
    assert amended_fm["approval_evidence"] == "PR #42"
    subprocess.run([sys.executable, "-B", str(vdocs_bin), "--require-tasks", "--strict", "--root", str(sroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(sroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "commit amended mini"], check=True)

    # Staged --dry-run failing on unresolved Clarify tag without touching disk, + transactional rollback restoring exact bytes
    sclar = sfeatures / "002-clarify-fail"
    write_mini_spec(sclar, fm=DRAFT_FM)
    clar_path = sclar / "1. Mini Spec.md"
    clar_path.write_text(clar_path.read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: missing timeout]\n", encoding="utf-8")
    orig_clar_bytes = clar_path.read_bytes()
    res_dry_clar = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "002-clarify-fail", "--by", "lead", "--evidence", "PR #44", "--dry-run", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_dry_clar.returncode != 0 and "NEEDS CLARIFICATION" in res_dry_clar.stderr, res_dry_clar.stderr
    assert clar_path.read_bytes() == orig_clar_bytes, "--dry-run mutated disk on failure"

    res_real_clar = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "002-clarify-fail", "--by", "lead", "--evidence", "PR #44", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_real_clar.returncode != 0 and "NEEDS CLARIFICATION" in res_real_clar.stderr, res_real_clar.stderr
    assert clar_path.read_bytes() == orig_clar_bytes, "rollback failed to restore exact bytes"
    shutil.rmtree(sclar)

    # Multi-file supersession rollback check
    srb = sfeatures / "003-rb-full"
    write_valid_pack(srb, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'))
    (srb / "4. Tasks.md").write_text((srb / "4. Tasks.md").read_text(encoding="utf-8").replace("- [x]", "- [ ]"), encoding="utf-8")
    orig_mini_bytes = (smini / "1. Mini Spec.md").read_bytes()
    orig_rb_bytes = {name: (srb / name).read_bytes() for name in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md")}
    res_rb = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "003-rb-full", "--by", "lead", "--evidence", "PR #45", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_rb.returncode != 0, "expected rollback failure on unchecked checkbox"
    assert (smini / "1. Mini Spec.md").read_bytes() == orig_mini_bytes, "supersession rollback altered old spec"
    for name, b_orig in orig_rb_bytes.items():
        assert (srb / name).read_bytes() == b_orig, f"rollback failed on {name}"
    shutil.rmtree(srb)

    # Atomic supersedes retirement preserving historical approval fields & wikilink preservation on --amend
    sfull = sfeatures / "004-stamp-full"
    write_valid_pack(sfull, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'))
    subprocess.run(["git", "-C", str(sroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "draft 004 pack"], check=True)
    s_draft4_sha = subprocess.check_output(["git", "-C", str(sroot), "rev-parse", "HEAD"], text=True).strip()

    subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "004-stamp-full", "--by", "arch", "--evidence", "PR #50", "--at", "2026-11-19", "--root", str(sroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for name in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
        fm4 = parse_frontmatter((sfull / name).read_text(encoding="utf-8"))
        assert fm4["status"] == "approved" and fm4["source_revision"] == s_draft4_sha
    old_fm = parse_frontmatter((smini / "1. Mini Spec.md").read_text(encoding="utf-8"))
    assert old_fm["status"] == "superseded"
    assert old_fm["superseded_by"] == "05 - Product Features/004-stamp-full/1. Product Spec.md"
    assert old_fm["approved_by"] == "lead eng"
    assert old_fm["approved_at"] == "2026-11-19"
    assert old_fm["approval_evidence"] == "PR #42"
    assert old_fm["source_revision"] == s_adv_sha

    # Preserve existing wikilink superseded_by format during --amend
    (smini / "1. Mini Spec.md").write_text(
        (smini / "1. Mini Spec.md").read_text(encoding="utf-8").replace(
            '"05 - Product Features/004-stamp-full/1. Product Spec.md"',
            '"[[05 - Product Features/004-stamp-full/1. Product Spec]]"',
        ),
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(sroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(sroot), "commit", "-qm", "commit 004 approved and wikilink"], check=True)
    subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "004-stamp-full", "--by", "arch", "--evidence", "PR #51", "--at", "2026-11-20", "--amend", "--root", str(sroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    assert '"[[05 - Product Features/004-stamp-full/1. Product Spec]]"' in (smini / "1. Mini Spec.md").read_text(encoding="utf-8")

    # Refuse archived & already-superseded (hijacked) targets
    sarch = sfeatures / "005-arch"
    write_mini_spec(sarch, fm="---\nstatus: archived\nowner: eng\n---\n")
    sfrom_arch = sfeatures / "006-from-arch"
    write_mini_spec(sfrom_arch, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/005-arch"\n'))
    res_arch = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "006-from-arch", "--by", "arch", "--evidence", "PR #52", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_arch.returncode != 0 and "archived" in res_arch.stderr.lower(), res_arch.stderr
    shutil.rmtree(sarch)
    shutil.rmtree(sfrom_arch)

    shijack = sfeatures / "007-hijack"
    write_mini_spec(shijack, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'))
    res_hijack = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "007-hijack", "--by", "arch", "--evidence", "PR #53", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_hijack.returncode != 0 and "already superseded" in res_hijack.stderr.lower(), res_hijack.stderr
    shutil.rmtree(shijack)

    # Warning #4 regression: stamp-spec.py --dry-run resolves valid relative links from docs/current/ to root files outside docs/
    (sroot / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
    dry_guide = sroot / "docs/current/guide.md"
    dry_guide.write_text("---\nstatus: active\nowner: eng\n---\n# Guide\n\nSee [AGENTS.md](../../AGENTS.md).\n", encoding="utf-8")
    sdry_links = sfeatures / "008-dry-links"
    write_mini_spec(sdry_links, fm=DRAFT_FM)
    res_dry_links = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "008-dry-links", "--by", "lead", "--evidence", "PR #54", "--dry-run", "--root", str(sroot)],
        capture_output=True,
        text=True,
    )
    assert res_dry_links.returncode == 0 and "DRY-RUN:" in res_dry_links.stdout, res_dry_links.stderr
    assert parse_frontmatter((sdry_links / "1. Mini Spec.md").read_text(encoding="utf-8"))["status"] == "draft"
    shutil.rmtree(sdry_links)
    dry_guide.unlink()
    (sroot / "AGENTS.md").unlink()

    # Monorepo-subdir (root != git_top) --dry-run check for stamp-spec.py
    mono_git = v7_base / "mono-repo"
    mono_git.mkdir(parents=True)
    subprocess.run(["git", "-C", str(mono_git), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(mono_git), "symbolic-ref", "HEAD", "refs/heads/main"], check=True)
    subprocess.run(["git", "-C", str(mono_git), "config", "user.email", "v7@example.invalid"], check=True)
    subprocess.run(["git", "-C", str(mono_git), "config", "user.name", "V7 Test"], check=True)
    mono_sub = mono_git / "packages/app-a"
    mono_mini = mono_sub / "docs/current/05 - Product Features/001-mono-mini"
    write_mini_spec(mono_mini, fm=DRAFT_FM)
    (mono_sub / "README.md").write_text("subproject root\n", encoding="utf-8")
    (mono_sub / "docs/current/guide.md").write_text(
        "---\nstatus: active\nowner: eng\n---\n# Guide\n\nSee [README](../../README.md).\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "-C", str(mono_git), "add", "."], check=True)
    subprocess.run(["git", "-C", str(mono_git), "commit", "-qm", "init monorepo subdir"], check=True)
    mono_sha = subprocess.check_output(["git", "-C", str(mono_git), "rev-parse", "HEAD"], text=True).strip()
    res_mono_dry = subprocess.run(
        [sys.executable, "-B", str(stamp_bin), "001-mono-mini", "--by", "lead", "--evidence", "PR #77", "--dry-run", "--root", str(mono_sub)],
        capture_output=True,
        text=True,
    )
    assert res_mono_dry.returncode == 0 and "DRY-RUN:" in res_mono_dry.stdout and mono_sha in res_mono_dry.stdout, res_mono_dry.stderr
    assert parse_frontmatter((mono_mini / "1. Mini Spec.md").read_text(encoding="utf-8"))["status"] == "draft"

    # 7B. validate-docs.py --check-owned-paths fixture tests
    oroot = init_repo(v7_base / "owned-repo")
    ovdocs = oroot / "tools/validate-docs.py"
    ostamp = oroot / "tools/stamp-spec.py"
    ofeatures = oroot / "docs/current/05 - Product Features"
    ofeatures.mkdir(parents=True)
    (oroot / "docs/current/02 - Architecture").mkdir(parents=True)
    (oroot / "docs/current/02 - Architecture/Architecture.md").write_text("---\nstatus: active\nowner: eng\n---\n# Arch\n", encoding="utf-8")
    (oroot / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
    (oroot / "src").mkdir()
    (oroot / "src/unowned.py").write_text("x = 1\n", encoding="utf-8")
    (oroot / "other.txt").write_text("main\n", encoding="utf-8")

    ofeat = ofeatures / "001-feat"
    write_valid_pack(
        ofeat,
        fm=DRAFT_FM,
        tasks_rows=(
            "| T-01 | todo | yes | - | AC-01 | `src/owned/` | Owned module | `pytest tests/owned` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/my module/tài liệu.py, src/other/` | Spaced UTF8 & other | `pytest tests/other` |\n"
        ),
    )
    ofeat2 = ofeatures / "002-other"
    write_mini_spec(ofeat2, fm=DRAFT_FM)
    subprocess.run(["git", "-C", str(oroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(oroot), "commit", "-qm", "base main"], check=True)

    subprocess.run([sys.executable, "-B", str(ostamp), "001-feat", "--by", "lead", "--evidence", "PR-1", "--root", str(oroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(oroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(oroot), "commit", "-qm", "approve 001-feat on main"], check=True)
    app_main_sha = subprocess.check_output(["git", "-C", str(oroot), "rev-parse", "HEAD"], text=True).strip()

    # Branch off main and verify merge-base + unrelated main commit isolation
    subprocess.run(["git", "-C", str(oroot), "checkout", "-qb", "feat/001-feat"], check=True)
    (oroot / "src/owned").mkdir()
    (oroot / "src/owned/app.py").write_text("ok = True\n", encoding="utf-8")
    (oroot / "src/my module").mkdir()
    (oroot / "src/my module/tài liệu.py").write_text("# utf8\n", encoding="utf-8")
    (ofeat / "4. Tasks.md").write_text((ofeat / "4. Tasks.md").read_text(encoding="utf-8").replace("| T-01 | todo |", "| T-01 | done |"), encoding="utf-8")
    (ofeat / "3. QA Spec.md").write_text((ofeat / "3. QA Spec.md").read_text(encoding="utf-8") + "\nRun ok.\n", encoding="utf-8")
    (oroot / "task-evidence").mkdir()
    (oroot / "task-evidence/2026-11-18-t1.md").write_text("---\nstatus: draft\n---\n# Note\n", encoding="utf-8")
    (oroot / "CHANGELOG.md").write_text("# Changelog\n- item\n", encoding="utf-8")
    (oroot / "docs/current/02 - Architecture/Architecture.md").write_text("---\nstatus: active\nowner: eng\n---\n# Arch\n- updated\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(oroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(oroot), "commit", "-qm", "valid feature changes"], check=True)

    # Advance main with unrelated commit and verify feature branch merge-base passes cleanly without trunk warning
    subprocess.run(["git", "-C", str(oroot), "checkout", "-q", "main"], check=True)
    (oroot / "other.txt").write_text("main-v2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(oroot), "add", "other.txt"], check=True)
    subprocess.run(["git", "-C", str(oroot), "commit", "-qm", "unrelated main"], check=True)
    subprocess.run(["git", "-C", str(oroot), "checkout", "-q", "feat/001-feat"], check=True)

    res_owned_ok = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--require-tasks", "--strict", "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_owned_ok.returncode == 0, res_owned_ok.stderr
    assert "directly on" not in res_owned_ok.stderr, res_owned_ok.stderr

    # --strict-owned-paths rejects exempt CHANGELOG/Architecture/task-evidence/4. Tasks.md
    res_strict_owned = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--strict-owned-paths", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_strict_owned.returncode != 0 and "CHANGELOG.md" in res_strict_owned.stderr, res_strict_owned.stderr

    # Negative: 2. Tech Spec.md, 1. Product Spec.md, 002-other, src/rogue.py, spaced/UTF8 unowned, git mv (--no-renames), symlink 120000
    for target_file, mut_text in (
        (ofeat / "2. Tech Spec.md", "\n<!-- rogue tech edit -->\n"),
        (ofeat / "1. Product Spec.md", "\n<!-- rogue product edit -->\n"),
        (ofeat2 / "1. Mini Spec.md", "\n<!-- rogue other feature -->\n"),
    ):
        orig_t = target_file.read_text(encoding="utf-8")
        target_file.write_text(orig_t + mut_text, encoding="utf-8")
        res_bad = subprocess.run(
            [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
            capture_output=True,
            text=True,
        )
        assert res_bad.returncode != 0 and "owned-paths violation" in res_bad.stderr, f"missed {target_file.name}: {res_bad.stderr}"
        target_file.write_text(orig_t, encoding="utf-8")

    rogue = oroot / "src/rogue.py"
    rogue.write_text("bad = 1\n", encoding="utf-8")
    res_rogue = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_rogue.returncode != 0 and "src/rogue.py" in res_rogue.stderr, res_rogue.stderr
    rogue.unlink()

    utf_rogue_dir = oroot / "src/other dir"
    utf_rogue_dir.mkdir()
    utf_rogue = utf_rogue_dir / "tài liệu lạ.py"
    utf_rogue.write_text("bad\n", encoding="utf-8")
    res_utf_bad = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_utf_bad.returncode != 0 and "tài liệu lạ.py" in res_utf_bad.stderr, res_utf_bad.stderr
    shutil.rmtree(utf_rogue_dir)

    subprocess.run(["git", "-C", str(oroot), "mv", "src/unowned.py", "src/owned/x.py"], check=True)
    res_mv = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_mv.returncode != 0 and "src/unowned.py" in res_mv.stderr, res_mv.stderr
    subprocess.run(["git", "-C", str(oroot), "reset", "-q", "--hard", "HEAD"], check=True)

    sym_owned = oroot / "src/owned/sym.py"
    sym_owned.symlink_to("../unowned.py")
    subprocess.run(["git", "-C", str(oroot), "add", "src/owned/sym.py"], check=True)
    res_sym_mode = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_sym_mode.returncode != 0 and "120000" in res_sym_mode.stderr, res_sym_mode.stderr
    subprocess.run(["git", "-C", str(oroot), "reset", "-q", "--hard", "HEAD"], check=True)

    # --task T-01 zero-exemption working-tree scope
    (oroot / "src/other").mkdir()
    (oroot / "src/other/t2.py").write_text("t2 = 1\n", encoding="utf-8")
    res_task_other = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--task", "T-01", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_task_other.returncode != 0 and "src/other/t2.py" in res_task_other.stderr, res_task_other.stderr
    shutil.rmtree(oroot / "src/other")

    (oroot / "CHANGELOG.md").write_text("# Changelog\n- wt\n", encoding="utf-8")
    res_task_noex = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--task", "T-01", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_task_noex.returncode != 0 and "CHANGELOG.md" in res_task_noex.stderr, res_task_noex.stderr
    subprocess.run(["git", "-C", str(oroot), "checkout", "--", "CHANGELOG.md"], check=True)

    (oroot / "src/owned/wt.py").write_text("wt = 1\n", encoding="utf-8")
    subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--task", "T-01", "--root", str(oroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    (oroot / "src/owned/wt.py").unlink()

    # Trunk fallback --base warning hint on main
    subprocess.run(["git", "-C", str(oroot), "checkout", "-q", "main"], check=True)
    res_trunk_fail = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_trunk_fail.returncode != 0 and "other.txt" in res_trunk_fail.stderr, res_trunk_fail.stderr
    subprocess.run(["git", "-C", str(oroot), "reset", "-q", "--hard", app_main_sha], check=True)
    (oroot / "src/owned").mkdir(exist_ok=True)
    (oroot / "src/owned/on_main.py").write_text("ok = True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(oroot), "add", "src/owned/on_main.py"], check=True)
    subprocess.run(["git", "-C", str(oroot), "commit", "-qm", "owned edit on main"], check=True)
    res_trunk_warn = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_trunk_warn.returncode == 0 and "directly on 'main'" in res_trunk_warn.stderr and "--base" in res_trunk_warn.stderr, res_trunk_warn.stderr
    res_trunk_base = subprocess.run(
        [sys.executable, "-B", str(ovdocs), "--check-owned-paths", "--feature", "001-feat", "--base", app_main_sha, "--root", str(oroot)],
        capture_output=True,
        text=True,
    )
    assert res_trunk_base.returncode == 0 and "directly on 'main'" not in res_trunk_base.stderr, res_trunk_base.stderr

    # Warning #1 regression: pushed feature branch upstream (origin/feat/001-feat) + follow-up local commit still catches out-of-scope edit in pushed commit C1
    w1_bare = v7_base / "w1-origin.git"
    subprocess.run(["git", "init", "--bare", "-q", str(w1_bare)], check=True)
    w1_root = init_repo(v7_base / "w1-repo")
    w1_vdocs = w1_root / "tools/validate-docs.py"
    w1_stamp = w1_root / "tools/stamp-spec.py"
    w1_feat = w1_root / "docs/current/05 - Product Features/001-feat"
    write_valid_pack(
        w1_feat,
        fm=DRAFT_FM,
        tasks_rows="| T-01 | todo | yes | - | AC-01, AC-02 | `src/owned/` | Owned module | `pytest tests/owned` |\n",
    )
    (w1_root / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(w1_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w1_root), "commit", "-qm", "base main"], check=True)
    subprocess.run([sys.executable, "-B", str(w1_stamp), "001-feat", "--by", "lead", "--evidence", "PR-1", "--root", str(w1_root)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(w1_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w1_root), "commit", "-qm", "approve 001-feat"], check=True)
    subprocess.run(["git", "-C", str(w1_root), "remote", "add", "origin", str(w1_bare)], check=True)
    subprocess.run(["git", "-C", str(w1_root), "push", "-q", "-u", "origin", "main"], check=True)
    subprocess.run(["git", "-C", str(w1_root), "remote", "set-head", "origin", "main"], check=True)

    subprocess.run(["git", "-C", str(w1_root), "checkout", "-qb", "feat/001-feat"], check=True)
    (w1_root / "src/owned").mkdir(parents=True)
    (w1_root / "src/owned/a.py").write_text("a = 1\n", encoding="utf-8")
    (w1_root / "rogue_pushed.txt").write_text("out of scope in C1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(w1_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w1_root), "commit", "-qm", "C1 pushed with rogue"], check=True)
    subprocess.run(["git", "-C", str(w1_root), "push", "-q", "-u", "origin", "feat/001-feat"], check=True)
    (w1_root / "src/owned/b.py").write_text("b = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(w1_root), "add", "src/owned/b.py"], check=True)
    subprocess.run(["git", "-C", str(w1_root), "commit", "-qm", "C2 local owned"], check=True)

    res_w1 = subprocess.run(
        [sys.executable, "-B", str(w1_vdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(w1_root)],
        capture_output=True,
        text=True,
    )
    assert res_w1.returncode != 0 and "rogue_pushed.txt" in res_w1.stderr, res_w1.stderr

    # Even without origin/HEAD or main/master, @{upstream}=origin/feat/001-feat is skipped (matches /{curr_branch})
    subprocess.run(["git", "-C", str(w1_root), "remote", "set-head", "origin", "-d"], check=True)
    subprocess.run(["git", "-C", str(w1_root), "branch", "-D", "-q", "main"], check=True)
    res_w1_noup = subprocess.run(
        [sys.executable, "-B", str(w1_vdocs), "--check-owned-paths", "--feature", "001-feat", "--root", str(w1_root)],
        capture_output=True,
        text=True,
    )
    assert res_w1_noup.returncode != 0 and "rogue_pushed.txt" in res_w1_noup.stderr, res_w1_noup.stderr

    # Warning #2 regression: single-branch Tier L PR passes when 1. Product Spec.md / 2. Tech Spec.md are unchanged since approval, and fails on post-approval commit/dirty edit
    w2_root = init_repo(v7_base / "w2-single-pr")
    w2_vdocs = w2_root / "tools/validate-docs.py"
    w2_stamp = w2_root / "tools/stamp-spec.py"
    (w2_root / "README.md").write_text("base\n", encoding="utf-8")
    (w2_root / "docs/current/02 - Architecture").mkdir(parents=True)
    (w2_root / "docs/current/02 - Architecture/Architecture.md").write_text("---\nstatus: active\nowner: eng\n---\n# Arch\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(w2_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w2_root), "commit", "-qm", "init main"], check=True)

    subprocess.run(["git", "-C", str(w2_root), "checkout", "-qb", "feat/001-single-pr"], check=True)
    w2_feat = w2_root / "docs/current/05 - Product Features/001-single-pr"
    write_valid_pack(
        w2_feat,
        fm=DRAFT_FM,
        tasks_rows="| T-01 | todo | yes | - | AC-01, AC-02 | `src/owned/` | Owned module | `pytest tests/owned` |\n",
    )
    subprocess.run(["git", "-C", str(w2_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w2_root), "commit", "-qm", "draft 1..4 on PR branch"], check=True)

    subprocess.run([sys.executable, "-B", str(w2_stamp), "001-single-pr", "--by", "lead", "--evidence", "PR-99", "--root", str(w2_root)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(w2_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w2_root), "commit", "-qm", "approve 1..4 on PR branch"], check=True)

    (w2_root / "src/owned").mkdir(parents=True)
    (w2_root / "src/owned/feature.py").write_text("ok = True\n", encoding="utf-8")
    (w2_feat / "4. Tasks.md").write_text((w2_feat / "4. Tasks.md").read_text(encoding="utf-8").replace("| T-01 | todo |", "| T-01 | done |"), encoding="utf-8")
    (w2_feat / "3. QA Spec.md").write_text((w2_feat / "3. QA Spec.md").read_text(encoding="utf-8") + "\nVerified.\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(w2_root), "add", "."], check=True)
    subprocess.run(["git", "-C", str(w2_root), "commit", "-qm", "implement owned code on PR branch"], check=True)

    subprocess.run(
        [sys.executable, "-B", str(w2_vdocs), "--require-tasks", "--strict", "--check-owned-paths", "--feature", "001-single-pr", "--base", "main", "--root", str(w2_root)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run(
        [sys.executable, "-B", str(w2_vdocs), "--require-tasks", "--strict", "--check-owned-paths", "--feature", "001-single-pr", "--root", str(w2_root)],
        check=True,
        stdout=subprocess.DEVNULL,
    )

    for tamper_name in ("1. Product Spec.md", "2. Tech Spec.md"):
        tamper_path = w2_feat / tamper_name
        orig_spec_txt = tamper_path.read_text(encoding="utf-8")
        tamper_path.write_text(orig_spec_txt + "\n<!-- post-approval commit edit -->\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(w2_root), "add", "."], check=True)
        subprocess.run(["git", "-C", str(w2_root), "commit", "-qm", f"tamper {tamper_name} post-approval"], check=True)
        res_w2_bad = subprocess.run(
            [sys.executable, "-B", str(w2_vdocs), "--check-owned-paths", "--feature", "001-single-pr", "--base", "main", "--root", str(w2_root)],
            capture_output=True,
            text=True,
        )
        assert res_w2_bad.returncode != 0 and tamper_name in res_w2_bad.stderr and "owned-paths violation" in res_w2_bad.stderr, res_w2_bad.stderr
        subprocess.run(["git", "-C", str(w2_root), "reset", "-q", "--hard", "HEAD~1"], check=True)

    dirty_prod = w2_feat / "1. Product Spec.md"
    orig_dirty_prod = dirty_prod.read_text(encoding="utf-8")
    dirty_prod.write_text(orig_dirty_prod + "\n<!-- dirty edit -->\n", encoding="utf-8")
    res_w2_dirty = subprocess.run(
        [sys.executable, "-B", str(w2_vdocs), "--check-owned-paths", "--feature", "001-single-pr", "--base", "main", "--root", str(w2_root)],
        capture_output=True,
        text=True,
    )
    assert res_w2_dirty.returncode != 0 and "1. Product Spec.md" in res_w2_dirty.stderr, res_w2_dirty.stderr
    dirty_prod.write_text(orig_dirty_prod, encoding="utf-8")

    # Unborn-HEAD --task diff fixture exercising validate_owned_paths_diff empty-tree fallback
    from docs_validation import validate_owned_paths_diff  # noqa: E402

    ub_root = init_repo(v7_base / "unborn-repo")
    ub_vdocs = ub_root / "tools/validate-docs.py"
    ub_feat = ub_root / "docs/current/05 - Product Features/001-unborn"
    ub_rows = (
        "| T-01 | todo | yes | - | AC-01 | `docs/current/05 - Product Features/001-unborn/, src/owned/, tools/` | Owned initial task | `pytest` |\n"
        "| T-02 | todo | yes | - | AC-02 | `src/other/` | Other task | `pytest` |\n"
    )
    write_mini_spec(ub_feat, fm=APPROVED_FM, rows=ub_rows)
    (ub_root / "src/owned").mkdir(parents=True)
    (ub_root / "src/owned/a.py").write_text("a = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(ub_root), "add", "."], check=True)
    assert validate_owned_paths_diff(ub_root, feature_arg="001-unborn", task_id="T-01") == []

    # Also test CLI validate-docs.py --check-owned-paths --task under unborn HEAD
    write_mini_spec(
        ub_feat,
        fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "initial"),
        rows=ub_rows,
    )
    subprocess.run(["git", "-C", str(ub_root), "add", "."], check=True)
    res_ub_ok = subprocess.run(
        [sys.executable, "-B", str(ub_vdocs), "--check-owned-paths", "--feature", "001-unborn", "--task", "T-01", "--root", str(ub_root)],
        capture_output=True,
        text=True,
    )
    assert res_ub_ok.returncode == 0, res_ub_ok.stderr
    res_ub_notask = subprocess.run(
        [sys.executable, "-B", str(ub_vdocs), "--check-owned-paths", "--feature", "001-unborn", "--root", str(ub_root)],
        capture_output=True,
        text=True,
    )
    assert res_ub_notask.returncode != 0 and "unborn" in res_ub_notask.stderr.lower(), res_ub_notask.stderr
    (ub_root / "src/other").mkdir(parents=True)
    (ub_root / "src/other/b.py").write_text("b = 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(ub_root), "add", "src/other/b.py"], check=True)
    res_ub_bad = subprocess.run(
        [sys.executable, "-B", str(ub_vdocs), "--check-owned-paths", "--feature", "001-unborn", "--task", "T-01", "--root", str(ub_root)],
        capture_output=True,
        text=True,
    )
    assert res_ub_bad.returncode != 0 and "src/other/b.py" in res_ub_bad.stderr, res_ub_bad.stderr
    expect_fail(
        lambda: validate_owned_paths_diff(ub_root, feature_arg="001-unborn", task_id="T-01"),
        "unborn HEAD staged out-of-scope",
        "src/other/b.py",
    )

    # ImportError / missing-symbol remediation when docs_validation.py is outdated or missing
    outdated_dir = v7_base / "outdated-bundle"
    (outdated_dir / "tools").mkdir(parents=True)
    (outdated_dir / "tools/stamp-spec.py").write_text((tools_src_dir / "stamp-spec.py").read_text(encoding="utf-8"), encoding="utf-8")
    (outdated_dir / "tools/record-evidence.py").write_text((tools_src_dir / "record-evidence.py").read_text(encoding="utf-8"), encoding="utf-8")
    res_imp_err = subprocess.run(
        [sys.executable, "-B", str(outdated_dir / "tools/stamp-spec.py"), "001-x", "--by", "a", "--evidence", "b", "--root", str(outdated_dir)],
        capture_output=True,
        text=True,
    )
    assert res_imp_err.returncode == 1 and "setup.sh --update" in res_imp_err.stderr, res_imp_err.stderr
    (outdated_dir / "tools/docs_validation.py").write_text("# outdated v0.6.1 bundle stub\n", encoding="utf-8")
    res_sym_stamp = subprocess.run(
        [sys.executable, "-B", str(outdated_dir / "tools/stamp-spec.py"), "001-x", "--by", "a", "--evidence", "b", "--root", str(outdated_dir)],
        capture_output=True,
        text=True,
    )
    assert res_sym_stamp.returncode == 1 and "setup.sh --update" in res_sym_stamp.stderr, res_sym_stamp.stderr
    res_sym_rec = subprocess.run(
        [sys.executable, "-B", str(outdated_dir / "tools/record-evidence.py"), "--task-id", "t1", "--feature", "001-x", "--root", str(outdated_dir)],
        capture_output=True,
        text=True,
    )
    assert res_sym_rec.returncode == 1 and "setup.sh --update" in res_sym_rec.stderr, res_sym_rec.stderr

    # 7C. record-evidence.py + validate-task-evidence.py fixtures
    rroot = init_repo(v7_base / "rec-repo")
    rfeatures = rroot / "docs/current/05 - Product Features"
    rfeatures.mkdir(parents=True)
    rmini = rfeatures / "001-rec-mini"
    write_mini_spec(
        rmini,
        fm=DRAFT_FM,
        rows=(
            "| T-01 | todo | yes | - | AC-01 | `src/a.py` | Task A | `echo a` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/b.py` | Task B | `echo b` |\n"
        ),
    )
    (rroot / ".gitattributes").write_text("* text\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(rroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "init rec repo"], check=True)
    subprocess.run([sys.executable, "-B", str(rroot / "tools/stamp-spec.py"), "001-rec-mini", "--by", "lead", "--evidence", "PR-1", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(rroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "approve rec spec"], check=True)

    rec_bin = rroot / "tools/record-evidence.py"
    rev_bin = rroot / "tools/validate-task-evidence.py"

    # --status draft + --allow-working-tree pass
    subprocess.run(
        [sys.executable, "-B", str(rec_bin), "--task-id", "t-draft", "--feature", "001-rec-mini", "--status", "draft", "--by", "dev", "--root", str(rroot)],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)
    for f in (rroot / "task-evidence").glob("*.md"):
        f.unlink()

    # --feature without --task/--ac refuses --status completed
    res_unscoped = subprocess.run(
        [sys.executable, "-B", str(rec_bin), "--task-id", "t-unscoped", "--feature", "001-rec-mini", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), "--exec", sys.executable, "-c", "print('ok')"],
        capture_output=True,
        text=True,
    )
    assert res_unscoped.returncode != 0 and "--task" in res_unscoped.stderr, res_unscoped.stderr

    # --feature --task T-01 marks only matching AC (AC-01 PASS, AC-02 PENDING), ANSI stripped in log
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "t1-self",
            "--feature",
            "001-rec-mini",
            "--task",
            "T-01",
            "--status",
            "completed",
            "--mode",
            "self",
            "--output",
            "task-evidence/01-t1.md",
            "--artifact-path",
            "task-evidence/artifacts/01-t1.log",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
            "--exec",
            sys.executable,
            "-c",
            "print('\\x1b[32mPASS_T1\\x1b[0m')",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    t1_md = (rroot / "task-evidence/01-t1.md").read_text(encoding="utf-8")
    assert "| AC-01 |" in t1_md and "PASS / 0" in t1_md and "| AC-02 |" in t1_md and "| PENDING |" in t1_md, t1_md
    t1_log = (rroot / "task-evidence/artifacts/01-t1.log").read_text(encoding="utf-8")
    assert "PASS_T1" in t1_log and "\x1b" not in t1_log, t1_log

    # Pre-commit --allow-working-tree passes on new self record; --require-completed fails until committed
    subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)
    res_uncomm = subprocess.run([sys.executable, "-B", str(rev_bin), "--require-completed", "--root", str(rroot)], capture_output=True, text=True)
    assert res_uncomm.returncode != 0, "uncommitted self evidence must fail --require-completed"

    # Single-commit --require-completed pass (including CRLF .gitattributes * text artifact!)
    (rroot / "task-evidence/artifacts/crlf.log").write_bytes(b"line1\r\nline2\r\n")
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "crlf-self",
            "--feature",
            "001-rec-mini",
            "--ac",
            "all",
            "--status",
            "completed",
            "--mode",
            "self",
            "--output",
            "task-evidence/02-crlf.md",
            "--artifact",
            "task-evidence/artifacts/crlf.log",
            "--command",
            "crlf-check",
            "--result",
            "PASS / 0",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    crlf_md = (rroot / "task-evidence/02-crlf.md").read_text(encoding="utf-8")
    assert "| PENDING |" not in crlf_md and crlf_md.count("PASS / 0") == 2, crlf_md
    subprocess.run(["git", "-C", str(rroot), "add", "."], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "single-commit self evidence + crlf"], check=True)
    subprocess.run([sys.executable, "-B", str(rev_bin), "--require-completed", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)

    # Dirty edit to committed self record fails even under --allow-working-tree
    (rroot / "task-evidence/01-t1.md").write_text(t1_md + "\n<!-- dirty -->\n", encoding="utf-8")
    res_dirty_self = subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], capture_output=True, text=True)
    assert res_dirty_self.returncode != 0, "dirty edit to committed self record must fail even under --allow-working-tree"
    subprocess.run(["git", "-C", str(rroot), "checkout", "--", "task-evidence/01-t1.md"], check=True)

    # O_EXCL refusal to overwrite completed evidence (even with --overwrite-draft) & --output escape refusal
    res_ow_comp = subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "t1-self",
            "--output",
            "task-evidence/01-t1.md",
            "--status",
            "completed",
            "--mode",
            "self",
            "--overwrite-draft",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
            "--exec",
            sys.executable,
            "-c",
            "print('dup')",
        ],
        capture_output=True,
        text=True,
    )
    assert res_ow_comp.returncode != 0 and "completed" in res_ow_comp.stderr.lower(), res_ow_comp.stderr

    for bad_out in ("../escape.md", "task-evidence/sub/nested.md"):
        res_out_esc = subprocess.run(
            [sys.executable, "-B", str(rec_bin), "--task-id", "esc", "--output", bad_out, "--status", "draft", "--root", str(rroot)],
            capture_output=True,
            text=True,
        )
        assert res_out_esc.returncode != 0, f"expected --output refusal for {bad_out}"

    # ANSI-colored secret & non-UTF-8 --artifact secret refusal (dynamic token construction)
    ansi_cmd = "print('\\x1b[31m' + 'AKIA' + 'IOSFODNN7EXAMPLE' + '\\x1b[0m')"
    res_ansi_sec = subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "ansi-sec",
            "--output",
            "task-evidence/03-ansi-sec.md",
            "--artifact-path",
            "task-evidence/artifacts/03-ansi-sec.log",
            "--status",
            "completed",
            "--mode",
            "self",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
            "--exec",
            sys.executable,
            "-c",
            ansi_cmd,
        ],
        capture_output=True,
        text=True,
    )
    assert res_ansi_sec.returncode != 0 and "secret" in res_ansi_sec.stderr.lower(), res_ansi_sec.stderr
    assert not (rroot / "task-evidence/03-ansi-sec.md").exists() and not (rroot / "task-evidence/artifacts/03-ansi-sec.log").exists()

    bin_sec = rroot / "task-evidence/artifacts/bin-secret.bin"
    bin_sec.write_bytes(b"\xff\xfe\x00\n" + b"ghp_" + (b"A1b2C3d4E5f6" * 3) + b"\n")
    res_bin_sec = subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "bin-sec",
            "--artifact",
            "task-evidence/artifacts/bin-secret.bin",
            "--command",
            "scan",
            "--result",
            "PASS / 0",
            "--status",
            "completed",
            "--mode",
            "self",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
        ],
        capture_output=True,
        text=True,
    )
    assert res_bin_sec.returncode != 0 and "secret" in res_bin_sec.stderr.lower(), res_bin_sec.stderr
    bin_sec.unlink()

    # Post-commit git rm of artifact fails --require-completed
    subprocess.run(["git", "-C", str(rroot), "rm", "-q", "task-evidence/artifacts/01-t1.log"], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "drop artifact in C2"], check=True)
    res_rm_art = subprocess.run([sys.executable, "-B", str(rev_bin), "--require-completed", "--root", str(rroot)], capture_output=True, text=True)
    assert res_rm_art.returncode != 0, "post-commit artifact removal must fail --require-completed"
    subprocess.run(["git", "-C", str(rroot), "reset", "-q", "--hard", "HEAD~1"], check=True)

    # .gitignored .log refusal & invalid source_revision: working-tree still failing under --allow-working-tree
    (rroot / ".gitignore").write_text("*.log\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(rroot), "add", ".gitignore"], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "ignore logs"], check=True)
    res_gi = subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "gi-log",
            "--status",
            "completed",
            "--mode",
            "self",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
            "--exec",
            sys.executable,
            "-c",
            "print('ignored')",
        ],
        capture_output=True,
        text=True,
    )
    assert res_gi.returncode != 0 and ".gitignore" in res_gi.stderr, res_gi.stderr
    (rroot / ".gitignore").unlink()
    subprocess.run(["git", "-C", str(rroot), "reset", "-q", "--hard", "HEAD~1"], check=True)

    bad_wt_self = rroot / "task-evidence/99-bad-wt.md"
    bad_wt_self.write_text(t1_md.replace("source_revision: self", "source_revision: working-tree"), encoding="utf-8")
    res_wt_self = subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], capture_output=True, text=True)
    assert res_wt_self.returncode != 0, "source_revision: working-tree on completed record must fail under --allow-working-tree"
    bad_wt_self.unlink()

    # Warning #3 regression: nested --artifact-path creates parent subdirectories safely and passes validate-task-evidence.py
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "t-nested",
            "--feature",
            "001-rec-mini",
            "--task",
            "T-02",
            "--status",
            "completed",
            "--mode",
            "self",
            "--output",
            "task-evidence/04-nested.md",
            "--artifact-path",
            "task-evidence/artifacts/2026-11/nested.log",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
            "--exec",
            sys.executable,
            "-c",
            "print('nested_ok')",
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    assert (rroot / "task-evidence/artifacts/2026-11/nested.log").is_file()
    subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(rroot), "add", "task-evidence/04-nested.md", "task-evidence/artifacts/2026-11/nested.log"], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "commit nested artifact evidence"], check=True)
    subprocess.run([sys.executable, "-B", str(rev_bin), "--require-completed", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)

    # Suggestion #2 regression: secret token in --command fails secret scan and writes zero files (both normal and --dry-run)
    clean_art = rroot / "task-evidence/artifacts/clean-cmd.log"
    clean_art.write_text("ok\n", encoding="utf-8")
    dyn_secret_cmd = "curl -u " + "AKIA" + "IOSFODNN7EXAMPLE"
    for extra_flag in ([], ["--dry-run"]):
        res_cmd_sec = subprocess.run(
            [
                sys.executable,
                "-B",
                str(rec_bin),
                "--task-id",
                "cmd-sec",
                "--output",
                "task-evidence/05-cmd-sec.md",
                "--artifact",
                "task-evidence/artifacts/clean-cmd.log",
                "--command",
                dyn_secret_cmd,
                "--result",
                "PASS / 0",
                "--status",
                "completed",
                "--mode",
                "self",
                "--by",
                "dev",
                "--reviewer",
                "lead",
                "--root",
                str(rroot),
                *extra_flag,
            ],
            capture_output=True,
            text=True,
        )
        assert res_cmd_sec.returncode != 0 and "secret" in res_cmd_sec.stderr.lower(), res_cmd_sec.stderr
        assert not (rroot / "task-evidence/05-cmd-sec.md").exists()
    clean_art.unlink()

    # Suggestion #1 regression: --artifact allows backslash in table-only --command/--result (e.g. grep 'a\|b'), while YAML scalars (--by/--reviewer/--environment) still reject backslash
    bs_art = rroot / "task-evidence/artifacts/backslash-cmd.log"
    bs_art.write_text("matched a\n", encoding="utf-8")
    subprocess.run(
        [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "bs-art",
            "--feature",
            "001-rec-mini",
            "--task",
            "T-01",
            "--output",
            "task-evidence/06-backslash.md",
            "--artifact",
            "task-evidence/artifacts/backslash-cmd.log",
            "--command",
            "grep 'a\\|b'",
            "--result",
            "PASS / 0 (a\\|b)",
            "--status",
            "completed",
            "--mode",
            "self",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    bs_md = (rroot / "task-evidence/06-backslash.md").read_text(encoding="utf-8")
    assert "grep 'a\\|b'" in bs_md and "PASS / 0 (a\\|b)" in bs_md, bs_md
    subprocess.run([sys.executable, "-B", str(rev_bin), "--allow-working-tree", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(["git", "-C", str(rroot), "add", "task-evidence/06-backslash.md", "task-evidence/artifacts/backslash-cmd.log"], check=True)
    subprocess.run(["git", "-C", str(rroot), "commit", "-qm", "commit backslash artifact evidence"], check=True)
    subprocess.run([sys.executable, "-B", str(rev_bin), "--require-completed", "--root", str(rroot)], check=True, stdout=subprocess.DEVNULL)

    for bad_flag, bad_val in (("--by", "foo\\bar"), ("--reviewer", "foo\\bar"), ("--environment", "local\\dev")):
        rec_args = [
            sys.executable,
            "-B",
            str(rec_bin),
            "--task-id",
            "bad-bs",
            "--output",
            "task-evidence/07-bad-bs.md",
            "--artifact",
            "task-evidence/artifacts/backslash-cmd.log",
            "--command",
            "ok",
            "--result",
            "PASS / 0",
            "--status",
            "completed",
            "--mode",
            "self",
            "--by",
            "dev",
            "--reviewer",
            "lead",
            "--root",
            str(rroot),
        ]
        if bad_flag == "--by":
            rec_args[rec_args.index("--by") + 1] = bad_val
        elif bad_flag == "--reviewer":
            rec_args[rec_args.index("--reviewer") + 1] = bad_val
        else:
            rec_args.extend(["--environment", bad_val])
        res_bad_bs = subprocess.run(rec_args, capture_output=True, text=True)
        assert res_bad_bs.returncode != 0 and "backslash" in res_bad_bs.stderr.lower(), f"{bad_flag}: {res_bad_bs.stderr}"
        assert not (rroot / "task-evidence/07-bad-bs.md").exists()

    for bad_ctrl_val in ("grep\n", "grep\rfoo", "   "):
        res_bad_cmd = subprocess.run(
            [
                sys.executable,
                "-B",
                str(rec_bin),
                "--task-id",
                "bad-cmd",
                "--output",
                "task-evidence/07-bad-cmd.md",
                "--artifact",
                "task-evidence/artifacts/backslash-cmd.log",
                "--command",
                bad_ctrl_val,
                "--result",
                "PASS / 0",
                "--status",
                "completed",
                "--mode",
                "self",
                "--by",
                "dev",
                "--reviewer",
                "lead",
                "--root",
                str(rroot),
            ],
            capture_output=True,
            text=True,
        )
        assert res_bad_cmd.returncode != 0, f"expected refusal for --command {bad_ctrl_val!r}"

    import importlib.util as _ilu
    _rec_spec = _ilu.spec_from_file_location("_rec_mod_test", str(rec_bin))
    assert _rec_spec is not None and _rec_spec.loader is not None
    _rec_mod = _ilu.module_from_spec(_rec_spec)
    _rec_spec.loader.exec_module(_rec_mod)
    expect_fail(
        lambda: _rec_mod._validate_metadata_scalar("grep\x00foo", "--command", required=True, allow_backslash=True),
        "NUL in --command",
        "control",
    )

print("PASS: semantic Clarify gate, Mini-Spec, Git tampering, URI/embed, task-evidence, stamp-spec, owned-paths, record-evidence, and [P] concurrency fixtures")
PY

echo "PASS: documentation guardrail validation"
