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

print("PASS: semantic Clarify gate, Mini-Spec, Git tampering, URI/embed, task-evidence, and [P] concurrency fixtures")
PY

echo "PASS: documentation guardrail validation"
