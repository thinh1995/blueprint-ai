#!/usr/bin/env python3
"""Fast static contract, release-matrix, CI-workflow, and context-diet unittest suite."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import contextlib
import importlib.util
import io
import tempfile
import unittest
from pathlib import Path
from types import ModuleType

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def _load_script_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, str(path))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StaticContractsTest(unittest.TestCase):
    """Port of validate-docs.sh static text guards + all 5 static validators + context diet."""

    def _require_text(self, rel_path: str, needle: str) -> None:
        content = (ROOT / rel_path).read_text(encoding="utf-8")
        self.assertIn(needle, content, f"Missing {needle!r} in {rel_path}")

    def test_static_text_and_ci_workflow_contracts(self) -> None:
        for spec_tpl in (
            "docs/templates/mini-spec-template/1. Mini Spec.md",
            "docs/templates/feature-spec-template/1. Product Spec.md",
            "docs/templates/feature-spec-template/2. Tech Spec.md",
            "docs/templates/feature-spec-template/3. QA Spec.md",
            "docs/templates/feature-spec-template/4. Tasks.md",
        ):
            for key in ("approved_by:", "approved_at:", "approval_evidence:", "source_revision:"):
                self._require_text(spec_tpl, key)

        self._require_text("docs/templates/3. Task Evidence Template.md", "Acceptance criteria and validation")
        self._require_text("docs/templates/3. Task Evidence Template.md", "output_artifact_path:")
        for agent_tok in (
            "Never invent file/line references",
            "untrusted data",
            "Do not introduce speculative abstractions",
            "Make surgical changes",
            "3-Tier SDD Routing",
            "Spec Amendment",
            "Contract Language Rule",
            "NEEDS CLARIFICATION",
            "Owned paths",
            "stamp-spec.py",
            "--check-owned-paths",
            "/sdd-review",
            "contract_sha256",
            "Secret-file read denylist",
            "--exec",
        ):
            self._require_text("AGENTS.md", agent_tok)

        self._require_text("adapters/cursor-agents.mdc", "alwaysApply: true")
        self._require_text("adapters/copilot-instructions.md", "AGENTS.md")
        self._require_text("docs/current/00 - Onboarding/3. AI Agent Workflow.md", "Simplicity first")
        self._require_text("docs/current/00 - Onboarding/3. AI Agent Workflow.md", "Surgical changes")
        self._require_text("docs/current/00 - Onboarding/3. AI Agent Workflow.md", "Spec-Driven Feature Prompts")
        self._require_text("docs/current/02 - Architecture/Generated Reference Inventory.md", "verified: false")
        self._require_text("docs/current/02 - Architecture/Generated Reference Inventory.md", "verified_at:")
        self._require_text("docs/current/01 - Overview/BA Foundation.md", "Stakeholders and RACI")
        self._require_text("docs/current/01 - Overview/BA Foundation.md", "Business rules catalogue")
        self._require_text("docs/current/08 - Diagram Standards/Diagram Standards.md", "diagram_format: mermaid")
        self._require_text(
            "docs/current/08 - Diagram Standards/Diagram Standards.md",
            "**Mermaid** là định dạng sơ đồ chuẩn duy nhất",
        )
        self._require_text("docs/current/08 - Diagram Standards/Diagram Standards.md", "```mermaid")
        self._require_text(
            "docs/templates/feature-spec-template/1. Product Spec.md",
            "Stakeholder, user stories, and use cases",
        )
        self._require_text("docs/templates/feature-spec-template/1. Product Spec.md", "## Traceability")
        self._require_text(
            "docs/templates/feature-spec-template/2. Tech Spec.md",
            "Tool permissions, timeout, retry, fallback",
        )
        self._require_text("docs/templates/feature-spec-template/3. QA Spec.md", "prompt injection")

        for sample_file in (
            "docs/templates/examples/ai-support-agent/1. Product Spec.md",
            "docs/templates/examples/ai-support-agent/2. Tech Spec.md",
            "docs/templates/examples/ai-support-agent/3. QA Spec.md",
            "docs/templates/examples/ai-support-agent/4. Tasks.md",
        ):
            self._require_text(sample_file, "status: example")

        self._require_text("docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md", "tools/validate-docs.py --require-tasks")
        self._require_text("docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md", "## 8. Review")
        self._require_text("docs/current/00 - Onboarding/2. Task Evidence.md", "source_revision: self")
        self._require_text("docs/current/02 - Architecture/Architecture.md", "## Brownfield security and tech-debt triage")
        self._require_text("docs/current/05 - Product Features/README.md", "## Anti-fragmentation and supersession lifecycle")
        self._require_text(
            "docs/current/06 - Infrastructure & Deployment/Infrastructure Spec.md",
            "Secrets management and security scanning",
        )
        self._require_text("docs/templates/examples/ai-support-agent/1. Product Spec.md", "```mermaid")
        self._require_text("docs/templates/examples/ai-support-agent/2. Tech Spec.md", "```mermaid")
        self._require_text("docs/templates/examples/ai-support-agent/2. Tech Spec.md", "sequenceDiagram")
        self._require_text("docs/templates/examples/ai-support-agent/2. Tech Spec.md", "stateDiagram-v2")
        self._require_text("docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md", "docs/templates")
        self._require_text("docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md", "tools/validate-docs.py")
        self._require_text("README.md", "--dry-run --update")
        self._require_text("docs/current/00 - Onboarding/1. Setup Guide.md", "RECOVERY.md")

        # Historical & current release acceptance matrices
        for matrix_rel, expected_ver in (
            ("docs/internal/acceptance-matrices/V3_ACCEPTANCE_MATRIX.md", "0.3.0"),
            ("docs/internal/acceptance-matrices/V4_ACCEPTANCE_MATRIX.md", "0.4.0"),
            ("docs/internal/acceptance-matrices/V5_ACCEPTANCE_MATRIX.md", "0.5.0"),
            ("docs/internal/acceptance-matrices/V5_1_ACCEPTANCE_MATRIX.md", "0.5.1"),
            ("docs/internal/acceptance-matrices/V6_ACCEPTANCE_MATRIX.md", "0.6.0"),
            ("docs/internal/acceptance-matrices/V6_1_ACCEPTANCE_MATRIX.md", "0.6.1"),
            ("docs/internal/acceptance-matrices/V7_ACCEPTANCE_MATRIX.md", "0.7.0"),
            ("docs/internal/acceptance-matrices/V7_1_ACCEPTANCE_MATRIX.md", "0.7.1"),
            ("docs/internal/acceptance-matrices/V7_2_ACCEPTANCE_MATRIX.md", "0.7.2"),
        ):
            self._require_text(matrix_rel, f"Release target: `{expected_ver}`")

        # CI workflow audit substrings + RT-09 zero-cache system-Chrome checks
        wf_rel = ".github/workflows/ai-template-validation.yml"
        wf_text = (ROOT / wf_rel).read_text(encoding="utf-8")
        for ci_tok in (
            "fetch-depth: 0",
            "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
            "actions/setup-node@949feb2413d6458794dcd2491c4babbbce0c15c1",
            "node-version: 22.14.0",
            "workflow_dispatch:",
            "concurrency:",
            "bash setup.sh --doctor",
            "tools/validate-task-evidence.py",
            "if: runner.os == 'Linux'",
            "PUPPETEER_SKIP_DOWNLOAD=true",
            "--ignore-scripts",
            "bash tests/render-mermaid.sh --extract-only",
        ):
            self.assertIn(ci_tok, wf_text, f"Missing {ci_tok!r} in {wf_rel}")
        self.assertNotIn("actions/cache", wf_text, "RT-09 forbids actions/cache in CI workflow")

    def test_all_five_static_python_validators_and_symlink_filter(self) -> None:
        v_docs = _load_script_module("_v_tpl_docs", TESTS_DIR / "validate-template-docs.py")
        v_skills = _load_script_module("_v_skills", TESTS_DIR / "validate-skills-contract.py")
        v_orch = _load_script_module("_v_orch", TESTS_DIR / "validate-orchestration-contract.py")
        v_deleg = _load_script_module("_v_deleg", TESTS_DIR / "validate-runtime-delegation-fixture.py")
        v_agy = _load_script_module("_v_agy", TESTS_DIR / "validate-antigravity-conformance-fixture.py")

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            v_docs.main()
            v_skills.validate_skills_contract(ROOT)
            v_skills.run_self_test()
            v_orch.main()
            v_deleg.main()
            v_agy.main()

        # RT-10: markdown_files() skips symlinks and docs/internal/
        with tempfile.TemporaryDirectory() as td:
            fake_docs = Path(td) / "docs"
            (fake_docs / "current").mkdir(parents=True)
            (fake_docs / "internal").mkdir(parents=True)
            real_md = fake_docs / "current/real.md"
            real_md.write_text("# Real\n", encoding="utf-8")
            (fake_docs / "internal/secret.md").write_text("# Internal\n", encoding="utf-8")
            sym_md = fake_docs / "current/sym.md"
            sym_md.symlink_to(real_md)
            found = v_docs.markdown_files(fake_docs)
            self.assertEqual(found, [real_md])

    def test_context_token_diet_and_installer_line_budget(self) -> None:
        agents_size = len((ROOT / "AGENTS.md").read_bytes())
        skill_paths = sorted((ROOT / "skills").glob("sdd-*/SKILL.md"))
        self.assertEqual(len(skill_paths), 9)
        max_skill = 0
        for sp in skill_paths:
            sz = len(sp.read_bytes())
            self.assertLessEqual(sz, 4950, f"{sp.relative_to(ROOT)} exceeds 4950-byte target ({sz} B)")
            self.assertLessEqual(sz, 5120, f"{sp.relative_to(ROOT)} exceeds 5120-byte hard cap ({sz} B)")
            max_skill = max(max_skill, sz)

        self.assertLessEqual(
            agents_bytes_plus := agents_size + max_skill,
            19000,
            f"Combined AGENTS.md + max SKILL.md ({agents_bytes_plus} B) exceeds 19000 B",
        )
        mdc_size = len((ROOT / "adapters/cursor-agents.mdc").read_bytes())
        self.assertLessEqual(mdc_size, 450, f"cursor-agents.mdc ({mdc_size} B) exceeds 450 B")

        setup_lines = len((ROOT / "setup.sh").read_text(encoding="utf-8").splitlines())
        self.assertLessEqual(setup_lines, 770, f"setup.sh ({setup_lines} lines) exceeds 770 lines")

        for adapter_rel in (
            "CLAUDE.md",
            "GEMINI.md",
            "QWEN.md",
            "adapters/copilot-instructions.md",
            "adapters/cursor-agents.mdc",
        ):
            self.assertNotIn(
                "3. AI Agent Workflow.md",
                (ROOT / adapter_rel).read_text(encoding="utf-8"),
            )


if __name__ == "__main__":
    unittest.main()
