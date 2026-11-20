#!/usr/bin/env python3
"""Comprehensive < 4.0s unittest suite for docs_validation, _sdd_core, and tools/*.py."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import concurrent.futures
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import re
import runpy
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from _sdd_core import GitCatFileBatch  # noqa: E402
from docs_validation import (  # noqa: E402
    _split_table_row,
    compute_contract_sha256,
    parse_frontmatter,
    read_markdown,
    validate_clarify_gate,
    validate_feature_folder,
    validate_feature_specs,
    validate_links,
    validate_mermaid,
    validate_owned_paths_diff,
)

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


def _load_tool_module(mod_name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(mod_name, str(TOOLS_DIR / filename))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


STAMP_MOD = _load_tool_module("_tool_stamp_spec", "stamp-spec.py")
VDOCS_MOD = _load_tool_module("_tool_validate_docs", "validate-docs.py")
REC_MOD = _load_tool_module("_tool_record_evidence", "record-evidence.py")
VTE_MOD = _load_tool_module("_tool_validate_task_evidence", "validate-task-evidence.py")
NF_MOD = _load_tool_module("_tool_new_feature", "new-feature.py")
EXP_MOD = _load_tool_module("_tool_export_tasks", "export-tasks.py")


def run_tool(mod: ModuleType, argv: list[str]) -> tuple[int, str, str]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
        try:
            rc = mod.main(argv)
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
        except ValueError as exc:
            print(f"FAIL: {exc}", file=err_buf)
            rc = 1
    return rc, out_buf.getvalue(), err_buf.getvalue()


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
        + "## Implementation notes\n\n- [ ] Rollout metric wired.\n\n"
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
        + "## Validation evidence\n\nPending execution.\n\n"
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
            + "Keep slices small and atomic.\n\n"
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
        + "## Design and blast radius\n\n- [ ] Telemetry wired.\n\n"
        + "## Pre-implementation readiness checklist\n\n"
        + "- [x] AGENTS.md Constitution check passed.\n\n"
        + "## Execution tasks\n\n"
        + "Execute slices sequentially.\n\n"
        + "| Task ID | Status | [P] | Depends on | Related AC | Owned paths | Summary | Verification |\n"
        + "|---|---|---|---|---|---|---|---|\n"
        + exec_rows,
        encoding="utf-8",
    )


def git_run(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


class DocsAndToolsTest(unittest.TestCase):
    """Full 100%-parity + v0.7.2 RT-01..RT-10 suite over lean cached golden sandboxes."""

    _class_tmp: tempfile.TemporaryDirectory[str] | None = None
    _owns_class_tmp: bool = False
    _shared_base: Path
    golden_repo: Path
    golden_tpl_repo: Path

    @classmethod
    def setUpClass(cls) -> None:
        shared_env = os.environ.get("_AI_TPL_SHARED_DOCSTOOLS_DIR", "").strip()
        if shared_env:
            cls._owns_class_tmp = False
            cls._class_tmp = None
            base = Path(shared_env).resolve()
            cls._shared_base = base
            cls.golden_repo = base / "golden-repo"
            cls.golden_tpl_repo = base / "golden-tpl-repo"
            return

        cls._owns_class_tmp = True
        cls._class_tmp = tempfile.TemporaryDirectory(prefix="ai-tpl-docstools-")
        base = Path(cls._class_tmp.name).resolve()
        cls._shared_base = base
        golden = base / "golden-repo"
        golden.mkdir(parents=True)
        git_run(golden, "init", "-q")
        git_run(golden, "symbolic-ref", "HEAD", "refs/heads/main")
        git_run(golden, "config", "user.email", "test@example.invalid")
        git_run(golden, "config", "user.name", "Template Test")

        (golden / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (golden / "README.md").write_text("base\n", encoding="utf-8")
        (golden / "CHANGELOG.md").write_text("# Changelog\n", encoding="utf-8")
        (golden / ".gitignore").write_text(
            ".ai-template-backup.*/\nplans/\n.DS_Store\n__pycache__/\n",
            encoding="utf-8",
        )
        (golden / "docs/current/02 - Architecture").mkdir(parents=True)
        (golden / "docs/current/02 - Architecture/Architecture.md").write_text(
            "---\nstatus: active\nowner: eng\n---\n# Arch\n",
            encoding="utf-8",
        )
        (golden / "docs/current/05 - Product Features").mkdir(parents=True)
        (golden / "task-evidence").mkdir()
        (golden / "task-evidence/.gitkeep").write_text("", encoding="utf-8")
        (golden / "template-manifest.json").write_text(
            json.dumps(
                {
                    "template": "ai-agent-obsidian-project-template",
                    "version": "0.7.2",
                    "requested_models": ["claude"],
                    "selected_models": ["claude"],
                    "managed_adapter_models": ["claude"],
                    "default_preset": "general",
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        git_run(golden, "add", ".")
        git_run(golden, "commit", "-qm", "chore: base main")
        cls.golden_repo = golden

        golden_tpl = base / "golden-tpl-repo"
        shutil.copytree(golden, golden_tpl, symlinks=True)
        shutil.copytree(ROOT / "docs/templates", golden_tpl / "docs/templates")
        for sub_rel in (
            "docs/current/01 - Overview/BA Foundation.md",
            "docs/current/08 - Diagram Standards/Diagram Standards.md",
        ):
            dst = golden_tpl / sub_rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / sub_rel, dst)
        git_run(golden_tpl, "add", ".")
        git_run(golden_tpl, "commit", "-qm", "chore: add templates")
        cls.golden_tpl_repo = golden_tpl

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._owns_class_tmp and cls._class_tmp is not None:
            cls._class_tmp.cleanup()
            cls._class_tmp = None

    def clone_golden(self, name: str, *, with_templates: bool = False) -> Path:
        td = tempfile.TemporaryDirectory(prefix=f"ai-tpl-{name}-")
        self.addCleanup(td.cleanup)
        dest = Path(td.name).resolve() / "repo"
        src = self.golden_tpl_repo if with_templates else self.golden_repo
        shutil.copytree(src, dest, symlinks=True)
        return dest

    def make_empty_dir(self, name: str) -> Path:
        td = tempfile.TemporaryDirectory(prefix=f"ai-tpl-{name}-")
        self.addCleanup(td.cleanup)
        return Path(td.name).resolve()

    def expect_fail(self, fn, expected_substr: str = "") -> None:
        with self.assertRaises(ValueError) as ctx:
            fn()
        if expected_substr:
            self.assertIn(expected_substr.lower(), str(ctx.exception).lower())

    def test_links_mermaid_clarify_packs_and_governance_yaml(self) -> None:
        """Port of validate-docs.sh Sections 1..5b (links, Mermaid, Clarify, packs, governance, triage, secrets)."""
        root = self.make_empty_dir("semantic")
        docs = root / "docs"
        current = docs / "current"
        features = current / "05 - Product Features"
        features.mkdir(parents=True)

        # 1. Links & Mermaid
        (current / "Target Note.md").write_text("---\nstatus: active\nowner: eng\n---\n# Target\n\n## Sec\n", encoding="utf-8")
        (current / "diagram.png").write_bytes(b"\x89PNG\r\n")
        note = current / "prompts.md"
        note.write_text(
            "---\nstatus: active\nowner: eng\ntags: [moc, docs]\nsource_paths: [AGENTS.md]\n---\n"
            "Inline `[[1. Product Spec]]` and ``[missing](nope.md)`` are code.\n\n"
            "Valid [spaced](./Target%20Note.md), [titled](./Target%20Note.md (Title)), "
            "[[docs/current/Target Note#Sec|Alias]], and ![[diagram.png|600]].\n\n"
            "```markdown\n[[Unresolved Wiki]] and [broken](missing-file.md)\n```\n",
            encoding="utf-8",
        )
        target_note = current / "Target Note.md"
        validate_links(root, docs, [note, target_note])
        validate_clarify_gate(root, [note, target_note], strict=True)

        broken = current / "broken.md"
        broken.write_text("Real broken [link](does-not-exist.md)\n", encoding="utf-8")
        self.expect_fail(lambda: validate_links(root, docs, [note, target_note, broken]), "missing markdown link")

        for bad_uri in ("file%3A///etc/passwd", "file:///outside.md", "javascript:alert(1)"):
            broken.write_text(f"Blocked [uri]({bad_uri})\n", encoding="utf-8")
            self.expect_fail(lambda: validate_links(root, docs, [broken]), "unsupported markdown uri scheme")

        broken.write_text("[outside](../../../outside-fixture.md)\n", encoding="utf-8")
        self.expect_fail(lambda: validate_links(root, docs, [broken]), "escapes project root")

        broken.write_text("Traversal embed ![[../../etc/passwd]]\n", encoding="utf-8")
        self.expect_fail(lambda: validate_links(root, docs, [broken]))
        broken.unlink()

        mermaid_note = current / "mermaid-test.md"
        mermaid_note.write_text(
            "```mermaid\n%%{init: {'theme': 'neutral'}}%%\nflowchart LR\n  A[\"Start\"] --> B[\"End\"]\n```\n\n"
            "````markdown\nNested example:\n```mermaid\nnot-a-diagram-inside-outer-fence\n```\n````\n",
            encoding="utf-8",
        )
        validate_mermaid(root, [mermaid_note])
        mermaid_note.unlink()

        # 2. Clarify gate & status enum
        draft_note = current / "draft-spec.md"
        draft_note.write_text(
            DRAFT_FM
            + "[NEEDS CLARIFICATION: q1]\n[NEEDS CLARIFICATION: q2]\n[NEEDS CLARIFICATION: q3]\n"
            + "`[NEEDS CLARIFICATION: ignored-in-code]`\n",
            encoding="utf-8",
        )
        validate_clarify_gate(root, [draft_note])
        draft_note.write_text(DRAFT_FM + "\n".join(f"[NEEDS CLARIFICATION: q{i}]" for i in range(4)) + "\n", encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [draft_note]), "3")

        draft_note.write_text("---\nstatus: archived\nowner: eng\n---\n# Old\n", encoding="utf-8")
        validate_clarify_gate(root, [draft_note])
        validate_clarify_gate(root, [draft_note], strict=True)

        draft_note.write_text("---\nstatus: superseded\nowner: eng\n---\n# Orphan Superseded\n", encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [draft_note], strict=False), "superseded_by")
        self.expect_fail(lambda: validate_clarify_gate(root, [draft_note], strict=True), "superseded_by")

        for valid_sup_target in ('"Target Note.md"', '"[[Target Note]]"', '"[[docs/current/Target Note#Sec|Alias]]"'):
            draft_note.write_text(
                f"---\nstatus: superseded\nsuperseded_by: {valid_sup_target}\ntags: [moc, docs]\nsource_paths: [AGENTS.md]\n---\n# Replaced\n",
                encoding="utf-8",
            )
            validate_clarify_gate(root, [draft_note], strict=True)

        draft_note.write_text("---\nstatus: approve\nowner: eng\n---\n# Typo\n", encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [draft_note]), "status")
        draft_note.unlink()

        # 3 & 4. 4-file & Mini-Spec packs, duplicate prefix, clarify/checkbox/placeholder/short-SHA
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

        validate_clarify_gate(root, sorted(current.rglob("*.md")))
        self.assertEqual(validate_feature_specs(root, features, require_tasks=True), [])

        dup_feat = features / "001-duplicate"
        write_mini_spec(dup_feat, fm=DRAFT_FM)
        self.expect_fail(lambda: validate_feature_specs(root, features), "001")
        shutil.rmtree(dup_feat)

        bad_mini = features / "007-bad-mini"
        write_mini_spec(bad_mini, fm=APPROVED_FM, rows="| T-01 | todo | no | - | AC-01 | `src/a.py` | Only AC-01 | `pytest` |\n")
        self.expect_fail(lambda: validate_feature_folder(root, bad_mini), "AC-02")
        write_mini_spec(bad_mini, fm=APPROVED_FM, rows="| T-01 | todo | no | - | - | `src/a.py` | Chore only | `pytest` |\n")
        self.expect_fail(lambda: validate_feature_folder(root, bad_mini), "AC-01")
        write_valid_pack(bad_mini, fm=DRAFT_FM)
        self.expect_fail(lambda: validate_feature_folder(root, bad_mini), "Mini Spec")
        shutil.rmtree(bad_mini)

        bad_clarify = features / "003-bad"
        write_valid_pack(bad_clarify)
        (bad_clarify / "1. Product Spec.md").write_text(
            (bad_clarify / "1. Product Spec.md").read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: leak]\n",
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Product Spec.md"]))

        write_valid_pack(bad_clarify)
        (bad_clarify / "4. Tasks.md").write_text(
            (bad_clarify / "4. Tasks.md").read_text(encoding="utf-8").replace("- [x]", "- [ ]"),
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "4. Tasks.md"]))

        for bad_token in ("todo", "tbd", "draft", ""):
            write_valid_pack(bad_clarify)
            (bad_clarify / "2. Tech Spec.md").write_text(
                (bad_clarify / "2. Tech Spec.md").read_text(encoding="utf-8").replace("approved_by: lead-eng", f"approved_by: {bad_token}"),
                encoding="utf-8",
            )
            self.expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "2. Tech Spec.md"]))

        write_mini_spec(bad_clarify, fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "0" * 40))
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"]), "source_revision")

        write_mini_spec(bad_clarify, fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "b8b8355"))
        short_warns = validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"], strict=False)
        self.assertTrue(any("b8b8355" in w for w in short_warns))
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_clarify / "1. Mini Spec.md"], strict=True), "40-char")
        shutil.rmtree(bad_clarify)

        # 5. Legacy 3-file, cycle, glob, [P] overlap, \\| table row split
        self.assertEqual(_split_table_row(r"| AC-01 | Path C:\\ | Expect OK |"), ["AC-01", r"Path C:\\", "Expect OK"])

        legacy_3 = features / "004-legacy"
        write_valid_pack(legacy_3, fm=APPROVED_FM, with_tasks=False)
        warns = validate_feature_folder(root, legacy_3, require_tasks=False)
        self.assertEqual(len(warns), 1)
        self.assertIn("4. Tasks.md", warns[0])
        self.expect_fail(lambda: validate_feature_folder(root, legacy_3, require_tasks=True), "4. Tasks.md")
        shutil.rmtree(legacy_3)

        bad_tasks = features / "008-bad-tasks"
        write_valid_pack(bad_tasks, fm=DRAFT_FM, tasks_rows="| T-01 |bogus| no | - | AC-01 | `src/a` | Bad status | `pytest` |\n")
        self.expect_fail(lambda: validate_feature_folder(root, bad_tasks), "status")
        write_valid_pack(
            bad_tasks,
            fm=DRAFT_FM,
            tasks_rows=(
                "| T-01 | todo | no | T-02 | AC-01 | `src/a` | A | `pytest` |\n"
                "| T-02 | todo | no | T-01 | AC-02 | `src/b` | B | `pytest` |\n"
            ),
        )
        self.expect_fail(lambda: validate_feature_folder(root, bad_tasks), "cycle")
        write_valid_pack(bad_tasks, fm=DRAFT_FM, tasks_rows="| T-01 | todo | no | - | AC-01 | `src/*` | Glob | `pytest` |\n")
        self.expect_fail(lambda: validate_feature_folder(root, bad_tasks), "glob")
        write_valid_pack(
            bad_tasks,
            fm=DRAFT_FM,
            tasks_rows=(
                "| T-01 | todo | yes | - | AC-01 | `src/api/` | Parent | `pytest` |\n"
                "| T-02 | todo | yes | - | AC-02 | `src/other, src/api/users.py` | Child | `pytest` |\n"
            ),
        )
        self.expect_fail(lambda: validate_feature_folder(root, bad_tasks), "overlap")
        shutil.rmtree(bad_tasks)

        # 5b. 2-hop supersession chain, export-tasks refusal, governance YAML, and brownfield triage/secrets
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
        self.assertEqual(validate_feature_specs(root, features, require_tasks=True, strict=True), [])

        rc_sup, _, err_sup = run_tool(EXP_MOD, [str(mini_ok), "--allow-draft", "--root", str(root)])
        self.assertNotEqual(rc_sup, 0)
        self.assertIn("009-auth-full", err_sup)

        arch_mini = features / "011-arch-mini"
        write_mini_spec(arch_mini, fm=APPROVED_FM.replace("status: approved\n", "status: archived\n"))
        rc_arch, _, err_arch = run_tool(EXP_MOD, [str(arch_mini), "--allow-draft", "--root", str(root)])
        self.assertNotEqual(rc_arch, 0)
        self.assertIn("archived", err_arch.lower())
        shutil.rmtree(arch_mini)

        gov_bad = current / "gov-bad.md"
        for bad_fm_body, substr in (
            ("status: superseded\nsuperseded_by: [[Target Note]]\n", "quoted"),
            ("status: [approved]\n", "scalar"),
            ('status: superseded\nsuperseded_by: "Target Note.md"\nsuperseded_by: "Overview.md"\n', "duplicate"),
            ('status: superseded\nsuperseded_by: "Target Note.md\n', "quote"),
            ('status: superseded\nsuperseded_by: "Target\\Note.md"\n', "\\"),
            ("status: |\n  superseded\n", "plain or quoted scalar"),
            ("status: superseded\nsuperseded_by: # comment-only\n", "superseded_by"),
            ('status: superseded\nsuperseded_by: "tbd"\n', "placeholder"),
            ('status: superseded\nsuperseded_by: "none"\n', "placeholder"),
            ('status: superseded\nsuperseded_by: "-"\n', "placeholder"),
            ('status: superseded\nsuperseded_by: "../outside.md"\n', ".."),
            ('status: superseded\nsuperseded_by: "%2e%2e/outside.md"\n', "%"),
            ('status: superseded\nsuperseded_by: "gov-bad.md"\n', "itself"),
        ):
            gov_bad.write_text(f"---\n{bad_fm_body}---\n# Bad\n", encoding="utf-8")
            self.expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), substr)

        bad_sup_pack = features / "012-bad-sup"
        write_mini_spec(bad_sup_pack, fm=APPROVED_FM.replace("approved_by: lead-eng", "approved_by: # waiting"))
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_sup_pack / "1. Mini Spec.md"], strict=True), "approved_by")
        write_mini_spec(bad_sup_pack, fm=DRAFT_FM.replace("status: draft\n", "status: draft\nsupersedes: [[005-mini-auth]]\n"))
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_sup_pack / "1. Mini Spec.md"], strict=True), "scalar")
        shutil.rmtree(bad_sup_pack)

        (features / "README.md").write_text("---\nstatus: active\nowner: eng\n---\n# Features\n", encoding="utf-8")
        gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "05 - Product Features/README.md"\n---\n# Bad\n', encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "spec file")
        (features / "README.md").unlink()

        sym_target = current / "Sym Target.md"
        sym_target.symlink_to(current / "Target Note.md")
        gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "Sym Target.md"\n---\n# Bad\n', encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "symlink")
        sym_target.unlink()

        cycle_b = current / "cycle-b.md"
        gov_bad.write_text('---\nstatus: superseded\nsuperseded_by: "cycle-b.md"\n---\n# A\n', encoding="utf-8")
        cycle_b.write_text('---\nstatus: superseded\nsuperseded_by: "gov-bad.md"\n---\n# B\n', encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [gov_bad, cycle_b], strict=True), "cycle")
        cycle_b.write_text("---\nstatus: archived\nowner: eng\n---\n# Dead\n", encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(root, [gov_bad], strict=True), "archived")
        cycle_b.unlink()
        gov_bad.unlink()

        bad_pack_sup = features / "013-bad-pack"
        write_valid_pack(
            bad_pack_sup,
            fm=APPROVED_FM.replace("status: approved\n", 'status: superseded\nsuperseded_by: "05 - Product Features/013-bad-pack/2. Tech Spec.md"\n'),
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Product Spec.md"], strict=True), "same feature folder")

        write_valid_pack(
            bad_pack_sup,
            fm=APPROVED_FM.replace("status: approved\n", 'status: superseded\nsuperseded_by: "05 - Product Features/010-auth-next/1. Product Spec.md"\n'),
        )
        (bad_pack_sup / "2. Tech Spec.md").write_text(
            (bad_pack_sup / "2. Tech Spec.md").read_text(encoding="utf-8").replace("010-auth-next", "001-auth"),
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_feature_folder(root, bad_pack_sup, strict=True), "same replacement")

        write_valid_pack(
            bad_pack_sup,
            fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-auth"\n'),
        )
        (bad_pack_sup / "3. QA Spec.md").write_text(
            (bad_pack_sup / "3. QA Spec.md").read_text(encoding="utf-8").replace("001-auth", "002-five-col"),
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_feature_folder(root, bad_pack_sup, strict=True), "divergent 'supersedes'")

        write_mini_spec(
            bad_pack_sup,
            fm=APPROVED_FM.replace("status: approved\n", 'status: superseded\nsuperseded_by: "05 - Product Features/006-mini-draft/1. Mini Spec.md"\n'),
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Mini Spec.md"], strict=True), "approved")

        write_mini_spec(
            bad_pack_sup,
            fm=APPROVED_FM.replace("status: approved\n", 'status: approved\nsupersedes: "05 - Product Features/001-auth"\n'),
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [bad_pack_sup / "1. Mini Spec.md"], strict=True), "superseded")
        shutil.rmtree(bad_pack_sup)
        shutil.rmtree(feat_mid)
        shutil.rmtree(feat_final)
        write_mini_spec(mini_ok, fm=APPROVED_FM)

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

        arch_note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Arch\n\n## Brownfield security and tech-debt triage\n\n"
            "| ID | Category | Severity | Risk / debt summary | Status |\n|---|---|---|---|---|\n"
            "| SEC-01 | auth | high | Missing cols | Open |\n",
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "missing required column")

        arch_note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Arch\n\n## Brownfield security and tech-debt triage\n\n"
            "| ID | Category | Severity | Evidence | Risk / debt summary | Remediation route | Target spec or evidence | Status |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| SEC-01 | auth | high | `a.py:1` | One | `/sdd-fix` | - | Open |\n"
            "| SEC-01 | auth | low | `b.py:2` | Dup | `/sdd-fix` | - | Open |\n",
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "duplicate triage id")

        arch_note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Arch\n\n## Brownfield security and tech-debt triage\n\n"
            "| ID | Category | Severity | Evidence | Risk / debt summary | Remediation route | Target spec or evidence | Status |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| SEC-01 | auth | high | `a.py:1` | Bad status | `/sdd-fix` | - | Resolved |\n",
            encoding="utf-8",
        )
        self.expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "invalid status")

        for leaked_tok in (
            "AKIA" + "IOSFODNN7EXAMPLE",
            "ghp_" + ("A1b2C3d4E5f6" * 3),
            "github_pat_" + ("11AABBCCDD" * 3),
            "-----BEGIN " + "PRIVATE KEY-----",
        ):
            arch_note.write_text(f"---\nstatus: active\nowner: eng\n---\n# Arch\n\nLeaked: {leaked_tok}\n", encoding="utf-8")
            self.expect_fail(lambda: validate_clarify_gate(root, [arch_note], strict=True), "secret")
        arch_note.unlink()

        rc_vd, _, _ = run_tool(VDOCS_MOD, ["--require-tasks", "--root", str(root)])
        self.assertEqual(rc_vd, 0)

    def test_legacy_head_sha_git_tampering_stamp_and_amend(self) -> None:
        """Port of validate-docs.sh Sections 6, 7A, 8A, and 8B for 40-hex head-sha mode + monorepo."""
        sroot = self.clone_golden("stamp-legacy")
        sfeatures = sroot / "docs/current/05 - Product Features"
        smini = sfeatures / "001-stamp-mini"
        write_mini_spec(smini, fm=DRAFT_FM)
        git_run(sroot, "add", ".")
        git_run(sroot, "commit", "-qm", "draft mini")
        s_draft_sha = git_run(sroot, "rev-parse", "HEAD")

        # Source-template guard refuses stamping inside canonical source repo without --dry-run
        rc_guard, _, err_guard = run_tool(STAMP_MOD, ["001-x", "--by", "a", "--evidence", "b", "--root", str(ROOT)])
        self.assertNotEqual(rc_guard, 0)
        self.assertIn("source ai-project-template", err_guard)

        # Initial draft -> approved in --mode head-sha (pure 40-hex, zero contract_sha256)
        rc_st, _, err_st = run_tool(
            STAMP_MOD,
            ["001-stamp-mini", "--by", "lead eng", "--evidence", "PR #42", "--at", "2026-11-18", "--mode", "head-sha", "--root", str(sroot)],
        )
        self.assertEqual(rc_st, 0, err_st)
        smini_raw = (smini / "1. Mini Spec.md").read_text(encoding="utf-8")
        self.assertIn('approval_evidence: "PR #42"', smini_raw)
        self.assertNotIn("contract_sha256", smini_raw)
        self.assertEqual(parse_frontmatter(smini_raw)["source_revision"], s_draft_sha)
        git_run(sroot, "add", ".")
        git_run(sroot, "commit", "-qm", "approve mini")

        # Converging todo -> done passes; tampering Owned paths or AC fails
        mini_path = smini / "1. Mini Spec.md"
        conv_text = mini_path.read_text(encoding="utf-8").replace("| todo |", "| done |")
        mini_path.write_text(conv_text, encoding="utf-8")
        self.assertEqual(validate_feature_folder(sroot, smini, require_tasks=True, strict=True), [])

        mini_path.write_text(conv_text.replace("src/login.py", "src/hacked.py"), encoding="utf-8")
        self.expect_fail(lambda: validate_feature_folder(sroot, smini, require_tasks=True, strict=True), "owned paths")
        mini_path.write_text(conv_text.replace("200 OK", "201 Created"), encoding="utf-8")
        self.expect_fail(lambda: validate_feature_folder(sroot, smini, require_tasks=True, strict=True), "acceptance criteria")
        mini_path.write_text(conv_text, encoding="utf-8")

        # Refusal without --amend
        rc_noam, _, err_noam = run_tool(STAMP_MOD, ["001-stamp-mini", "--by", "lead", "--evidence", "PR #43", "--root", str(sroot)])
        self.assertNotEqual(rc_noam, 0)
        self.assertIn("--amend", err_noam)

        # --amend WITHOUT --mode preserves 40-hex head-sha without adding contract_sha256 (Session 2 Q2 / Session 3 Q2)
        (sroot / "README.md").write_text("amend target\n", encoding="utf-8")
        git_run(sroot, "commit", "-qam", "advance head")
        s_adv_sha = git_run(sroot, "rev-parse", "HEAD")
        mini_path.write_text(mini_path.read_text(encoding="utf-8").replace("200 OK", "200 JSON"), encoding="utf-8")
        rc_am, _, err_am = run_tool(
            STAMP_MOD,
            ["001-stamp-mini", "--by", "lead eng", "--evidence", "PR #42", "--at", "2026-11-19", "--amend", "--root", str(sroot)],
        )
        self.assertEqual(rc_am, 0, err_am)
        amended_raw = mini_path.read_text(encoding="utf-8")
        self.assertNotIn("contract_sha256", amended_raw)
        self.assertEqual(parse_frontmatter(amended_raw)["source_revision"], s_adv_sha)
        git_run(sroot, "commit", "-qam", "commit amended mini")

        # Staged --dry-run Clarify failure & transactional rollback + multi-file supersession rollback
        sclar = sfeatures / "002-clarify-fail"
        write_mini_spec(sclar, fm=DRAFT_FM)
        clar_p = sclar / "1. Mini Spec.md"
        clar_p.write_text(clar_p.read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: missing timeout]\n", encoding="utf-8")
        orig_clar = clar_p.read_bytes()
        for extra in (["--dry-run"], []):
            rc_c, _, err_c = run_tool(STAMP_MOD, ["002-clarify-fail", "--by", "lead", "--evidence", "PR", *extra, "--root", str(sroot)])
            self.assertNotEqual(rc_c, 0)
            self.assertIn("NEEDS CLARIFICATION", err_c)
            self.assertEqual(clar_p.read_bytes(), orig_clar)
        shutil.rmtree(sclar)

        srb = sfeatures / "003-rb-full"
        write_valid_pack(srb, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'))
        (srb / "4. Tasks.md").write_text((srb / "4. Tasks.md").read_text(encoding="utf-8").replace("- [x]", "- [ ]"), encoding="utf-8")
        orig_mini_b = mini_path.read_bytes()
        orig_rb_b = {n: (srb / n).read_bytes() for n in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md")}
        rc_rb, _, _ = run_tool(STAMP_MOD, ["003-rb-full", "--by", "lead", "--evidence", "PR #45", "--root", str(sroot)])
        self.assertNotEqual(rc_rb, 0)
        self.assertEqual(mini_path.read_bytes(), orig_mini_b)
        for n, b0 in orig_rb_b.items():
            self.assertEqual((srb / n).read_bytes(), b0)
        shutil.rmtree(srb)

        # Atomic supersedes retirement + wikilink preservation on --amend + archived/hijacked refusal
        sfull = sfeatures / "004-stamp-full"
        write_valid_pack(
            sfull,
            fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'),
            tasks_rows="| T-01 | todo | yes | - | AC-01, AC-02 | `src/owned/` | Owned module | `pytest` |\n",
        )
        rc_sf, _, err_sf = run_tool(
            STAMP_MOD,
            ["004-stamp-full", "--by", "arch", "--evidence", "PR #50", "--at", "2026-11-19", "--mode", "head-sha", "--root", str(sroot)],
        )
        self.assertEqual(rc_sf, 0, err_sf)
        old_fm = parse_frontmatter(mini_path.read_text(encoding="utf-8"))
        self.assertEqual(old_fm["status"], "superseded")
        self.assertEqual(old_fm["source_revision"], s_adv_sha)
        mini_path.write_text(
            mini_path.read_text(encoding="utf-8").replace(
                '"05 - Product Features/004-stamp-full/1. Product Spec.md"',
                '"[[05 - Product Features/004-stamp-full/1. Product Spec]]"',
            ),
            encoding="utf-8",
        )
        git_run(sroot, "add", ".")
        git_run(sroot, "commit", "-qm", "commit 004 and wikilink")

        # Historical AC tampering on status: superseded spec fails
        orig_old_txt = mini_path.read_text(encoding="utf-8")
        mini_path.write_text(orig_old_txt.replace("200 JSON", "201 Tampered"), encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(sroot, [mini_path], strict=True), "acceptance criteria")
        mini_path.write_text(orig_old_txt, encoding="utf-8")

        sarch = sfeatures / "005-arch"
        write_mini_spec(sarch, fm="---\nstatus: archived\nowner: eng\n---\n")
        sfrom_arch = sfeatures / "006-from-arch"
        write_mini_spec(sfrom_arch, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/005-arch"\n'))
        rc_fa, _, err_fa = run_tool(STAMP_MOD, ["006-from-arch", "--by", "arch", "--evidence", "PR", "--root", str(sroot)])
        self.assertNotEqual(rc_fa, 0)
        self.assertIn("archived", err_fa.lower())
        shutil.rmtree(sarch)
        shutil.rmtree(sfrom_arch)

        shijack = sfeatures / "007-hijack"
        write_mini_spec(shijack, fm=DRAFT_FM.replace("status: draft\n", 'status: draft\nsupersedes: "05 - Product Features/001-stamp-mini"\n'))
        rc_hj, _, err_hj = run_tool(STAMP_MOD, ["007-hijack", "--by", "arch", "--evidence", "PR", "--root", str(sroot)])
        self.assertNotEqual(rc_hj, 0)
        self.assertIn("already superseded", err_hj.lower())
        shutil.rmtree(shijack)

        # 8A. Legacy 40-hex Tier L --amend on feature branch (reusing 004-stamp-full!) + dirty hint + backup immunity + post-amend tamper
        git_run(sroot, "checkout", "-qb", "feat/004-stamp-full")
        (sroot / "src/owned").mkdir(parents=True)
        (sroot / "src/owned/v1.py").write_text("v = 1\n", encoding="utf-8")
        git_run(sroot, "add", ".")
        git_run(sroot, "commit", "-qm", "impl v1")

        (sfull / "1. Product Spec.md").write_text(
            (sfull / "1. Product Spec.md").read_text(encoding="utf-8").replace("Session issued", r"Session issued at C:\\"),
            encoding="utf-8",
        )
        (sfull / "4. Tasks.md").write_text(
            (sfull / "4. Tasks.md").read_text(encoding="utf-8").replace("`src/owned/`", "`src/owned/, src/amended/`"),
            encoding="utf-8",
        )
        rc_am4, _, err_am4 = run_tool(
            STAMP_MOD,
            ["004-stamp-full", "--by", "arch", "--evidence", "PR #51", "--at", "2026-11-20", "--amend", "--root", str(sroot)],
        )
        self.assertEqual(rc_am4, 0, err_am4)
        self.assertIn('"[[05 - Product Features/004-stamp-full/1. Product Spec]]"', mini_path.read_text(encoding="utf-8"))
        self.assertNotIn("contract_sha256", (sfull / "1. Product Spec.md").read_text(encoding="utf-8"))

        self.expect_fail(
            lambda: validate_owned_paths_diff(sroot, feature_arg="004-stamp-full"),
            "commit the approved spec pack before running --check-owned-paths",
        )
        git_run(sroot, "commit", "-qam", "amend 004-stamp-full")
        self.assertEqual(validate_owned_paths_diff(sroot, feature_arg="004-stamp-full"), [])

        (sfull / "2. Tech Spec.md").write_text(
            (sfull / "2. Tech Spec.md").read_text(encoding="utf-8") + "\n<!-- post-amend tamper -->\n",
            encoding="utf-8",
        )
        git_run(sroot, "commit", "-qam", "tamper 2. Tech Spec")
        self.expect_fail(lambda: validate_owned_paths_diff(sroot, feature_arg="004-stamp-full"), "2. Tech Spec.md")

    def test_legacy_head_sha_monorepo_and_dry_run_links(self) -> None:
        """Port of validate-docs.sh Section 8B: Monorepo subdir (root != git_top) + zero-touch --dry-run + RT-03 traversal block."""
        mono_git = self.make_empty_dir("monorepo")
        git_run(mono_git, "init", "-q")
        git_run(mono_git, "symbolic-ref", "HEAD", "refs/heads/main")
        git_run(mono_git, "config", "user.email", "m@example.invalid")
        git_run(mono_git, "config", "user.name", "Mono")
        mono_pkg = mono_git / "packages/app-a"
        (mono_pkg / "docs/current/05 - Product Features").mkdir(parents=True)
        (mono_pkg / "AGENTS.md").write_text("# App-A Agents\n", encoding="utf-8")
        mono_feat1 = mono_pkg / "docs/current/05 - Product Features/001-mono-approved"
        write_mini_spec(mono_feat1, fm=DRAFT_FM)
        mono_guide = mono_pkg / "docs/current/guide.md"
        mono_guide.write_text("---\nstatus: active\nowner: eng\n---\n# Guide\n\nSee [AGENTS](../../AGENTS.md).\n", encoding="utf-8")
        git_run(mono_git, "add", ".")
        git_run(mono_git, "commit", "-qm", "draft mono")

        rc_ms, _, err_ms = run_tool(
            STAMP_MOD, ["001-mono-approved", "--by", "lead", "--evidence", "PR-201", "--mode", "head-sha", "--root", str(mono_pkg)]
        )
        self.assertEqual(rc_ms, 0, err_ms)
        git_run(mono_git, "commit", "-qam", "approve mono")

        mono_spec_p = mono_feat1 / "1. Mini Spec.md"
        orig_mono_spec = mono_spec_p.read_text(encoding="utf-8")
        real_sha = parse_frontmatter(orig_mono_spec)["source_revision"]
        mono_spec_p.write_text(orig_mono_spec.replace(real_sha, "deadbeef" * 5), encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(mono_pkg, [mono_spec_p], strict=True), "source_revision")
        mono_spec_p.write_text(orig_mono_spec.replace("200 OK", "201 Tampered"), encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(mono_pkg, [mono_spec_p], strict=True), "acceptance criteria")
        mono_spec_p.write_text(orig_mono_spec, encoding="utf-8")

        mono_feat2 = mono_pkg / "docs/current/05 - Product Features/002-mono-dry"
        write_mini_spec(mono_feat2, fm=DRAFT_FM)
        staged_top_entries: list[list[str]] = []
        orig_tempdir = STAMP_MOD.tempfile.TemporaryDirectory

        class _InspectTempDir:
            def __init__(self, *a, **kw):
                self._inner = orig_tempdir(*a, **kw)
                self.name = self._inner.name

            def __enter__(self):
                return self._inner.__enter__()

            def __exit__(self, exc_type, exc, tb):
                staged_top_entries.append(sorted(p.name for p in Path(self.name).iterdir()))
                return self._inner.__exit__(exc_type, exc, tb)

        STAMP_MOD.tempfile.TemporaryDirectory = _InspectTempDir
        try:
            rc_dry, out_dry, err_dry = run_tool(
                STAMP_MOD, ["002-mono-dry", "--by", "lead", "--evidence", "PR-202", "--dry-run", "--root", str(mono_pkg)]
            )
        finally:
            STAMP_MOD.tempfile.TemporaryDirectory = orig_tempdir
        self.assertEqual(rc_dry, 0, err_dry)
        self.assertIn("DRY-RUN:", out_dry)
        self.assertEqual(staged_top_entries, [["docs"]])

        orig_guide = mono_guide.read_text(encoding="utf-8")
        mono_guide.write_text(orig_guide + "\nBad [traversal](../../../docs/current/deleted.md).\n", encoding="utf-8")
        rc_esc, _, err_esc = run_tool(
            STAMP_MOD, ["002-mono-dry", "--by", "lead", "--evidence", "PR-203", "--dry-run", "--root", str(mono_pkg)]
        )
        self.assertNotEqual(rc_esc, 0)
        self.assertIn("escapes project root", err_esc)
        mono_guide.write_text(orig_guide, encoding="utf-8")

        ghost_doc = mono_pkg / "docs/current/deleted.md"
        ghost_doc.write_text("---\nstatus: active\nowner: eng\n---\n# Ghost\n", encoding="utf-8")
        stage_dir = self.make_empty_dir("rt03-stage")
        shutil.copytree(mono_pkg / "docs", stage_dir / "docs")
        (stage_dir / "docs/current/deleted.md").unlink()
        staged_g = stage_dir / "docs/current/guide.md"
        staged_g.write_text(orig_guide + "\nGhost [doc](../../docs/current/deleted.md).\n", encoding="utf-8")
        self.expect_fail(
            lambda: validate_links(stage_dir, stage_dir / "docs", [staged_g], external_root=mono_pkg),
            "missing markdown link target",
        )

    def test_owned_paths_diff_matrix_upstream_single_pr_and_unborn(self) -> None:
        """Port of validate-docs.sh Section 7B (owned-paths, UTF-8, git mv, 120000, --task, upstream W1, single-PR W2, unborn HEAD)."""
        oroot = self.clone_golden("owned-paths")
        (oroot / "src").mkdir()
        (oroot / "src/unowned.py").write_text("x = 1\n", encoding="utf-8")
        (oroot / "other.txt").write_text("main\n", encoding="utf-8")

        ofeat = oroot / "docs/current/05 - Product Features/001-feat"
        write_valid_pack(
            ofeat,
            fm=DRAFT_FM,
            tasks_rows=(
                "| T-01 | todo | yes | - | AC-01 | `src/owned/` | Owned module | `pytest tests/owned` |\n"
                "| T-02 | todo | yes | - | AC-02 | `src/my module/tài liệu.py, src/other/` | Spaced UTF8 & other | `pytest tests/other` |\n"
            ),
        )
        ofeat2 = oroot / "docs/current/05 - Product Features/002-other"
        write_mini_spec(ofeat2, fm=DRAFT_FM)
        git_run(oroot, "add", ".")
        git_run(oroot, "commit", "-qm", "base main")

        run_tool(STAMP_MOD, ["001-feat", "--by", "lead", "--evidence", "PR-1", "--mode", "head-sha", "--root", str(oroot)])
        git_run(oroot, "commit", "-qam", "approve 001-feat on main")
        app_main_sha = git_run(oroot, "rev-parse", "HEAD")

        git_run(oroot, "checkout", "-qb", "feat/001-feat")
        (oroot / "src/owned").mkdir()
        (oroot / "src/owned/app.py").write_text("ok = True\n", encoding="utf-8")
        (oroot / "src/my module").mkdir()
        (oroot / "src/my module/tài liệu.py").write_text("# utf8\n", encoding="utf-8")
        (ofeat / "4. Tasks.md").write_text((ofeat / "4. Tasks.md").read_text(encoding="utf-8").replace("| T-01 | todo |", "| T-01 | done |"), encoding="utf-8")
        (ofeat / "3. QA Spec.md").write_text((ofeat / "3. QA Spec.md").read_text(encoding="utf-8") + "\nRun ok.\n", encoding="utf-8")
        (oroot / "task-evidence/2026-11-18-t1.md").write_text("---\nstatus: draft\n---\n# Note\n", encoding="utf-8")
        (oroot / "CHANGELOG.md").write_text("# Changelog\n- item\n", encoding="utf-8")
        (oroot / "docs/current/02 - Architecture/Architecture.md").write_text(
            (oroot / "docs/current/02 - Architecture/Architecture.md").read_text(encoding="utf-8") + "\n- updated\n",
            encoding="utf-8",
        )
        git_run(oroot, "add", ".")
        git_run(oroot, "commit", "-qm", "valid feature changes")

        git_run(oroot, "checkout", "-q", "main")
        (oroot / "other.txt").write_text("main-v2\n", encoding="utf-8")
        git_run(oroot, "commit", "-qam", "unrelated main")
        git_run(oroot, "checkout", "-q", "feat/001-feat")

        rc_ok, _, err_ok = run_tool(
            VDOCS_MOD, ["--require-tasks", "--strict", "--check-owned-paths", "--feature", "001-feat", "--root", str(oroot)]
        )
        self.assertEqual(rc_ok, 0, err_ok)
        self.assertNotIn("directly on", err_ok)

        # Untracked .ai-template-backup.* ignored even when .gitignore does not cover it
        (oroot / ".gitignore").write_text("", encoding="utf-8")
        git_run(oroot, "commit", "-qam", "empty gitignore")
        git_run(oroot, "reset", "-q", "--hard", "HEAD~1")
        backup_dir = oroot / ".ai-template-backup.xyz"
        backup_dir.mkdir()
        (backup_dir / "AGENTS.md").write_text("# b\n", encoding="utf-8")
        self.assertEqual(validate_owned_paths_diff(oroot, feature_arg="001-feat"), [])
        shutil.rmtree(backup_dir)

        self.expect_fail(
            lambda: validate_owned_paths_diff(oroot, feature_arg="001-feat", strict_owned_paths=True),
            "CHANGELOG.md",
        )

        for target_file in (ofeat / "2. Tech Spec.md", ofeat / "1. Product Spec.md", ofeat2 / "1. Mini Spec.md"):
            target_file.write_text(target_file.read_text(encoding="utf-8") + "\n<!-- rogue edit -->\n", encoding="utf-8")
        rogue = oroot / "src/rogue.py"
        rogue.write_text("bad = 1\n", encoding="utf-8")
        utf_rogue_dir = oroot / "src/other dir"
        utf_rogue_dir.mkdir()
        (utf_rogue_dir / "tài liệu lạ.py").write_text("bad\n", encoding="utf-8")
        git_run(oroot, "mv", "src/unowned.py", "src/owned/x.py")

        with self.assertRaises(ValueError) as vio_ctx:
            validate_owned_paths_diff(oroot, feature_arg="001-feat")
        vio_msg = str(vio_ctx.exception)
        for expected_vio in (
            "1. Product Spec.md",
            "2. Tech Spec.md",
            "002-other/1. Mini Spec.md",
            "src/rogue.py",
            "tài liệu lạ.py",
            "src/unowned.py",
        ):
            self.assertIn(expected_vio, vio_msg)

        rogue.unlink()
        shutil.rmtree(utf_rogue_dir)
        git_run(oroot, "reset", "-q", "--hard", "HEAD")

        sym_owned = oroot / "src/owned/sym.py"
        sym_owned.symlink_to("../unowned.py")
        git_run(oroot, "add", "src/owned/sym.py")
        self.expect_fail(lambda: validate_owned_paths_diff(oroot, feature_arg="001-feat"), "120000")
        git_run(oroot, "reset", "-q", "--hard", "HEAD")

        # --task T-01 zero-exemption scope
        (oroot / "src/other").mkdir()
        (oroot / "src/other/t2.py").write_text("t2 = 1\n", encoding="utf-8")
        (oroot / "CHANGELOG.md").write_text("# Changelog\n- wt\n", encoding="utf-8")
        with self.assertRaises(ValueError) as task_vio_ctx:
            validate_owned_paths_diff(oroot, feature_arg="001-feat", task_id="T-01")
        self.assertIn("src/other/t2.py", str(task_vio_ctx.exception))
        self.assertIn("CHANGELOG.md", str(task_vio_ctx.exception))
        shutil.rmtree(oroot / "src/other")
        git_run(oroot, "checkout", "--", "CHANGELOG.md")

        (oroot / "src/owned/wt.py").write_text("wt = 1\n", encoding="utf-8")
        self.assertEqual(validate_owned_paths_diff(oroot, feature_arg="001-feat", task_id="T-01"), [])
        (oroot / "src/owned/wt.py").unlink()

        # Trunk fallback --base warning hint on main
        git_run(oroot, "checkout", "-q", "main")
        self.expect_fail(lambda: validate_owned_paths_diff(oroot, feature_arg="001-feat"), "other.txt")
        git_run(oroot, "reset", "-q", "--hard", app_main_sha)
        (oroot / "src/owned").mkdir(exist_ok=True)
        (oroot / "src/owned/on_main.py").write_text("ok = True\n", encoding="utf-8")
        git_run(oroot, "add", "src/owned/on_main.py")
        git_run(oroot, "commit", "-qm", "owned edit on main")
        trunk_warns = validate_owned_paths_diff(oroot, feature_arg="001-feat")
        self.assertTrue(any("directly on 'main'" in w for w in trunk_warns))
        self.assertEqual(validate_owned_paths_diff(oroot, feature_arg="001-feat", base_rev=app_main_sha), [])

        # W1: pushed feature branch upstream + follow-up local commit catches C1 out-of-scope
        w1_bare = self.make_empty_dir("w1-bare") / "origin.git"
        subprocess.run(["git", "init", "--bare", "-q", str(w1_bare)], check=True)
        git_run(oroot, "reset", "-q", "--hard", app_main_sha)
        git_run(oroot, "remote", "add", "origin", str(w1_bare))
        git_run(oroot, "push", "-q", "-u", "origin", "main")
        git_run(oroot, "remote", "set-head", "origin", "main")
        git_run(oroot, "checkout", "-qb", "feat/w1-test")
        (oroot / "src/owned").mkdir(exist_ok=True)
        (oroot / "src/owned/a.py").write_text("a = 1\n", encoding="utf-8")
        (oroot / "rogue_pushed.txt").write_text("rogue\n", encoding="utf-8")
        git_run(oroot, "add", ".")
        git_run(oroot, "commit", "-qm", "C1 pushed with rogue")
        git_run(oroot, "push", "-q", "-u", "origin", "feat/w1-test")
        (oroot / "src/owned/b.py").write_text("b = 2\n", encoding="utf-8")
        git_run(oroot, "add", "src/owned/b.py")
        git_run(oroot, "commit", "-qm", "C2 local owned")
        self.expect_fail(lambda: validate_owned_paths_diff(oroot, feature_arg="001-feat"), "rogue_pushed.txt")
        git_run(oroot, "remote", "set-head", "origin", "-d")
        git_run(oroot, "branch", "-D", "-q", "main")
        self.expect_fail(lambda: validate_owned_paths_diff(oroot, feature_arg="001-feat"), "rogue_pushed.txt")

    def test_owned_paths_single_pr_and_unborn_head(self) -> None:
        """Port of validate-docs.sh Section 7B W2 single-branch Tier L PR + unborn HEAD --task diff fixture."""
        w2_root = self.clone_golden("w2-single-pr")
        git_run(w2_root, "checkout", "-qb", "feat/001-single-pr")
        w2_feat = w2_root / "docs/current/05 - Product Features/001-single-pr"
        write_valid_pack(w2_feat, fm=DRAFT_FM, tasks_rows="| T-01 | todo | yes | - | AC-01, AC-02 | `src/owned/` | Owned | `pytest` |\n")
        git_run(w2_root, "add", ".")
        git_run(w2_root, "commit", "-qm", "draft on PR")
        run_tool(STAMP_MOD, ["001-single-pr", "--by", "lead", "--evidence", "PR-99", "--mode", "head-sha", "--root", str(w2_root)])
        git_run(w2_root, "commit", "-qam", "approve on PR")
        (w2_root / "src/owned").mkdir(parents=True)
        (w2_root / "src/owned/feature.py").write_text("ok = True\n", encoding="utf-8")
        (w2_feat / "4. Tasks.md").write_text((w2_feat / "4. Tasks.md").read_text(encoding="utf-8").replace("| T-01 | todo |", "| T-01 | done |"), encoding="utf-8")
        git_run(w2_root, "add", ".")
        git_run(w2_root, "commit", "-qm", "implement on PR")
        self.assertEqual(validate_owned_paths_diff(w2_root, feature_arg="001-single-pr", base_rev="main"), [])
        dirty_prod = w2_feat / "1. Product Spec.md"
        orig_dp = dirty_prod.read_text(encoding="utf-8")
        dirty_prod.write_text(orig_dp + "\n<!-- dirty -->\n", encoding="utf-8")
        self.expect_fail(lambda: validate_owned_paths_diff(w2_root, feature_arg="001-single-pr", base_rev="main"), "1. Product Spec.md")
        dirty_prod.write_text(orig_dp, encoding="utf-8")

        # Unborn HEAD --task diff fixture
        ub_root = self.make_empty_dir("unborn")
        git_run(ub_root, "init", "-q")
        git_run(ub_root, "config", "user.email", "u@example.invalid")
        git_run(ub_root, "config", "user.name", "Unborn")
        ub_feat = ub_root / "docs/current/05 - Product Features/001-unborn"
        ub_rows = (
            "| T-01 | todo | yes | - | AC-01 | `docs/current/05 - Product Features/001-unborn/, src/owned/` | Owned | `pytest` |\n"
            "| T-02 | todo | yes | - | AC-02 | `src/other/` | Other | `pytest` |\n"
        )
        write_mini_spec(ub_feat, fm=APPROVED_FM.replace("b8b83557c19217002b0586c052b68e2684706057", "initial"), rows=ub_rows)
        (ub_root / "src/owned").mkdir(parents=True)
        (ub_root / "src/owned/a.py").write_text("a = 1\n", encoding="utf-8")
        git_run(ub_root, "add", ".")
        rc_ub, _, err_ub = run_tool(VDOCS_MOD, ["--check-owned-paths", "--feature", "001-unborn", "--task", "T-01", "--root", str(ub_root)])
        self.assertEqual(rc_ub, 0, err_ub)
        rc_ub_nt, _, err_ub_nt = run_tool(VDOCS_MOD, ["--check-owned-paths", "--feature", "001-unborn", "--root", str(ub_root)])
        self.assertNotEqual(rc_ub_nt, 0)
        self.assertIn("unborn", err_ub_nt.lower())
        (ub_root / "src/other").mkdir(parents=True)
        (ub_root / "src/other/b.py").write_text("b = 2\n", encoding="utf-8")
        git_run(ub_root, "add", "src/other/b.py")
        self.expect_fail(lambda: validate_owned_paths_diff(ub_root, feature_arg="001-unborn", task_id="T-01"), "src/other/b.py")

    def test_record_and_validate_task_evidence_security_matrix(self) -> None:
        """Port of validate-docs.sh Sections 6 & 7C + setup.sh strict missing-artifact check."""
        rroot = self.clone_golden("rec-evidence")
        rmini = rroot / "docs/current/05 - Product Features/001-rec-mini"
        write_mini_spec(
            rmini,
            fm=DRAFT_FM,
            rows=(
                "| T-01 | todo | yes | - | AC-01 | `src/a.py` | Task A | `echo a` |\n"
                "| T-02 | todo | yes | - | AC-02 | `src/b.py` | Task B | `echo b` |\n"
            ),
        )
        (rroot / "artifact.txt").write_text("v1\n", encoding="utf-8")
        (rroot / ".gitattributes").write_text("* text\n", encoding="utf-8")
        git_run(rroot, "add", ".")
        git_run(rroot, "commit", "-qm", "init rec repo")
        run_tool(STAMP_MOD, ["001-rec-mini", "--by", "lead", "--evidence", "PR-1", "--root", str(rroot)])
        git_run(rroot, "commit", "-qam", "approve rec spec")
        approved_sha = git_run(rroot, "rev-parse", "HEAD")
        art_sha = hashlib.sha256((rroot / "artifact.txt").read_bytes()).hexdigest()
        ev_dir = rroot / "task-evidence"

        # CRLF quoted draft + --allow-working-tree vs --require-completed mutual exclusion
        draft_ev = ev_dir / "00-draft.md"
        draft_ev.write_bytes(
            (
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
                "# Draft Evidence\r\n\r\n| AC-01 | Check | cmd | Pass / 0 |\r\n"
            ).encode("utf-8")
        )
        self.assertEqual(run_tool(VTE_MOD, ["--allow-working-tree", "--root", str(rroot)])[0], 0)
        self.assertNotEqual(run_tool(VTE_MOD, ["--allow-working-tree", "--require-completed", "--root", str(rroot)])[0], 0)
        draft_ev.unlink()

        # CRLF quoted 40-hex completed pass, working-tree rejection, downstream corrections spoof ignored, missing artifact at rev, symlink rejection
        comp_ev = ev_dir / "00-comp.md"
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
                "# Completed Evidence\r\n\r\n| AC-01 | Check | cmd | Pass / 0 |\r\n"
            ).encode("utf-8")
        )
        self.assertEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)

        bad_wt = ev_dir / "00-bad-wt.md"
        bad_wt.write_text(comp_ev.read_text(encoding="utf-8").replace(approved_sha, "working-tree"), encoding="utf-8")
        self.assertNotEqual(run_tool(VTE_MOD, ["--allow-working-tree", "--root", str(rroot)])[0], 0)
        bad_wt.unlink()

        root_commit = git_run(rroot, "rev-list", "--max-parents=0", "HEAD")
        missing_at_rev = ev_dir / "00-missing-at-rev.md"
        missing_at_rev.write_text(comp_ev.read_text(encoding="utf-8").replace(approved_sha, root_commit), encoding="utf-8")
        self.assertNotEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)
        missing_at_rev.unlink()

        bogus_rev = "1" * 40
        comp_ev.write_text(comp_ev.read_text(encoding="utf-8").replace(approved_sha, bogus_rev), encoding="utf-8")
        (ev_dir / "evidence-corrections.json").write_text(
            json.dumps({"schema_version": 1, "corrections": {"task-evidence/00-comp.md": {"source_revision": approved_sha, "reason": "spoof"}}}),
            encoding="utf-8",
        )
        self.assertNotEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)
        (ev_dir / "evidence-corrections.json").unlink()
        comp_ev.unlink()

        outside_ev = self.make_empty_dir("outside-ev") / "outside.md"
        outside_ev.write_text("# out\n", encoding="utf-8")
        sym_ev = ev_dir / "99-sym.md"
        sym_ev.symlink_to(outside_ev)
        self.assertNotEqual(run_tool(VTE_MOD, ["--root", str(rroot)])[0], 0)
        sym_ev.unlink()

        # record-evidence.py: --feature without --task/--ac refuses completed
        rc_unsc, _, err_unsc = run_tool(
            REC_MOD,
            ["--task-id", "t-unscoped", "--feature", "001-rec-mini", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), "--exec", "/bin/echo", "ok"],
        )
        self.assertNotEqual(rc_unsc, 0)
        self.assertIn("--task", err_unsc)

        # --task T-01 marks AC-01 PASS and AC-02 PENDING + strips ANSI
        rc_t1, _, err_t1 = run_tool(
            REC_MOD,
            [
                "--task-id", "t1-self",
                "--feature", "001-rec-mini",
                "--task", "T-01",
                "--status", "completed",
                "--mode", "self",
                "--output", "task-evidence/01-t1.md",
                "--artifact-path", "task-evidence/artifacts/01-t1.log",
                "--by", "dev",
                "--reviewer", "lead",
                "--root", str(rroot),
                "--exec", "/usr/bin/printf", "\\033[32mPASS_T1\\033[0m\\n",
            ],
        )
        self.assertEqual(rc_t1, 0, err_t1)
        t1_md = (ev_dir / "01-t1.md").read_text(encoding="utf-8")
        self.assertIn("| AC-01 |", t1_md)
        self.assertIn("PASS / 0", t1_md)
        self.assertIn("| PENDING |", t1_md)
        t1_log = (ev_dir / "artifacts/01-t1.log").read_text(encoding="utf-8")
        self.assertIn("PASS_T1", t1_log)
        self.assertNotIn("\x1b", t1_log)

        self.assertEqual(run_tool(VTE_MOD, ["--allow-working-tree", "--root", str(rroot)])[0], 0)
        self.assertNotEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)

        # CRLF artifact + nested artifact-path + backslash in --command/--result
        (ev_dir / "artifacts/crlf.log").write_bytes(b"line1\r\nline2\r\n")
        rc_crlf, _, err_crlf = run_tool(
            REC_MOD,
            [
                "--task-id", "crlf-self",
                "--feature", "001-rec-mini",
                "--ac", "all",
                "--status", "completed",
                "--mode", "self",
                "--output", "task-evidence/02-crlf.md",
                "--artifact", "task-evidence/artifacts/crlf.log",
                "--command", "grep 'a\\|b'",
                "--result", "PASS / 0 (a\\|b)",
                "--by", "dev",
                "--reviewer", "lead",
                "--root", str(rroot),
            ],
        )
        self.assertEqual(rc_crlf, 0, err_crlf)
        rc_nest, _, err_nest = run_tool(
            REC_MOD,
            [
                "--task-id", "t-nested",
                "--feature", "001-rec-mini",
                "--task", "T-02",
                "--status", "completed",
                "--mode", "self",
                "--output", "task-evidence/04-nested.md",
                "--artifact-path", "task-evidence/artifacts/2026-11/nested.log",
                "--by", "dev",
                "--reviewer", "lead",
                "--root", str(rroot),
                "--exec", "/bin/echo", "nested_ok",
            ],
        )
        self.assertEqual(rc_nest, 0, err_nest)

        git_run(rroot, "add", ".")
        git_run(rroot, "commit", "-qm", "single-commit self evidence")
        self.assertEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)

        (ev_dir / "01-t1.md").write_text(t1_md + "\n<!-- dirty -->\n", encoding="utf-8")
        self.assertNotEqual(run_tool(VTE_MOD, ["--allow-working-tree", "--root", str(rroot)])[0], 0)
        git_run(rroot, "checkout", "--", "task-evidence/01-t1.md")

        rc_ow, _, err_ow = run_tool(
            REC_MOD,
            ["--task-id", "t1-self", "--output", "task-evidence/01-t1.md", "--status", "completed", "--mode", "self", "--overwrite-draft", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), "--exec", "/bin/echo", "dup"],
        )
        self.assertNotEqual(rc_ow, 0)
        self.assertIn("completed", err_ow.lower())

        for bad_out in ("../escape.md", "task-evidence/sub/nested.md"):
            self.assertNotEqual(
                run_tool(REC_MOD, ["--task-id", "esc", "--output", bad_out, "--status", "draft", "--root", str(rroot)])[0],
                0,
            )

        # Secret scanning: ANSI-colored secret, non-UTF-8 --artifact secret, and --command secret (normal & --dry-run)
        rc_as, _, err_as = run_tool(
            REC_MOD,
            ["--task-id", "ansi-sec", "--output", "task-evidence/03-ansi.md", "--artifact-path", "task-evidence/artifacts/03-ansi.log", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), "--exec", "/usr/bin/printf", "\\033[31m" + "AKIA" + "IOSFODNN7EXAMPLE\\033[0m\\n"],
        )
        self.assertNotEqual(rc_as, 0)
        self.assertIn("secret", err_as.lower())
        self.assertFalse((ev_dir / "03-ansi.md").exists())

        bin_sec = ev_dir / "artifacts/bin-secret.bin"
        bin_sec.write_bytes(b"\xff\xfe\x00\n" + b"ghp_" + (b"A1b2C3d4E5f6" * 3) + b"\n")
        rc_bs, _, err_bs = run_tool(
            REC_MOD,
            ["--task-id", "bin-sec", "--artifact", "task-evidence/artifacts/bin-secret.bin", "--command", "scan", "--result", "PASS / 0", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot)],
        )
        self.assertNotEqual(rc_bs, 0)
        self.assertIn("secret", err_bs.lower())
        bin_sec.unlink()

        clean_art = ev_dir / "artifacts/clean-cmd.log"
        clean_art.write_text("ok\n", encoding="utf-8")
        dyn_sec_cmd = "curl -u " + "AKIA" + "IOSFODNN7EXAMPLE"
        for extra_f in ([], ["--dry-run"]):
            rc_cs, _, err_cs = run_tool(
                REC_MOD,
                ["--task-id", "cmd-sec", "--output", "task-evidence/05-cmd.md", "--artifact", "task-evidence/artifacts/clean-cmd.log", "--command", dyn_sec_cmd, "--result", "PASS / 0", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), *extra_f],
            )
            self.assertNotEqual(rc_cs, 0)
            self.assertIn("secret", err_cs.lower())
            self.assertFalse((ev_dir / "05-cmd.md").exists())

        for bad_flag, bad_val in (("--by", "foo\\bar"), ("--reviewer", "foo\\bar"), ("--environment", "local\\dev")):
            argv = ["--task-id", "bad-bs", "--output", "task-evidence/07-bs.md", "--artifact", "task-evidence/artifacts/clean-cmd.log", "--command", "ok", "--result", "PASS / 0", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot)]
            if bad_flag in argv:
                argv[argv.index(bad_flag) + 1] = bad_val
            else:
                argv.extend([bad_flag, bad_val])
            rc_b, _, err_b = run_tool(REC_MOD, argv)
            self.assertNotEqual(rc_b, 0)
            self.assertIn("backslash", err_b.lower())

        for bad_ctrl in ("grep\n", "grep\rfoo", "   ", "grep\x00foo"):
            self.assertNotEqual(
                run_tool(REC_MOD, ["--task-id", "bad-cmd", "--output", "task-evidence/07-cmd.md", "--artifact", "task-evidence/artifacts/clean-cmd.log", "--command", bad_ctrl, "--result", "PASS / 0", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot)])[0],
                0,
            )
        clean_art.unlink()

        git_run(rroot, "rm", "-q", "task-evidence/artifacts/01-t1.log")
        git_run(rroot, "commit", "-qm", "drop artifact")
        self.assertNotEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(rroot)])[0], 0)
        git_run(rroot, "reset", "-q", "--hard", "HEAD~1")

        (rroot / ".gitignore").write_text("*.log\n", encoding="utf-8")
        rc_gi, _, err_gi = run_tool(
            REC_MOD,
            ["--task-id", "gi-log", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(rroot), "--exec", "/bin/echo", "ignored"],
        )
        self.assertNotEqual(rc_gi, 0)
        self.assertIn(".gitignore", err_gi)

    def test_new_feature_and_export_tasks_full_matrix(self) -> None:
        """Port of setup.sh new-feature.py & export-tasks.py scenarios (presets, --mini, --supersede, mock gh)."""
        proot = self.clone_golden("presets-export", with_templates=True)
        custom_p = proot / "docs/templates/presets/team-api"
        custom_p.mkdir(parents=True)
        (custom_p / "README.md").write_text(
            "# Custom Team API — [Feature name]\n\n- [[1. Product Spec]]\n- [[2. Tech Spec]]\n- [[3. QA Spec]]\n- [[4. Tasks]]\n",
            encoding="utf-8",
        )
        m_data = json.loads((proot / "template-manifest.json").read_text(encoding="utf-8"))
        m_data["default_preset"] = "team-api"
        (proot / "template-manifest.json").write_text(json.dumps(m_data, indent=2) + "\n", encoding="utf-8")

        self.assertEqual(run_tool(NF_MOD, ["--list-presets", "--root", str(ROOT)])[0], 0)
        self.assertEqual(run_tool(NF_MOD, ["preview-only", "--dry-run", "--root", str(ROOT)])[0], 0)
        rc_src_nf, _, err_src_nf = run_tool(NF_MOD, ["accidental-spec", "--root", str(ROOT)])
        self.assertNotEqual(rc_src_nf, 0)
        self.assertIn("refusing to scaffold feature specs inside the source ai-project-template repository", err_src_nf)

        rc_lp, out_lp, _ = run_tool(NF_MOD, ["--list-presets", "--root", str(proot)])
        self.assertEqual(rc_lp, 0)
        self.assertIn("web-api (built-in)", out_lp)
        self.assertIn("security-hardening (built-in)", out_lp)
        self.assertIn("team-api (custom:", out_lp)

        self.assertEqual(run_tool(NF_MOD, ["dry-check", "--preset", "general", "--dry-run", "--root", str(proot)])[0], 0)
        self.assertFalse((proot / "docs/current/05 - Product Features/001-dry-check").exists())

        for slug, preset in (("auth", "general"), ("billing", "web-api"), ("sync-cli", "cli-tool"), ("triage-bot", "ai-agent")):
            self.assertEqual(run_tool(NF_MOD, [slug, "--preset", preset, "--root", str(proot)])[0], 0)

        f_auth = proot / "docs/current/05 - Product Features/001-auth"
        self.assertTrue(f_auth.is_dir())
        self.assertFalse((f_auth / "README.md").exists())
        for sf in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            self.assertRegex((f_auth / sf).read_text(encoding="utf-8"), r"(?m)^source_revision:[ \t]*$")

        self.assertNotEqual(run_tool(NF_MOD, ["auth", "--root", str(proot)])[0], 0)
        self.assertNotEqual(run_tool(NF_MOD, ["../evil", "--root", str(proot)])[0], 0)
        rc_nnn, _, err_nnn = run_tool(NF_MOD, ["001-dup-prefix", "--root", str(proot)])
        self.assertNotEqual(rc_nnn, 0)
        self.assertIn("do not include a leading numeric prefix", err_nnn)

        self.assertEqual(run_tool(NF_MOD, ["custom-svc", "--plain", "--root", str(proot)])[0], 0)
        self.assertEqual(len(list((proot / "docs/current/05 - Product Features/custom-svc").iterdir())), 5)

        self.assertEqual(run_tool(NF_MOD, ["mini-custom", "--mini", "--root", str(proot)])[0], 0)
        self.assertEqual([p.name for p in (proot / "docs/current/05 - Product Features/005-mini-custom").iterdir()], ["1. Mini Spec.md"])

        self.assertEqual(run_tool(NF_MOD, ["mini-web", "--mini", "--preset", "web-api", "--root", str(proot)])[0], 0)
        self.assertIn("src/api/handlers/", (proot / "docs/current/05 - Product Features/006-mini-web/1. Mini Spec.md").read_text(encoding="utf-8"))

        # Clean up non-stamped draft fixtures before running full-vault stamp-spec.py checks
        for extra_d in ("002-billing", "003-sync-cli", "004-triage-bot", "custom-svc", "005-mini-custom", "006-mini-web"):
            shutil.rmtree(proot / "docs/current/05 - Product Features" / extra_d)

        # Tier M security-hardening -> Tier L --supersede promotion
        # Note: after deleting 002..006, next auto-seq after 001-auth is 002-sec-auth -> 003-sec-auth!
        self.assertEqual(run_tool(NF_MOD, ["sec-auth", "--mini", "--preset", "security-hardening", "--root", str(proot)])[0], 0)
        sec_mini = proot / "docs/current/05 - Product Features/002-sec-auth/1. Mini Spec.md"
        self.assertIn("SEC-xx", sec_mini.read_text(encoding="utf-8"))
        sec_mini.write_text(sec_mini.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        self.assertEqual(run_tool(STAMP_MOD, ["002-sec-auth", "--by", "sec-lead", "--evidence", "SEC-1", "--root", str(proot)])[0], 0)

        self.assertNotEqual(run_tool(NF_MOD, ["sec-auth", "--preset", "security-hardening", "--root", str(proot)])[0], 0)
        rc_sup_nf, out_sup_nf, _ = run_tool(
            NF_MOD, ["sec-auth", "--supersede", "002-sec-auth", "--preset", "security-hardening", "--root", str(proot)]
        )
        self.assertEqual(rc_sup_nf, 0)
        self.assertIn("/sdd-analyze", out_sup_nf)
        sec_full = proot / "docs/current/05 - Product Features/003-sec-auth"
        for sf in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            p = sec_full / sf
            p.write_text(p.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        self.assertEqual(run_tool(STAMP_MOD, ["003-sec-auth", "--by", "sec-lead", "--evidence", "SEC-2", "--root", str(proot)])[0], 0)
        self.assertEqual(parse_frontmatter(sec_mini.read_text(encoding="utf-8"))["status"], "superseded")
        rc_dead, _, err_dead = run_tool(NF_MOD, ["sec-auth", "--supersede", "002-sec-auth", "--root", str(proot)])
        self.assertNotEqual(rc_dead, 0)
        self.assertIn("already superseded or archived", err_dead)

        # export-tasks.py
        rc_ed, _, err_ed = run_tool(EXP_MOD, [str(f_auth), "--root", str(proot)])
        self.assertNotEqual(rc_ed, 0)
        self.assertIn("--allow-draft", err_ed)

        for sf in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            p = f_auth / sf
            p.write_text(p.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")
        t_p = f_auth / "4. Tasks.md"
        t_p.write_text(
            re.sub(
                r"^\| T-01 \|.*$",
                "| T-01 | done | no | - | AC-01 | `src/auth/model.py` | Completed auth model | `pytest` |\n"
                "| T-02 | todo | no | T-01 | AC-01 | `src/auth/api.py` | Wire login endpoint | `pytest` |\n"
                "| T-03 | todo | no | T-02 | - | `docs/api.md` | Sync API note | `python3 -B tools/validate-docs.py` |",
                t_p.read_text(encoding="utf-8"),
                flags=re.M,
            ),
            encoding="utf-8",
        )
        self.assertEqual(run_tool(STAMP_MOD, ["001-auth", "--by", "lead", "--evidence", "PR-101", "--root", str(proot)])[0], 0)

        rc_ej, out_ej, _ = run_tool(EXP_MOD, [str(f_auth), "--format", "json", "--root", str(proot)])
        self.assertEqual(rc_ej, 0)
        payload = json.loads(out_ej)
        self.assertEqual([t["task_id"] for t in payload["tasks"]], ["T-02", "T-03"])
        self.assertEqual(payload["tasks"][0]["title"], "[001-auth][T-02] Wire login endpoint")

        rc_eall, out_eall, _ = run_tool(EXP_MOD, [str(f_auth), "--include-done", "--format", "json", "--root", str(proot)])
        self.assertEqual(rc_eall, 0)
        self.assertEqual([t["task_id"] for t in json.loads(out_eall)["tasks"]], ["T-01", "T-02", "T-03"])

        rc_emd, out_emd, _ = run_tool(EXP_MOD, [str(f_auth), "--format", "markdown", "--root", str(proot)])
        self.assertEqual(rc_emd, 0)
        self.assertIn("- Related AC: `-`", out_emd)
        self.assertNotIn("AC--", out_emd)

        rc_egh, out_egh, _ = run_tool(EXP_MOD, [str(f_auth), "--format", "gh-commands", "--repo", "acme/demo", "--root", str(proot)])
        self.assertEqual(rc_egh, 0)
        self.assertIn("[001-auth][T-02] Wire login endpoint", out_egh)

        self.assertNotEqual(run_tool(EXP_MOD, [str(f_auth), "--apply-gh", "--root", str(proot)])[0], 0)
        self.assertNotEqual(run_tool(EXP_MOD, [str(f_auth), "--label", "bad,label", "--root", str(proot)])[0], 0)

        mock_dir = self.make_empty_dir("mock-gh")
        gh_script = mock_dir / "gh"
        store_file = mock_dir / "store.json"
        log_file = mock_dir / "gh.log"
        store_file.write_text("[]\n", encoding="utf-8")
        log_file.write_text("", encoding="utf-8")
        gh_script.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "from pathlib import Path\n"
            "store = Path(os.environ['MOCK_GH_STORE'])\n"
            "log = Path(os.environ['MOCK_GH_LOG'])\n"
            "with log.open('a', encoding='utf-8') as fh:\n"
            "    fh.write(' '.join(sys.argv[1:]) + '\\n')\n"
            "args = sys.argv[1:]\n"
            "if args[:2] == ['issue', 'list']:\n"
            "    print(store.read_text(encoding='utf-8'))\n"
            "    sys.exit(0)\n"
            "if args[:2] == ['issue', 'create']:\n"
            "    title = args[args.index('--title') + 1]\n"
            "    items = json.loads(store.read_text(encoding='utf-8'))\n"
            "    num = len(items) + 1\n"
            "    url = f'https://example.invalid/acme/demo/issues/{num}'\n"
            "    items.append({'number': num, 'title': title, 'url': url})\n"
            "    store.write_text(json.dumps(items), encoding='utf-8')\n"
            "    print(url)\n"
            "    sys.exit(0)\n"
            "sys.exit(1)\n",
            encoding="utf-8",
        )
        gh_script.chmod(0o755)
        old_env = os.environ.copy()
        os.environ["MOCK_GH_STORE"] = str(store_file)
        os.environ["MOCK_GH_LOG"] = str(log_file)
        os.environ["PATH"] = f"{mock_dir}:{old_env.get('PATH', '')}"
        try:
            rc_g1, out_g1, err_g1 = run_tool(
                EXP_MOD, [str(f_auth), "--apply-gh", "--repo", "acme/demo", "--label", "sdd", "--root", str(proot)]
            )
            self.assertEqual(rc_g1, 0, err_g1)
            self.assertIn("CREATED: [001-auth][T-02]", out_g1)
            self.assertIn("CREATED: [001-auth][T-03]", out_g1)

            rc_g2, out_g2, err_g2 = run_tool(
                EXP_MOD, [str(f_auth), "--apply-gh", "--repo", "acme/demo", "--root", str(proot)]
            )
            self.assertEqual(rc_g2, 0, err_g2)
            self.assertIn("SKIP: [001-auth][T-02] already exists", out_g2)
            self.assertEqual(len(json.loads(store_file.read_text(encoding="utf-8"))), 2)
            gh_logs = log_file.read_text(encoding="utf-8").splitlines()
            self.assertEqual(sum(1 for ln in gh_logs if ln.startswith("issue list ")), 2)
            self.assertTrue(any("--json number,title,state,url" in ln for ln in gh_logs))
        finally:
            os.environ.clear()
            os.environ.update(old_env)

    def test_v072_zero_draft_commit_and_squash_merge_e2e(self) -> None:
        """v0.7.2 RT-01 + RT-02 + Session 2 Q1 + Session 3 Q1: 0-draft-commit Tier M & Tier L + Squash-Merge HEAD~1...HEAD."""
        repo = self.clone_golden("v072-squash", with_templates=True)
        git_run(repo, "checkout", "-qb", "feat/001-quick-pay")
        self.assertEqual(run_tool(NF_MOD, ["quick-pay", "--mini", "--root", str(repo)])[0], 0)
        mini_p = repo / "docs/current/05 - Product Features/001-quick-pay/1. Mini Spec.md"
        mini_txt = (
            mini_p.read_text(encoding="utf-8")
            .replace("- [ ]", "- [x]")
            .replace("`src/example/`", "`src/pay.py`")
            .replace(
                "- Affected modules, routes, jobs, schemas, or integrations:",
                "- Affected modules, routes, jobs, schemas, or integrations: `src/pay.py`\n- [ ] Telemetry hook added.",
            )
        )
        mini_p.write_text(mini_txt, encoding="utf-8")

        rc_sm, _, err_sm = run_tool(STAMP_MOD, ["001-quick-pay", "--by", "lead", "--evidence", "PR-1", "--root", str(repo)])
        self.assertEqual(rc_sm, 0, err_sm)
        fm_m = parse_frontmatter(mini_p.read_text(encoding="utf-8"))
        self.assertEqual(fm_m["source_revision"], "self")
        self.assertRegex(fm_m["contract_sha256"], r"^[0-9a-f]{64}$")

        # Pre-commit dirty working tree (0 draft commits): both --task T-01 and pack-wide pass!
        (repo / "src").mkdir()
        (repo / "src/pay.py").write_text("def charge(c: int) -> bool:\n    return c > 0\n", encoding="utf-8")
        self.assertEqual(validate_owned_paths_diff(repo, feature_arg="001-quick-pay", task_id="T-01"), [])
        self.assertEqual(validate_owned_paths_diff(repo, feature_arg="001-quick-pay"), [])

        (repo / "src/rogue.py").write_text("x = 1\n", encoding="utf-8")
        self.expect_fail(lambda: validate_owned_paths_diff(repo, feature_arg="001-quick-pay", task_id="T-01"), "src/rogue.py")
        self.expect_fail(lambda: validate_owned_paths_diff(repo, feature_arg="001-quick-pay"), "src/rogue.py")
        (repo / "src/rogue.py").unlink()

        mini_p.write_text(
            mini_p.read_text(encoding="utf-8")
            .replace("| T-01 | todo |", "| T-01 | done |")
            .replace("- [ ] Telemetry hook added.", "- [x] Telemetry hook added."),
            encoding="utf-8",
        )
        self.assertEqual(
            run_tool(REC_MOD, ["--task-id", "T-01", "--feature", "001-quick-pay", "--task", "T-01", "--status", "completed", "--mode", "self", "--by", "dev", "--reviewer", "lead", "--root", str(repo), "--exec", "/bin/echo", "PAY_OK"])[0],
            0,
        )
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-qm", "feat: implement 001-quick-pay in single commit")

        # Simulate GitHub Squash-Merge onto main + delete branch + prune reflog/gc
        git_run(repo, "checkout", "-q", "main")
        git_run(repo, "merge", "--squash", "feat/001-quick-pay")
        git_run(repo, "commit", "-qm", "feat: 001-quick-pay (#1)")
        git_run(repo, "branch", "-D", "-q", "feat/001-quick-pay")
        git_run(repo, "reflog", "expire", "--expire=now", "--all")

        rc_post_sq, _, err_post_sq = run_tool(
            VDOCS_MOD, ["--require-tasks", "--strict", "--check-owned-paths", "--feature", "001-quick-pay", "--root", str(repo)]
        )
        self.assertEqual(rc_post_sq, 0, err_post_sq)
        self.assertEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(repo)])[0], 0)

        clone_dir = self.make_empty_dir("fresh-clone") / "clone"
        subprocess.run(["git", "clone", "-q", f"file://{repo}", str(clone_dir)], check=True)
        self.assertEqual(run_tool(VDOCS_MOD, ["--require-tasks", "--strict", "--root", str(clone_dir)])[0], 0)
        self.assertEqual(run_tool(VTE_MOD, ["--require-completed", "--root", str(clone_dir)])[0], 0)

    def test_v072_zero_draft_commit_and_squash_merge_tier_l(self) -> None:
        """v0.7.2 RT-01 + Session 2 Q1 + Session 3 Q1: Tier L (1..4) 0-draft-commit + convergence + rogue Squash-Merge HEAD~1...HEAD failure."""
        repo = self.clone_golden("v072-tier-l")
        git_run(repo, "checkout", "-qb", "feat/002-tier-l")
        feat_l = repo / "docs/current/05 - Product Features/002-tier-l"
        write_valid_pack(
            feat_l,
            fm=DRAFT_FM,
            tasks_rows="| T-01 | todo | no | - | AC-01, AC-02 | `src/tier_l/` | Tier L slice | `pytest` |\n",
        )
        rc_sl, _, err_sl = run_tool(STAMP_MOD, ["002-tier-l", "--by", "lead", "--evidence", "PR-2", "--root", str(repo)])
        self.assertEqual(rc_sl, 0, err_sl)
        for sf in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            fm_sf = parse_frontmatter((feat_l / sf).read_text(encoding="utf-8"))
            self.assertEqual(fm_sf["source_revision"], "self")
            self.assertRegex(fm_sf["contract_sha256"], r"^[0-9a-f]{64}$")

        (repo / "src/tier_l").mkdir(parents=True)
        (repo / "src/tier_l/service.py").write_text("ok = True\n", encoding="utf-8")
        self.assertEqual(validate_owned_paths_diff(repo, feature_arg="002-tier-l", task_id="T-01"), [])
        self.assertEqual(validate_owned_paths_diff(repo, feature_arg="002-tier-l"), [])

        (feat_l / "2. Tech Spec.md").write_text(
            (feat_l / "2. Tech Spec.md").read_text(encoding="utf-8").replace("- [ ] Rollout metric wired.", "- [x] Rollout metric wired."),
            encoding="utf-8",
        )
        (feat_l / "3. QA Spec.md").write_text(
            (feat_l / "3. QA Spec.md").read_text(encoding="utf-8").replace("Pending execution.", "- QA-01 & QA-02: PASS (`task-evidence/`)."),
            encoding="utf-8",
        )
        (feat_l / "4. Tasks.md").write_text(
            (feat_l / "4. Tasks.md").read_text(encoding="utf-8").replace("| T-01 | todo |", "| T-01 | done |"),
            encoding="utf-8",
        )
        self.assertEqual(validate_owned_paths_diff(repo, feature_arg="002-tier-l"), [])

        # Sneak src/rogue.py into Squash-Merge commit M1 onto main -> automatic HEAD~1...HEAD MUST FAIL!
        (repo / "src/rogue.py").write_text("sneaky = True\n", encoding="utf-8")
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-qm", "feat: tier-l with sneaky rogue")
        git_run(repo, "checkout", "-q", "main")
        git_run(repo, "merge", "--squash", "feat/002-tier-l")
        git_run(repo, "commit", "-qm", "feat: 002-tier-l squash (#2)")

        rc_sq_rogue, _, err_sq_rogue = run_tool(
            VDOCS_MOD, ["--require-tasks", "--strict", "--check-owned-paths", "--feature", "002-tier-l", "--root", str(repo)]
        )
        self.assertNotEqual(rc_sq_rogue, 0)
        self.assertIn("src/rogue.py", err_sq_rogue)

    def test_v072_contract_preimage_antiforgery_and_dirty_amend_guards(self) -> None:
        """v0.7.2 RT-01 + RT-02 + Session 3 Q1: preimage locks, H3 ban in Validation evidence, archived self, anti-forgery, dirty --amend."""
        repo = self.clone_golden("v072-preimage")
        old_sup_feat = repo / "docs/current/05 - Product Features/000-old"
        write_mini_spec(
            old_sup_feat,
            fm=APPROVED_FM.replace(
                "status: approved\n",
                'status: superseded\nsuperseded_by: "05 - Product Features/001-lock-l/1. Product Spec.md"\n',
            ),
        )
        feat = repo / "docs/current/05 - Product Features/001-lock-l"
        write_valid_pack(
            feat,
            fm=DRAFT_FM,
            tasks_rows="| T-01 | todo | no | - | AC-01, AC-02 | `src/owned/` | Initial summary | `pytest tests/owned` |\n",
        )
        # Keep 000-old draft during initial stamp of 001-lock-l, then mark 000-old superseded for the supersedes-injection test
        shutil.rmtree(old_sup_feat)
        self.assertEqual(run_tool(STAMP_MOD, ["001-lock-l", "--by", "lead", "--evidence", "PR-10", "--at", "2026-11-19", "--root", str(repo)])[0], 0)
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-qm", "approve 001-lock-l")

        write_mini_spec(
            old_sup_feat,
            fm=APPROVED_FM.replace(
                "status: approved\n",
                'status: superseded\nsuperseded_by: "05 - Product Features/001-lock-l/1. Product Spec.md"\n',
            ),
        )

        # Every immutable contract region fails BOTH strict=False and strict=True when edited post-approval!
        mutations: list[tuple[Path, str, str, str]] = [
            (feat / "1. Product Spec.md", "owner: engineering", "owner: attacker", "contract_sha256 mismatch"),
            (feat / "1. Product Spec.md", "status: approved\n", 'status: approved\nsupersedes: "05 - Product Features/000-old"\n', "contract_sha256 mismatch"),
            (feat / "1. Product Spec.md", "Session issued", "Tampered AC", "contract_sha256 mismatch"),
            (feat / "4. Tasks.md", "Initial summary", "Tampered summary", "contract_sha256 mismatch"),
            (feat / "4. Tasks.md", "`src/owned/`", "`src/owned/, src/extra/`", "contract_sha256 mismatch"),
            (feat / "4. Tasks.md", "`pytest tests/owned`", "`echo bypassed`", "contract_sha256 mismatch"),
            (feat / "4. Tasks.md", "Keep slices small and atomic.", "Injected non-table prose under Execution tasks.", "contract_sha256 mismatch"),
            (feat / "3. QA Spec.md", "Pending execution.", "### Injected H3 Subheading\nSneaky text.", "subheadings are forbidden"),
        ]
        for spec_p, old_s, new_s, expected_err in mutations:
            orig_txt = spec_p.read_text(encoding="utf-8")
            spec_p.write_text(orig_txt.replace(old_s, new_s, 1), encoding="utf-8")
            for strict_flag in (False, True):
                self.expect_fail(lambda sf=strict_flag, sp=spec_p: validate_clarify_gate(repo, [sp], strict=sf), expected_err)
            spec_p.write_text(orig_txt, encoding="utf-8")
        shutil.rmtree(old_sup_feat)

        # Silent contract_sha256 recomputation keeping historical (approved_by, approved_at, approval_evidence) fails anti-forgery!
        p4 = feat / "4. Tasks.md"
        orig_p4 = p4.read_text(encoding="utf-8")
        forged_body = orig_p4.replace("`src/owned/`", "`src/owned/, src/forged/`")
        old_csha = parse_frontmatter(orig_p4)["contract_sha256"]
        forged_csha = compute_contract_sha256("4. Tasks.md", p4.relative_to(repo), forged_body)
        p4.write_text(forged_body.replace(old_csha, forged_csha), encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(repo, [p4], strict=False), "anti-forgery check failed")
        p4.write_text(orig_p4, encoding="utf-8")

        # status: archived on self spec validates contract_sha256 (passes intact, fails when tampered)
        arch_feat = repo / "docs/current/05 - Product Features/002-arch-self"
        write_mini_spec(arch_feat, fm=DRAFT_FM)
        self.assertEqual(run_tool(STAMP_MOD, ["002-arch-self", "--by", "lead", "--evidence", "PR-11", "--root", str(repo)])[0], 0)
        arch_p = arch_feat / "1. Mini Spec.md"
        arch_txt = arch_p.read_text(encoding="utf-8").replace("status: approved", "status: archived", 1)
        arch_p.write_text(arch_txt, encoding="utf-8")
        validate_clarify_gate(repo, [arch_p], strict=True)
        arch_p.write_text(arch_txt.replace("200 OK", "500 Tampered"), encoding="utf-8")
        self.expect_fail(lambda: validate_clarify_gate(repo, [arch_p], strict=False), "contract_sha256 mismatch")
        shutil.rmtree(arch_feat)

        # Dirty working-tree stamp-spec.py --amend on a previously committed self pack MUST fail --check-owned-paths until committed,
        # AND committing an amendment never erases an earlier committed out-of-scope file on the feature branch!
        git_run(repo, "checkout", "-qb", "feat/001-lock-l")
        (repo / "src").mkdir()
        (repo / "src/earlier_rogue.py").write_text("rogue = 1\n", encoding="utf-8")
        git_run(repo, "add", "src/earlier_rogue.py")
        git_run(repo, "commit", "-qm", "earlier rogue commit on branch")

        p4.write_text(orig_p4.replace("`src/owned/`", "`src/owned/, src/amended/`"), encoding="utf-8")
        self.assertEqual(run_tool(STAMP_MOD, ["001-lock-l", "--by", "lead", "--evidence", "PR-12", "--amend", "--root", str(repo)])[0], 0)
        self.expect_fail(
            lambda: validate_owned_paths_diff(repo, feature_arg="001-lock-l"),
            "commit the approved spec pack before running --check-owned-paths",
        )

        git_run(repo, "commit", "-qam", "commit amended self pack")
        self.expect_fail(lambda: validate_owned_paths_diff(repo, feature_arg="001-lock-l"), "src/earlier_rogue.py")

    def test_v072_monotonic_multi_amend_and_head_sha_mode_separation(self) -> None:
        """v0.7.2 RT-03 + Session 2 Q2 + Session 3 Q2: 2nd & 3rd same-day --amend monotonic UTC + self <-> head-sha mode switch."""
        repo = self.clone_golden("v072-monotonic")
        feat = repo / "docs/current/05 - Product Features/001-multi-amend"
        write_valid_pack(
            feat,
            fm=DRAFT_FM,
            tasks_rows="| T-01 | todo | no | - | AC-01, AC-02 | `src/v1/` | Slice v1 | `pytest` |\n",
        )
        self.assertEqual(run_tool(STAMP_MOD, ["001-multi-amend", "--by", "lead", "--evidence", "PR-1", "--root", str(repo)])[0], 0)
        git_run(repo, "add", ".")
        git_run(repo, "commit", "-qm", "initial approval")

        timestamps: list[str] = []
        for idx in (1, 2, 3):
            p4 = feat / "4. Tasks.md"
            p4.write_text(p4.read_text(encoding="utf-8").replace(f"Slice v{idx}", f"Slice v{idx + 1}"), encoding="utf-8")
            rc, _, err = run_tool(STAMP_MOD, ["001-multi-amend", "--by", "lead", "--evidence", "PR-1", "--amend", "--root", str(repo)])
            self.assertEqual(rc, 0, err)
            ats = {
                parse_frontmatter((feat / n).read_text(encoding="utf-8"))["approved_at"]
                for n in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md")
            }
            self.assertEqual(len(ats), 1, f"Divergent approved_at across Tier L pack: {ats}")
            ts = next(iter(ats))
            self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            timestamps.append(ts)
            git_run(repo, "commit", "-qam", f"amend {idx}")

        self.assertLess(timestamps[0], timestamps[1])
        self.assertLess(timestamps[1], timestamps[2])

        # Downgrade self -> head-sha strips contract_sha256 cleanly; upgrade head-sha -> self restores contract_sha256!
        rc_down, _, err_down = run_tool(
            STAMP_MOD, ["001-multi-amend", "--by", "lead", "--evidence", "PR-2", "--amend", "--mode", "head-sha", "--root", str(repo)]
        )
        self.assertEqual(rc_down, 0, err_down)
        head_sha = git_run(repo, "rev-parse", "HEAD")
        for n in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            raw_n = (feat / n).read_text(encoding="utf-8")
            self.assertNotIn("contract_sha256", raw_n)
            self.assertEqual(parse_frontmatter(raw_n)["source_revision"], head_sha)
        git_run(repo, "commit", "-qam", "downgrade to head-sha")

        rc_up, _, err_up = run_tool(
            STAMP_MOD, ["001-multi-amend", "--by", "lead", "--evidence", "PR-3", "--amend", "--mode", "self", "--root", str(repo)]
        )
        self.assertEqual(rc_up, 0, err_up)
        for n in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
            fm_n = parse_frontmatter((feat / n).read_text(encoding="utf-8"))
            self.assertEqual(fm_n["source_revision"], "self")
            self.assertRegex(fm_n["contract_sha256"], r"^[0-9a-f]{64}$")

    def test_v072_hardened_git_cat_file_batch_and_symlink_artifact_rejection(self) -> None:
        """v0.7.2 RT-04: GitCatFileBatch spec guard, non-blob drain without desync, missing spaced path, missing git warn, 120000 artifact."""
        repo = self.clone_golden("v072-gitbatch")
        with GitCatFileBatch(repo) as batch:
            for bad_spec in ("", '"HEAD:README.md', "HEAD:README.md\nHEAD:AGENTS.md", "HEAD:a\rb", "HEAD:a\x00b"):
                with self.assertRaises(ValueError):
                    batch.check(bad_spec)
                with self.assertRaises(ValueError):
                    batch.read_blob(bad_spec)

            self.assertIsNone(batch.read_blob("HEAD^{tree}"))
            self.assertEqual(batch.read_blob("HEAD:README.md"), b"base\n")

            missing_spaced = "HEAD:docs/current/05 - Product Features/001-x/1. Mini Spec.md"
            self.assertIsNone(batch.check(missing_spaced))
            self.assertIsNone(batch.read_blob(missing_spaced))
            chk = batch.check("HEAD:README.md")
            self.assertIsNotNone(chk)
            assert chk is not None
            self.assertEqual(chk[1:], ("blob", 5))
            self.assertEqual(batch.tree_entry_mode("HEAD", "README.md"), "100644")

        # Missing git binary warning (strict=False) vs error (strict=True)
        mini = repo / "docs/current/05 - Product Features/001-nogit"
        write_mini_spec(mini, fm=DRAFT_FM)
        self.assertEqual(run_tool(STAMP_MOD, ["001-nogit", "--by", "lead", "--evidence", "PR-1", "--root", str(repo)])[0], 0)
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = "/nonexistent"
        try:
            warns = validate_clarify_gate(repo, [mini / "1. Mini Spec.md"], strict=False)
            self.assertTrue(any("git binary unavailable" in w for w in warns), warns)
            self.expect_fail(lambda: validate_clarify_gate(repo, [mini / "1. Mini Spec.md"], strict=True), "git binary unavailable")
        finally:
            os.environ["PATH"] = old_path
        shutil.rmtree(mini)

        # Committed 120000 symlink artifact rejected both when symlink is on disk AND via Git ls-tree mode 120000 in history!
        (repo / "real-target.log").write_text("ok\n", encoding="utf-8")
        art_dir = repo / "task-evidence/artifacts"
        art_dir.mkdir(parents=True, exist_ok=True)
        sym_art = art_dir / "sym.log"
        sym_art.symlink_to("../../real-target.log")
        git_run(repo, "add", "real-target.log", "task-evidence/artifacts/sym.log")
        git_run(repo, "commit", "-qm", "commit symlink artifact")
        sym_rev = git_run(repo, "rev-parse", "HEAD")
        with GitCatFileBatch(repo) as batch:
            self.assertEqual(batch.tree_entry_mode("HEAD", "task-evidence/artifacts/sym.log"), "120000")
            raw_sym_blob = batch.read_blob("HEAD:task-evidence/artifacts/sym.log")
            assert raw_sym_blob is not None
        sym_blob_sha = hashlib.sha256(raw_sym_blob).hexdigest()

        ev_hex = repo / "task-evidence/01-sym-hex.md"
        ev_hex.write_text(
            "---\n"
            "status: completed\n"
            "task_id: sym-hex\n"
            "recorded_at: 2026-11-19\n"
            "recorded_by: dev\n"
            f"source_revision: {sym_rev}\n"
            "completed_at: 2026-11-19T00:00:00Z\n"
            "reviewer: lead\n"
            "environment: local/dev\n"
            f"output_artifact_sha256: {sym_blob_sha}\n"
            "output_artifact_path: task-evidence/artifacts/sym.log\n"
            "---\n"
            "# Sym\n\n| AC-01 | x | y | PASS / 0 |\n",
            encoding="utf-8",
        )
        # (a) Symlink still on disk -> rejected lexically before Git read
        rc_disk_sym, _, err_disk_sym = run_tool(VTE_MOD, ["--require-completed", "--root", str(repo)])
        self.assertNotEqual(rc_disk_sym, 0)
        self.assertIn("symlink", err_disk_sym.lower())

        # (b) Replace symlink on disk with regular file in C2 -> 40-hex historical check catches mode 120000 via GitCatFileBatch.tree_entry_mode!
        sym_art.unlink()
        sym_art.write_text("regular replacement\n", encoding="utf-8")
        git_run(repo, "add", "task-evidence/artifacts/sym.log")
        git_run(repo, "commit", "-qm", "replace symlink on disk with regular file")
        rc_hist_sym, _, err_hist_sym = run_tool(VTE_MOD, ["--require-completed", "--root", str(repo)])
        self.assertNotEqual(rc_hist_sym, 0)
        self.assertIn("120000", err_hist_sym)

    def test_v072_sdd_core_isolation_version_guard_and_cli_smoke(self) -> None:
        """v0.7.2 RT-05 + RT-06 + RT-10: missing/outdated _sdd_core.py across all 7 tools, standalone isolation, O_NOFOLLOW read_markdown, CLI smoke."""
        # RT-10: read_markdown refuses symlinks via O_NOFOLLOW
        tmp = self.make_empty_dir("nofollow")
        real_f = tmp / "real.md"
        real_f.write_text("# Real\n", encoding="utf-8")
        sym_f = tmp / "sym.md"
        sym_f.symlink_to(real_f)
        self.expect_fail(lambda: read_markdown(sym_f), "symlink refused")

        # RT-06: Missing or outdated _sdd_core.py exits 1 with clean remediation across all 7 tools
        iso_root = self.clone_golden("iso-tools", with_templates=True)
        iso_tools = iso_root / "tools"
        shutil.copytree(TOOLS_DIR, iso_tools)
        seven_tools = (
            "docs_validation.py",
            "validate-docs.py",
            "stamp-spec.py",
            "record-evidence.py",
            "validate-task-evidence.py",
            "new-feature.py",
            "export-tasks.py",
        )

        def _assert_seven_tools_guard(expected_token: str) -> None:
            saved_path = list(sys.path)
            saved_mods = dict(sys.modules)
            for tname in seven_tools:
                err_b = io.StringIO()
                sys.path[:] = [str(iso_tools), *[p for p in saved_path if p != str(TOOLS_DIR)]]
                sys.modules.pop("_sdd_core", None)
                sys.modules.pop("docs_validation", None)
                try:
                    with contextlib.redirect_stderr(err_b):
                        with self.assertRaises(SystemExit) as cm:
                            runpy.run_path(str(iso_tools / tname), run_name="__main__")
                    self.assertEqual(cm.exception.code, 1, tname)
                    stderr_txt = err_b.getvalue()
                    self.assertIn(expected_token, stderr_txt, tname)
                    self.assertIn("setup.sh --update --force", stderr_txt, tname)
                    self.assertNotIn("Traceback", stderr_txt, tname)
                finally:
                    sys.path[:] = saved_path
                    sys.modules.clear()
                    sys.modules.update(saved_mods)

        (iso_tools / "_sdd_core.py").unlink()
        _assert_seven_tools_guard("_sdd_core.py")

        (iso_tools / "_sdd_core.py").write_text("SDD_CORE_API_VERSION = 0\n", encoding="utf-8")
        _assert_seven_tools_guard("SDD_CORE_API_VERSION")

        # Standalone isolation when docs_validation.py is deleted + 1 real subprocess.run CLI smoke test per tools/*.py script!
        (iso_tools / "_sdd_core.py").write_text((TOOLS_DIR / "_sdd_core.py").read_text(encoding="utf-8"), encoding="utf-8")
        (iso_tools / "docs_validation.py").unlink()

        subprocess.run(
            [sys.executable, "-B", str(iso_tools / "new-feature.py"), "standalone-mini", "--mini", "--root", str(iso_root)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                sys.executable, "-B", str(iso_tools / "record-evidence.py"),
                "--task-id", "tier-s-fix",
                "--status", "completed",
                "--mode", "self",
                "--by", "dev",
                "--reviewer", "lead",
                "--root", str(iso_root),
                "--exec", "/bin/echo", "tier_s_ok",
            ],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [sys.executable, "-B", str(iso_tools / "validate-task-evidence.py"), "--allow-working-tree", "--root", str(iso_root)],
            check=True,
            stdout=subprocess.DEVNULL,
        )

        res_st_nodv = subprocess.run(
            [sys.executable, "-B", str(iso_tools / "stamp-spec.py"), "001-standalone-mini", "--by", "a", "--evidence", "b", "--root", str(iso_root)],
            capture_output=True,
            text=True,
        )
        self.assertEqual(res_st_nodv.returncode, 1)
        self.assertIn("docs_validation.py", res_st_nodv.stderr)
        self.assertNotIn("Traceback", res_st_nodv.stderr)

        # Restore docs_validation.py and run CLI smoke tests for remaining scripts
        (iso_tools / "docs_validation.py").write_text((TOOLS_DIR / "docs_validation.py").read_text(encoding="utf-8"), encoding="utf-8")
        mini_sp = iso_root / "docs/current/05 - Product Features/001-standalone-mini/1. Mini Spec.md"
        mini_sp.write_text(mini_sp.read_text(encoding="utf-8").replace("- [ ]", "- [x]"), encoding="utf-8")

        subprocess.run([sys.executable, "-B", str(iso_tools / "_sdd_core.py")], check=True)
        subprocess.run([sys.executable, "-B", str(iso_tools / "docs_validation.py")], check=True)
        subprocess.run(
            [sys.executable, "-B", str(iso_tools / "stamp-spec.py"), "001-standalone-mini", "--by", "lead", "--evidence", "PR-1", "--root", str(iso_root)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [sys.executable, "-B", str(iso_tools / "validate-docs.py"), "--require-tasks", "--strict", "--root", str(iso_root)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
        subprocess.run(
            [sys.executable, "-B", str(iso_tools / "export-tasks.py"), "docs/current/05 - Product Features/001-standalone-mini", "--root", str(iso_root)],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def _iter_cases(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    cases: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            cases.extend(_iter_cases(item))
        else:
            cases.append(item)
    return cases


class _ParallelDocsAndToolsSuite(unittest.TestSuite):
    """Runs isolated DocsAndToolsTest methods across subprocess workers sharing one golden fixture dir."""

    def run(self, result: unittest.TestResult, debug: bool = False) -> unittest.TestResult:
        cases = list(self)
        if debug or len(cases) <= 1 or os.environ.get("_AI_TPL_SERIAL_WORKER") == "1":
            return super().run(result, debug=debug)

        DocsAndToolsTest.setUpClass()
        try:
            worker_env = os.environ.copy()
            worker_env["_AI_TPL_SERIAL_WORKER"] = "1"
            worker_env["_AI_TPL_SHARED_DOCSTOOLS_DIR"] = str(DocsAndToolsTest._shared_base)
            max_workers = min(len(cases), max(4, min(12, os.cpu_count() or 4)))

            def _exec_one(case: unittest.TestCase) -> tuple[unittest.TestCase, int, str, str]:
                target_id = f"tests.test_docs_and_tools.{case.__class__.__qualname__}.{case._testMethodName}"
                proc = subprocess.run(
                    [sys.executable, "-B", "-W", "error::ResourceWarning", "-m", "unittest", target_id],
                    cwd=ROOT,
                    env=worker_env,
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                )
                return case, proc.returncode, proc.stdout, proc.stderr

            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
                futures = [pool.submit(_exec_one, c) for c in cases]
                for fut in concurrent.futures.as_completed(futures):
                    case, rc, out, err = fut.result()
                    result.startTest(case)
                    try:
                        if rc == 0:
                            result.addSuccess(case)
                        else:
                            detail = f"Worker exited with code {rc} for {case.id()}:\n{out}\n{err}"
                            try:
                                raise AssertionError(detail)
                            except AssertionError:
                                result.addFailure(case, sys.exc_info())
                    finally:
                        result.stopTest(case)
                    if result.shouldStop:
                        break
        finally:
            DocsAndToolsTest.tearDownClass()
        return result


def load_tests(loader: unittest.TestLoader, standard_tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    if os.environ.get("_AI_TPL_SERIAL_WORKER") == "1":
        return standard_tests
    cases = _iter_cases(standard_tests)
    if len(cases) <= 1:
        return standard_tests
    return _ParallelDocsAndToolsSuite(cases)


if __name__ == "__main__":
    unittest.main()
