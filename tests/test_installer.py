#!/usr/bin/env python3
"""Comprehensive < 4.5s unittest suite for lib/installer_lib.py, doctor, ownership, and upgrades."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import concurrent.futures
import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
ROOT = TESTS_DIR.parent
LIB_DIR = ROOT / "lib"
TOOLS_DIR = ROOT / "tools"
for _d in (LIB_DIR, TOOLS_DIR):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import installer_lib  # noqa: E402
from docs_validation import compute_contract_sha256  # noqa: E402

HISTORICAL_REFS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("v0.4.0", ("587c1c93dc073f6b05e485695bcf1e6ea85636b8^{commit}",)),
    ("v0.4.2", ("1127e26bd04844d4a9a07d85223a62d5c434fbfd^{commit}",)),
    ("v0.5.1", ("c8b389e7b9670ac1868f3711bc1174a94997f310^{commit}",)),
    ("v0.6.0", ("v0.6.0^{commit}",)),
    ("v0.6.1", ("v0.6.1^{commit}",)),
    ("v0.7.0", ("v0.7.0^{commit}", "5a38f149bb9d7f8b4912f1b7857847a9a5fbe45e^{commit}")),
    ("v0.7.1", ("v0.7.1^{commit}", "dd017be73cf5f8fba87fd7b72eb44c3451295168^{commit}")),
)


def run_lib(argv: list[str]) -> tuple[int, str, str]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with contextlib.redirect_stdout(out_buf), contextlib.redirect_stderr(err_buf):
        rc = installer_lib.main(argv)
    return rc, out_buf.getvalue(), err_buf.getvalue()


def resolve_git_commit(candidates: tuple[str, ...]) -> str:
    for ref in candidates:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "rev-parse", "--verify", ref],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout.strip()
    raise RuntimeError(f"Unable to resolve historical commit from {candidates}")


class InstallerLibAndUpgradesTest(unittest.TestCase):
    """Covers 100% of installer_lib.py subcommands, trust boundaries, and v0.4.0..v0.7.1 -> v0.7.2 upgrades."""

    _class_tmp: tempfile.TemporaryDirectory[str] | None = None
    _owns_class_tmp: bool = False
    _shared_base: Path
    archives: dict[str, Path]
    golden_installed: Path
    mock_bin: Path

    @classmethod
    def setUpClass(cls) -> None:
        shared_env = os.environ.get("_AI_TPL_SHARED_INSTALLER_DIR", "").strip()
        if shared_env:
            cls._owns_class_tmp = False
            cls._class_tmp = None
            base = Path(shared_env).resolve()
            cls._shared_base = base
            cls.archives = {label: base / f"archive-{label}" for label, _ in HISTORICAL_REFS}
            cls.mock_bin = base / "mock-bin"
            cls.golden_installed = base / "golden-installed"
            return

        cls._owns_class_tmp = True
        cls._class_tmp = tempfile.TemporaryDirectory(prefix="ai-tpl-installer-")
        base = Path(cls._class_tmp.name).resolve()
        cls._shared_base = base
        cls.archives = {}

        def _extract_one(item: tuple[str, tuple[str, ...]]) -> tuple[str, Path]:
            label, ref_cands = item
            sha = resolve_git_commit(ref_cands)
            dest = base / f"archive-{label}"
            dest.mkdir(parents=True)
            archive_proc = subprocess.Popen(
                ["git", "-C", str(ROOT), "archive", sha],
                stdout=subprocess.PIPE,
            )
            assert archive_proc.stdout is not None
            try:
                subprocess.run(["tar", "-x", "-C", str(dest)], stdin=archive_proc.stdout, check=True)
            finally:
                archive_proc.stdout.close()
                archive_proc.wait()
            return label, dest

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(HISTORICAL_REFS)) as pool:
            for label, dest in pool.map(_extract_one, HISTORICAL_REFS):
                cls.archives[label] = dest

        cls.mock_bin = base / "mock-bin"
        cls.mock_bin.mkdir()
        for cli in ("claude", "agy", "qwen", "opencode", "codex", "cursor-agent", "copilot"):
            p = cls.mock_bin / cli
            p.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
            p.chmod(0o755)

        cls.golden_installed = base / "golden-installed"
        cls.golden_installed.mkdir()
        subprocess.run(
            ["bash", str(ROOT / "setup.sh")],
            cwd=cls.golden_installed,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if cls._owns_class_tmp and cls._class_tmp is not None:
            cls._class_tmp.cleanup()
            cls._class_tmp = None

    def make_dir(self, name: str) -> Path:
        td = tempfile.TemporaryDirectory(prefix=f"ai-inst-{name}-")
        self.addCleanup(td.cleanup)
        return Path(td.name).resolve()

    def clone_installed(self, name: str) -> Path:
        dest = self.make_dir(name) / "proj"
        shutil.copytree(self.golden_installed, dest, symlinks=True)
        return dest

    def clone_source_template(self, name: str) -> Path:
        dest = self.make_dir(name) / "src-tpl"
        dest.mkdir(parents=True)
        for item in ("setup.sh", "template-paths.sh", "AGENTS.md", "CLAUDE.md", "GEMINI.md", "QWEN.md", "template-manifest.json"):
            shutil.copy2(ROOT / item, dest / item)
        for dname in ("lib", "tools", "adapters", "skills"):
            shutil.copytree(ROOT / dname, dest / dname)
        (dest / "task-evidence").mkdir()
        (dest / "task-evidence/.gitkeep").write_text("", encoding="utf-8")
        shutil.copytree(ROOT / "docs/current", dest / "docs/current")
        shutil.copytree(ROOT / "docs/templates", dest / "docs/templates")
        return dest

    def test_load_manifest_state_and_rel_path_hardening(self) -> None:
        """RT-10 + Session 3: tab-delimited load-manifest-state (57, 5, 1) + validate_rel_path & source manifest guards."""
        rc, out, err = run_lib(["load-manifest-state", str(ROOT)])
        self.assertEqual(rc, 0, err)
        counts: dict[str, int] = {}
        for line in out.splitlines():
            parts = line.split("\t")
            self.assertEqual(len(parts), 2, f"Expected 2 tab-delimited fields, got {parts!r}")
            counts[parts[0]] = counts.get(parts[0], 0) + 1
        self.assertEqual(counts, {"core": 57, "--with-advanced-docs": 5, "--with-legacy-agents": 1})

        # RT-10: validate_rel_path rejects '|', '\\', leading/trailing whitespace, control chars, traversal, empty
        for bad_rel in (
            "",
            None,
            " AGENTS.md",
            "AGENTS.md ",
            "\tAGENTS.md",
            "docs|bad.md",
            "docs\\bad.md",
            "docs/\nbad.md",
            "docs/\x00bad.md",
            "docs/\x7fbad.md",
            "/etc/passwd",
            "../escape",
            "docs/../escape.md",
            "docs/./bad.md",
            "docs//bad.md",
        ):
            with self.assertRaises(ValueError, msg=f"Accepted unsafe path {bad_rel!r}"):
                installer_lib.validate_rel_path(bad_rel)

        # Source manifest negative schema/overlap/unprofiled checks
        bad_tpl = self.clone_source_template("bad-manifest")
        m_path = bad_tpl / "template-manifest.json"
        orig_m = json.loads(m_path.read_text(encoding="utf-8"))

        mut1 = json.loads(json.dumps(orig_m))
        mut1["profiles"]["--with-legacy-agents"] = ["../../outside-target"]
        m_path.write_text(json.dumps(mut1), encoding="utf-8")
        self.assertEqual(run_lib(["load-manifest-state", str(bad_tpl)])[0], 1)

        mut2 = json.loads(json.dumps(orig_m))
        mut2["profiles"]["--with-legacy-agents"] = [".agents/AGENTS.md\n../outside"]
        m_path.write_text(json.dumps(mut2), encoding="utf-8")
        rc2, _, err2 = run_lib(["validate-source-manifest", str(bad_tpl)])
        self.assertEqual(rc2, 1)
        self.assertIn("control character", err2)

        mut3 = json.loads(json.dumps(orig_m))
        mut3["profiles"]["--with-advanced-docs"].append("docs/templates/1. Agent System Prompt Template.md")
        m_path.write_text(json.dumps(mut3), encoding="utf-8")
        rc3, _, err3 = run_lib(["validate-source-manifest", str(bad_tpl)])
        self.assertEqual(rc3, 1)
        self.assertIn("profile paths overlap", err3)

        mut4 = json.loads(json.dumps(orig_m))
        mut4["managed_paths"] = None
        m_path.write_text(json.dumps(mut4), encoding="utf-8")
        self.assertEqual(run_lib(["validate-source-manifest", str(bad_tpl)])[0], 1)

        m_path.write_text(json.dumps(orig_m), encoding="utf-8")
        (bad_tpl / "docs/current/unprofiled-fixture.md").write_text("# Unprofiled\n", encoding="utf-8")
        rc5, _, err5 = run_lib(["validate-source-manifest", str(bad_tpl)])
        self.assertEqual(rc5, 1)
        self.assertIn("not declared by a profile", err5)

    def test_isolated_trusted_tool_loader_and_doctor_rce_boundary(self) -> None:
        """RT-05 + v0.7.1 #13: isolated spec_from_file_location across $SRC_DIR snapshots & untrusted $DEST_DIR RCE block."""
        src_a = self.clone_source_template("src-a")
        src_b = self.clone_source_template("src-b")
        (src_a / "tools/_sdd_core.py").write_text(
            (src_a / "tools/_sdd_core.py").read_text(encoding="utf-8") + "\nSNAPSHOT_TAG = 'A'\n",
            encoding="utf-8",
        )
        (src_b / "tools/_sdd_core.py").write_text(
            (src_b / "tools/_sdd_core.py").read_text(encoding="utf-8") + "\nSNAPSHOT_TAG = 'B'\n",
            encoding="utf-8",
        )
        saved_sys_path = list(sys.path)
        sentinel_core = object()
        sentinel_dv = object()
        old_core = sys.modules.get("_sdd_core")
        old_dv = sys.modules.get("docs_validation")
        sys.modules["_sdd_core"] = sentinel_core  # type: ignore[assignment]
        sys.modules["docs_validation"] = sentinel_dv  # type: ignore[assignment]
        try:
            core_a, dv_a = installer_lib._load_trusted_tools(src_a, need_docs_validation=True)
            core_b, dv_b = installer_lib._load_trusted_tools(src_b, need_docs_validation=True)
            self.assertEqual(core_a.SNAPSHOT_TAG, "A")
            self.assertEqual(core_b.SNAPSHOT_TAG, "B")
            self.assertIsNot(core_a, core_b)
            self.assertIsNot(dv_a, dv_b)
            self.assertIs(sys.modules.get("_sdd_core"), sentinel_core)
            self.assertIs(sys.modules.get("docs_validation"), sentinel_dv)
            self.assertEqual(sys.path, saved_sys_path)
        finally:
            if old_core is None:
                sys.modules.pop("_sdd_core", None)
            else:
                sys.modules["_sdd_core"] = old_core
            if old_dv is None:
                sys.modules.pop("docs_validation", None)
            else:
                sys.modules["docs_validation"] = old_dv

        # Untrusted $DEST_DIR/tools/{_sdd_core,docs_validation}.py NEVER executed by doctor-*!
        proj = self.clone_installed("rce-guard")
        sentinel_rce = self.make_dir("rce-sentinel") / "pwned.txt"
        payload = f"from pathlib import Path\nPath({str(sentinel_rce)!r}).write_text('pwned', encoding='utf-8')\n"
        (proj / "tools/docs_validation.py").write_text(payload, encoding="utf-8")
        (proj / "tools/_sdd_core.py").write_text(payload, encoding="utf-8")

        old_env_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.mock_bin}:{old_env_path}"
        try:
            rc_dm, out_dm, _ = run_lib(["doctor-manifest", str(proj), str(ROOT)])
            self.assertEqual(rc_dm, 0)
            self.assertIn("WARN tools: managed tool tools/docs_validation.py differs from canonical template SHA-256", out_dm)
            self.assertIn("WARN tools: managed tool tools/_sdd_core.py differs from canonical template SHA-256", out_dm)

            rc_dms, _, err_dms = run_lib(["doctor-manifest", str(proj), str(ROOT), "--strict"])
            self.assertEqual(rc_dms, 1)
            self.assertIn("FAIL tools: managed tool tools/docs_validation.py differs from canonical template SHA-256", err_dms)

            self.assertEqual(run_lib(["doctor-links", str(proj), str(ROOT)])[0], 0)
            self.assertEqual(run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])[0], 0)
            self.assertFalse(sentinel_rce.exists(), "Untrusted $DEST_DIR tool was executed!")
        finally:
            os.environ["PATH"] = old_env_path

    def test_sdd_core_doctor_diagnostics_and_brownfield_validator_bundle(self) -> None:
        """RT-06: missing/0-byte _sdd_core.py doctor diagnostics, 5120B skill cap, and brownfield VALIDATOR_BUNDLE_MANAGED=false."""
        src_tpl = self.clone_source_template("doc-src")
        self.assertEqual(run_lib(["doctor-source", str(src_tpl)])[0], 0)

        # Skill > 5120 bytes fails doctor-source; <= 5120 bytes passes
        sp = src_tpl / "skills/sdd-plan/SKILL.md"
        orig_sp = sp.read_bytes()
        sp.write_bytes(orig_sp + b"x" * 1200)
        rc_big, _, err_big = run_lib(["doctor-source", str(src_tpl)])
        self.assertEqual(rc_big, 1)
        self.assertIn("exceeds 5120 bytes", err_big)
        sp.write_bytes(orig_sp)

        # 0-byte and missing $SRC_DIR/tools/_sdd_core.py fail doctor-source, doctor-links, and doctor-spec-readiness cleanly
        core_src = src_tpl / "tools/_sdd_core.py"
        core_src.write_bytes(b"")
        for subcmd, args in (
            ("doctor-source", [str(src_tpl)]),
            ("doctor-links", [str(src_tpl), str(src_tpl)]),
            ("doctor-spec-readiness", [str(src_tpl), str(src_tpl)]),
        ):
            rc, _, err = run_lib([subcmd, *args])
            self.assertEqual(rc, 1, subcmd)
            self.assertIn("tools/_sdd_core.py", err)
            self.assertNotIn("Traceback", err)

        core_src.unlink()
        for subcmd, args in (
            ("doctor-source", [str(src_tpl)]),
            ("doctor-links", [str(src_tpl), str(src_tpl)]),
            ("doctor-spec-readiness", [str(src_tpl), str(src_tpl)]),
        ):
            rc, _, err = run_lib([subcmd, *args])
            self.assertEqual(rc, 1, subcmd)
            self.assertIn("tools/_sdd_core.py", err)

        # Downstream 0-byte and missing managed tools/_sdd_core.py fail default doctor-manifest
        proj = self.clone_installed("empty-core")
        (proj / "tools/_sdd_core.py").write_bytes(b"")
        rc_e, _, err_e = run_lib(["doctor-manifest", str(proj), str(ROOT)])
        self.assertEqual(rc_e, 1)
        self.assertIn("FAIL tools: empty managed tool tools/_sdd_core.py (0 bytes)", err_e)

        (proj / "tools/_sdd_core.py").unlink()
        rc_m, _, err_m = run_lib(["doctor-manifest", str(proj), str(ROOT)])
        self.assertEqual(rc_m, 1)
        self.assertIn("FAIL tools: missing or symlinked managed tool tools/_sdd_core.py", err_m)

        # Brownfield VALIDATOR_BUNDLE_MANAGED=false: user-owned docs_validation.py skips validator bundle
        # while STILL installing tools/_sdd_core.py, and doctor-manifest emits --update --force guidance!
        bf = self.make_dir("brownfield-vb") / "app"
        (bf / "tools").mkdir(parents=True)
        (bf / "tools/docs_validation.py").write_text("# user-owned helper\n", encoding="utf-8")
        subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--models", "claude"],
            cwd=bf,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        self.assertTrue((bf / "tools/_sdd_core.py").is_file())
        self.assertFalse((bf / "tools/validate-docs.py").exists())
        self.assertEqual((bf / "tools/docs_validation.py").read_text(encoding="utf-8"), "# user-owned helper\n")
        bf_manifest = json.loads((bf / "template-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("tools/_sdd_core.py", bf_manifest["managed_paths"])
        self.assertNotIn("tools/docs_validation.py", bf_manifest["managed_paths"])
        self.assertNotIn("tools/validate-docs.py", bf_manifest["managed_paths"])

        rc_bfd, out_bfd, _ = run_lib(["doctor-manifest", str(bf), str(ROOT)])
        self.assertEqual(rc_bfd, 0)
        self.assertIn("tools/docs_validation.py is user-owned while SDD tools are template-managed", out_bfd)
        self.assertIn("setup.sh --update --force", out_bfd)

    def test_doctor_spec_readiness_self_mode_and_vault_parity(self) -> None:
        """Session 3 Q1 + v0.7.1 #13: zero-warning self spec readiness (non-strict & strict) + legacy/Clarify/Wikilink/Mermaid checks."""
        proj = self.clone_installed("spec-readiness")
        feats = proj / "docs/current/05 - Product Features"

        # Add a Tier M self-stamped spec and verify BOTH non-strict and strict doctor-spec-readiness emit ZERO warnings!
        mini_dir = feats / "001-self-mini"
        mini_dir.mkdir(parents=True)
        mini_body = (
            "---\n"
            "status: approved\n"
            "owner: engineering\n"
            'approved_by: "lead"\n'
            'approved_at: "2026-11-19"\n'
            'approval_evidence: "PR-1"\n'
            "source_revision: self\n"
            "contract_sha256: PLACEHOLDER\n"
            "---\n"
            "# Mini\n\n## Acceptance criteria\n\n"
            "| ID | Scenario | Expected result |\n|---|---|---|\n"
            "| AC-01 | Login | 200 OK |\n\n"
            "## Pre-implementation readiness checklist\n\n- [x] Ready.\n\n"
            "## Execution tasks\n\n"
            "| Task ID | Status | [P] | Depends on | Related AC | Owned paths | Summary | Verification |\n"
            "|---|---|---|---|---|---|---|---|\n"
            "| T-01 | todo | no | - | AC-01 | `src/a.py` | Do A | `pytest` |\n"
        )
        csha = compute_contract_sha256("1. Mini Spec.md", Path("docs/current/05 - Product Features/001-self-mini/1. Mini Spec.md"), mini_body)
        (mini_dir / "1. Mini Spec.md").write_text(mini_body.replace("PLACEHOLDER", csha), encoding="utf-8")

        for extra in ([], ["--strict"]):
            rc, out, err = run_lib(["doctor-spec-readiness", str(proj), str(ROOT), *extra])
            self.assertEqual(rc, 0, err)
            self.assertNotIn("WARN spec readiness:", out)
            self.assertIn("PASS spec readiness:", out)

        # Legacy 7-hex source_revision warns in non-strict and fails in --strict
        short_dir = feats / "002-short-sha"
        short_dir.mkdir()
        (short_dir / "1. Mini Spec.md").write_text(
            mini_body.replace("source_revision: self\ncontract_sha256: PLACEHOLDER\n", "source_revision: b8b8355\n"),
            encoding="utf-8",
        )
        rc_w, out_w, _ = run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])
        self.assertEqual(rc_w, 0)
        self.assertIn("WARN spec readiness:", out_w)
        with self.assertRaises(ValueError):
            installer_lib.cmd_doctor_spec_readiness([str(proj), str(ROOT), "--strict"])
        shutil.rmtree(short_dir)

        # Broken [[NonExistentNote]], invalid Mermaid, orphan superseded, and [NEEDS CLARIFICATION] in approved fail!
        ov = proj / "docs/current/01 - Overview/Overview.md"
        orig_ov = ov.read_text(encoding="utf-8")

        ov.write_text(orig_ov + "\nBroken [[NonExistentNote]]\n", encoding="utf-8")
        self.assertEqual(run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])[0], 1)

        ov.write_text(orig_ov + "\n```mermaid\n--> no_type\n```\n", encoding="utf-8")
        self.assertEqual(run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])[0], 1)

        ov.write_text("---\nstatus: superseded\nowner: eng\n---\n# Orphan\n", encoding="utf-8")
        self.assertEqual(run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])[0], 1)
        ov.write_text(orig_ov, encoding="utf-8")

        (mini_dir / "1. Mini Spec.md").write_text(
            (mini_dir / "1. Mini Spec.md").read_text(encoding="utf-8") + "\n[NEEDS CLARIFICATION: leak]\n",
            encoding="utf-8",
        )
        self.assertEqual(run_lib(["doctor-spec-readiness", str(proj), str(ROOT)])[0], 1)

    def test_doctor_links_title_syntax_and_scoped_boundaries(self) -> None:
        """v0.7.1 #14 + v0.7.2: (Title) / <...> / balanced links via _sdd_core, !! & \\\\ failure, skipped dirs, backup gitignore warn."""
        proj = self.clone_installed("doc-links")
        (proj / "docs/current/file (1).md").write_text("---\nstatus: active\nowner: eng\n---\n# Spaced\n", encoding="utf-8")
        note = proj / "docs/current/note.md"
        note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Note\n\n"
            'See [A](<./file (1).md>), [B](./Overview.md "Title"), and [C](../Vault%20Index%20MOC.md (MOC Title)).\n',
            encoding="utf-8",
        )
        # Wait: Overview.md is in 01 - Overview/Overview.md; fix relative link to ./01%20-%20Overview/Overview.md
        note.write_text(
            "---\nstatus: active\nowner: eng\n---\n# Note\n\n"
            'See [A](<./file (1).md>), [B](./01%20-%20Overview/Overview.md "Title"), and [C](./Vault%20Index%20MOC.md (MOC Title)).\n',
            encoding="utf-8",
        )
        # Broken links outside docs/ & managed_paths (README.md, testdata/, plans/, node_modules/, .venv/, .ai-template-backup.*) are ignored
        (proj / "README.md").write_text("[gh](/blob/main/x.md) [broken](./nope.md)\n", encoding="utf-8")
        for ignored_rel in (
            "testdata/bad.md",
            "plans/roadmap.md",
            "node_modules/pkg/README.md",
            ".venv/lib/README.md",
            ".ai-template-backup.manual1/RECOVERY.md",
        ):
            p = proj / ignored_rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("[broken](./does-not-exist.md)\n", encoding="utf-8")

        rc_ok, out_ok, err_ok = run_lib(["doctor-links", str(proj), str(ROOT)])
        self.assertEqual(rc_ok, 0, err_ok)
        self.assertIn("PASS docs links:", out_ok)

        for bad_md in (
            "!![broken](./missing.md)",
            r"\\[broken](./missing.md)",
            "[scheme](file:///etc/passwd)",
            "[js](javascript:alert(1))",
            "[esc](../../../outside.md)",
        ):
            note.write_text(f"---\nstatus: active\nowner: eng\n---\n# Note\n\n{bad_md}\n", encoding="utf-8")
            rc_b, _, err_b = run_lib(["doctor-links", str(proj), str(ROOT)])
            self.assertEqual(rc_b, 1, bad_md)
            self.assertIn("FAIL docs links:", err_b)

        # Unignored .ai-template-backup.manual1 warns until .gitignore covers .ai-template-backup.*/
        (proj / ".gitignore").unlink()
        subprocess.run(["git", "-C", str(proj), "init", "-q"], check=True)
        _, out_unig, _ = run_lib(["doctor-manifest", str(proj), str(ROOT)])
        self.assertIn("WARN backup: local backup directory .ai-template-backup.manual1 is present and not git-ignored", out_unig)
        (proj / ".gitignore").write_text(".ai-template-backup.*/\n", encoding="utf-8")
        _, out_ig, _ = run_lib(["doctor-manifest", str(proj), str(ROOT)])
        self.assertNotIn("WARN backup:", out_ig)

    def test_models_ownership_adapters_skills_presets_and_manifest_guards(self) -> None:
        """Covers runtime selection, shared .agents/skills, gemma/codex/copilot doctor, user-owned skills/tools, --set-models, presets."""
        # 1. Invalid CLI combinations on setup.sh fail fast without writing files
        empty_t = self.make_dir("cli-guards")
        for bad_args, substr in (
            (["--models", "antigravity,invalid"], "Unknown model 'invalid'"),
            (["--models", "gemini"], "Unknown model 'gemini'"),
            (["--models="], "--models requires"),
            (["--models", "antigravity", "--models", "qwen"], "can only be provided once"),
            (["--update"], "--update requires"),
            (["--doctor", "--without-skills"], "--doctor"),
            (["--preset", "missing-custom"], "docs/templates/presets/missing-custom"),
        ):
            sub_t = empty_t / f"case-{abs(hash(tuple(bad_args)))}"
            sub_t.mkdir(exist_ok=True)
            res = subprocess.run(
                ["bash", str(ROOT / "setup.sh"), *bad_args],
                cwd=sub_t,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(res.returncode, 0, bad_args)
            self.assertIn(substr, res.stdout + res.stderr)
            self.assertFalse((sub_t / "AGENTS.md").exists())

        # 2. Shared .agents/skills deduplication (opencode,codex,cursor,copilot -> 9 skills) + AGENTS.override.md + gemma doctor
        shared_t = self.make_dir("shared-models")
        subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--models", "opencode,codex,cursor,copilot", "--preset", "security-hardening"],
            cwd=shared_t,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        m_shared = json.loads((shared_t / "template-manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m_shared["selected_models"], ["opencode", "codex", "cursor", "copilot"])
        self.assertEqual(m_shared["managed_adapter_models"], ["cursor", "copilot"])
        self.assertEqual(m_shared["default_preset"], "security-hardening")
        agent_skills = [p for p in m_shared["managed_paths"] if p.startswith(".agents/skills/")]
        self.assertEqual(len(agent_skills), 9)
        self.assertFalse((shared_t / "CLAUDE.md").exists())

        (shared_t / "AGENTS.override.md").write_text("# override\n", encoding="utf-8")
        old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = f"{self.mock_bin}:{old_path}"
        try:
            rc_co, out_co, _ = run_lib(["doctor-manifest", str(shared_t), str(ROOT)])
            self.assertEqual(rc_co, 0)
            self.assertIn("WARN runtime codex: unmanaged AGENTS.override.md", out_co)
            self.assertIn("PASS preset: built-in default_preset 'security-hardening' verified", out_co)
            rc_cos, _, err_cos = run_lib(["doctor-manifest", str(shared_t), str(ROOT), "--strict"])
            self.assertEqual(rc_cos, 1)
            self.assertIn("FAIL runtime codex: unmanaged AGENTS.override.md", err_cos)
        finally:
            os.environ["PATH"] = old_path

        # Gemma runtime fails doctor-manifest because host-level system-prompt injection cannot be verified
        m_shared["requested_models"] = ["gemma"]
        m_shared["selected_models"] = ["gemma"]
        (shared_t / "template-manifest.json").write_text(json.dumps(m_shared), encoding="utf-8")
        rc_gm, _, err_gm = run_lib(["doctor-manifest", str(shared_t), str(ROOT)])
        self.assertEqual(rc_gm, 1)
        self.assertIn("FAIL runtime gemma", err_gm)

        # Unsafe destination manifest rejected by doctor-manifest and prepare-manifest-models
        m_shared["managed_paths"].append("../outside")
        (shared_t / "template-manifest.json").write_text(json.dumps(m_shared), encoding="utf-8")
        self.assertEqual(run_lib(["doctor-manifest", str(shared_t), str(ROOT)])[0], 1)
        self.assertEqual(run_lib(["prepare-manifest-models", str(shared_t), "claude", "false"])[0], 1)

        # Unmanaged manifest preserved ("UNMANAGED")
        unm = self.make_dir("unmanaged-manifest")
        (unm / "template-manifest.json").write_text('{"template":"user-owned","custom":true}\n', encoding="utf-8")
        rc_u, out_u, _ = run_lib(["prepare-manifest-models", str(unm), "claude", "false"])
        self.assertEqual(rc_u, 0)
        self.assertEqual(out_u.strip(), "UNMANAGED")

        # 3. Brownfield user-owned adapter (.github/copilot-instructions.md), user-owned skill, user-owned tools, --set-models & presets
        bf_t = self.make_dir("bf-setmodels")
        (bf_t / ".github").mkdir()
        (bf_t / ".github/copilot-instructions.md").write_text("# Custom Copilot without canonical pointer\n", encoding="utf-8")
        (bf_t / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
        res_bf = subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--models", "copilot,claude,qwen", "--without-skills", "--with-advanced-docs", "--with-legacy-agents"],
            cwd=bf_t,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("WARN: .gitignore does not ignore '.ai-template-backup.*/'", res_bf.stdout + res_bf.stderr)
        self.assertEqual((bf_t / ".gitignore").read_text(encoding="utf-8"), "node_modules/\n")
        self.assertTrue((bf_t / ".agents/AGENTS.md").is_file())
        self.assertTrue((bf_t / "docs/current/03 - API & Integrations/API Reference.md").is_file())

        # Customize QWEN.md, then --update --set-models copilot -> prunes CLAUDE.md, preserves modified QWEN.md & custom copilot adapter
        with (bf_t / "QWEN.md").open("a", encoding="utf-8") as fh:
            fh.write("\n# local qwen customization\n")
        res_prune = subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--update", "--set-models", "copilot", "--without-skills", "--preset", "cli-tool"],
            cwd=bf_t,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("PRUNED (deselected): CLAUDE.md", res_prune.stdout)
        self.assertIn("WARN: preserving user-modified deselected file: QWEN.md", res_prune.stdout + res_prune.stderr)
        self.assertFalse((bf_t / "CLAUDE.md").exists())
        self.assertIn("# local qwen customization", (bf_t / "QWEN.md").read_text(encoding="utf-8"))
        self.assertEqual(json.loads((bf_t / "template-manifest.json").read_text(encoding="utf-8"))["default_preset"], "cli-tool")

        # Symlinked custom preset rejected on --update --preset
        (bf_t / "docs/templates/presets").mkdir(parents=True, exist_ok=True)
        (bf_t / "docs/templates/presets/evil-sym").symlink_to(empty_t)
        res_sym_p = subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--update", "--preset", "evil-sym"],
            cwd=bf_t,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(res_sym_p.returncode, 0)
        (bf_t / "docs/templates/presets/evil-sym").unlink()

        os.environ["PATH"] = f"{self.mock_bin}:{old_path}"
        try:
            rc_cpw, out_cpw, _ = run_lib(["doctor-manifest", str(bf_t), str(ROOT)])
            self.assertEqual(rc_cpw, 0)
            self.assertIn("WARN runtime copilot: user-owned .github/copilot-instructions.md does not reference AGENTS.md", out_cpw)
            rc_cps, _, err_cps = run_lib(["doctor-manifest", str(bf_t), str(ROOT), "--strict"])
            self.assertEqual(rc_cps, 1)
            self.assertIn("FAIL runtime copilot", err_cps)
        finally:
            os.environ["PATH"] = old_path

        # 4. --update --without-skills preserves SKILL.md on disk (OPTOUT_SKILL), and user-owned tools/skills report USER_TOOL / USER_SKILL
        u_proj = self.clone_installed("user-owned-items")
        _, out_opt, _ = run_lib(["prepare-ownership", str(ROOT), str(u_proj), "claude", "false", "false", "true", "false"])
        self.assertIn("OPTOUT_SKILL|.claude/skills/sdd-docs/SKILL.md", out_opt)
        u_m = json.loads((u_proj / "template-manifest.json").read_text(encoding="utf-8"))
        for drop_item in ("tools/_sdd_core.py", "tools/stamp-spec.py", ".claude/skills/sdd-plan/SKILL.md"):
            u_m["managed_paths"] = [x for x in u_m["managed_paths"] if x != drop_item]
            u_m["profiles"]["core"] = [x for x in u_m["profiles"]["core"] if x != drop_item]
        (u_proj / "template-manifest.json").write_text(json.dumps(u_m), encoding="utf-8")
        (u_proj / "tools/_sdd_core.py").write_text("# custom user _sdd_core\n", encoding="utf-8")
        (u_proj / "tools/stamp-spec.py").write_text("# custom user stamp-spec\n", encoding="utf-8")
        (u_proj / ".claude/skills/sdd-plan/SKILL.md").write_text("# custom user skill\n", encoding="utf-8")

        rc_uo, out_uo, _ = run_lib(["prepare-ownership", str(ROOT), str(u_proj), "claude", "true", "false", "true", "false"])
        self.assertEqual(rc_uo, 0)
        self.assertIn("USER_TOOL|tools/_sdd_core.py", out_uo)
        self.assertIn("USER_TOOL|tools/stamp-spec.py", out_uo)
        self.assertIn("SCHEDULE_TOOL|tools/record-evidence.py", out_uo)
        self.assertIn("USER_SKILL|.claude/skills/sdd-plan/SKILL.md", out_uo)
        self.assertIn("SCHEDULE_SKILL|.claude/skills/sdd-specify/SKILL.md", out_uo)

    def test_historical_git_archive_upgrades_to_v072(self) -> None:
        """Verifies v0.4.0..v0.7.1 -> v0.7.2 upgrades, legacy template renames, and zero-warning --set-models claude pruning."""
        # 1. Verify PRIOR_TEMPLATE_SHA256S covers 100% of canonical adapters, skills, and tools across ALL cached historical archives!
        check_rels = [
            "AGENTS.md",
            "CLAUDE.md",
            "GEMINI.md",
            "QWEN.md",
            "adapters/copilot-instructions.md",
            "adapters/cursor-agents.mdc",
            *[f"skills/{slug}/SKILL.md" for slug in installer_lib.SDD_SKILL_SLUGS],
            "tools/docs_validation.py",
            "tools/validate-docs.py",
            "tools/new-feature.py",
            "tools/export-tasks.py",
            "tools/stamp-spec.py",
            "tools/record-evidence.py",
            "tools/validate-task-evidence.py",
        ]
        current_shas = {
            rel: hashlib.sha256((ROOT / rel).read_bytes()).hexdigest()
            for rel in check_rels
            if (ROOT / rel).is_file()
        }
        for ver_label, arch_dir in self.archives.items():
            for rel in check_rels:
                arch_file = arch_dir / rel
                if not arch_file.is_file():
                    continue
                digest = hashlib.sha256(arch_file.read_bytes()).hexdigest()
                known = installer_lib.PRIOR_TEMPLATE_SHA256S.get(rel, set()) | {current_shas[rel]}
                self.assertIn(
                    digest,
                    known,
                    f"{ver_label}:{rel} SHA-256 {digest} missing from PRIOR_TEMPLATE_SHA256S!",
                )

        # 2. v0.4.0 & v0.4.2 -> v0.7.2 legacy template rename + user-modified preservation
        v042_src = self.archives["v0.4.2"]
        leg_clean = self.make_dir("v042-clean")
        subprocess.run(
            ["bash", str(v042_src / "setup.sh"), "--models", "claude,gemini,qwen"],
            cwd=leg_clean,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        res_v042 = subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--update", "--set-models", "claude"],
            cwd=leg_clean,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertIn("MIGRATED (renamed template)", res_v042.stdout)
        self.assertNotIn("preserving user-modified deselected file", res_v042.stdout + res_v042.stderr)
        self.assertFalse((leg_clean / "docs/templates/task-evidence-template.md").exists())
        self.assertTrue((leg_clean / "docs/templates/3. Task Evidence Template.md").is_file())
        self.assertFalse((leg_clean / "GEMINI.md").exists())
        self.assertFalse((leg_clean / "QWEN.md").exists())
        self.assertTrue((leg_clean / "tools/_sdd_core.py").is_file())

        # User-modified v0.4.2 template detected via check-legacy-rename & verify-sha256 (preserved during --update)
        leg_mod = self.clone_installed("v042-mod-check")
        leg_m = json.loads((leg_mod / "template-manifest.json").read_text(encoding="utf-8"))
        leg_m["version"] = "0.4.2"
        (leg_mod / "template-manifest.json").write_text(json.dumps(leg_m), encoding="utf-8")
        v042_tpl_bytes = (v042_src / "docs/templates/task-evidence-template.md").read_bytes()
        v042_tpl_sha = hashlib.sha256(v042_tpl_bytes).hexdigest()
        (leg_mod / "docs/templates/task-evidence-template.md").write_bytes(v042_tpl_bytes)
        self.assertEqual(run_lib(["check-legacy-rename", str(leg_mod), "docs/templates/task-evidence-template.md"])[0], 0)
        self.assertEqual(run_lib(["verify-sha256", str(leg_mod), "docs/templates/task-evidence-template.md", v042_tpl_sha])[0], 0)
        (leg_mod / "docs/templates/task-evidence-template.md").write_bytes(v042_tpl_bytes + b"user customization\n")
        self.assertEqual(run_lib(["verify-sha256", str(leg_mod), "docs/templates/task-evidence-template.md", v042_tpl_sha])[0], 1)

        # Post-v0.4.3 manifest never triggers legacy rename
        leg_m["version"] = "0.7.2"
        (leg_mod / "template-manifest.json").write_text(json.dumps(leg_m), encoding="utf-8")
        self.assertEqual(run_lib(["check-legacy-rename", str(leg_mod), "docs/templates/task-evidence-template.md"])[0], 1)

        # v0.4.0 verify-sha256 helper parity
        v040_src = self.archives["v0.4.0"]
        v040_sha = hashlib.sha256((v040_src / "docs/templates/runtime-delegation-evidence-template.md").read_bytes()).hexdigest()
        self.assertEqual(run_lib(["verify-sha256", str(v040_src), "docs/templates/runtime-delegation-evidence-template.md", v040_sha])[0], 0)

    def test_v071_to_v072_set_models_pruning_and_cursor_reselection(self) -> None:
        """End-to-end v0.7.1 -> v0.7.2 --update --set-models claude pruning + cursor re-selection with zero false warnings."""
        v071_src = self.archives["v0.7.1"]
        mig_071 = self.make_dir("v071-setmodels")
        subprocess.run(
            ["bash", str(v071_src / "setup.sh"), "--models", "claude,cursor,qwen"],
            cwd=mig_071,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        res_071 = subprocess.run(
            ["bash", str(ROOT / "setup.sh"), "--update", "--set-models", "claude"],
            cwd=mig_071,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertNotIn("preserving user-modified deselected file", res_071.stdout + res_071.stderr)
        for pruned_p in (".agents/skills", ".qwen/skills", "QWEN.md", ".cursor/rules/agents.mdc"):
            self.assertFalse((mig_071 / pruned_p).exists(), pruned_p)
        self.assertEqual(len(list((mig_071 / ".claude/skills").glob("sdd-*/SKILL.md"))), 9)
        self.assertTrue((mig_071 / "tools/_sdd_core.py").is_file())

        # Verify re-selecting claude,cursor schedules cursor adapter & 9 .agents/skills without USER_SKILL/USER_ADAPTER lockout
        rc_sel, out_sel, _ = run_lib(["select-update-models", str(ROOT), str(mig_071), "claude,cursor"])
        self.assertEqual(rc_sel, 0)
        self.assertIn("claude,cursor", out_sel)
        rc_readd, out_readd, _ = run_lib(["prepare-ownership", str(ROOT), str(mig_071), "claude,cursor", "true", "false", "true", "true"])
        self.assertEqual(rc_readd, 0)
        self.assertNotIn("USER_SKILL|", out_readd)
        self.assertIn("SCHEDULE_SKILL|.agents/skills/sdd-fix/SKILL.md", out_readd)


def _iter_cases(suite: unittest.TestSuite) -> list[unittest.TestCase]:
    cases: list[unittest.TestCase] = []
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            cases.extend(_iter_cases(item))
        else:
            cases.append(item)
    return cases


class _ParallelInstallerSuite(unittest.TestSuite):
    """Runs isolated InstallerLibAndUpgradesTest methods across subprocess workers sharing cached archives."""

    def run(self, result: unittest.TestResult, debug: bool = False) -> unittest.TestResult:
        cases = list(self)
        if debug or len(cases) <= 1 or os.environ.get("_AI_TPL_SERIAL_WORKER") == "1":
            return super().run(result, debug=debug)

        InstallerLibAndUpgradesTest.setUpClass()
        try:
            worker_env = os.environ.copy()
            worker_env["_AI_TPL_SERIAL_WORKER"] = "1"
            worker_env["_AI_TPL_SHARED_INSTALLER_DIR"] = str(InstallerLibAndUpgradesTest._shared_base)
            max_workers = min(len(cases), max(4, min(12, os.cpu_count() or 4)))

            def _exec_one(case: unittest.TestCase) -> tuple[unittest.TestCase, int, str, str]:
                target_id = f"tests.test_installer.{case.__class__.__qualname__}.{case._testMethodName}"
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
            InstallerLibAndUpgradesTest.tearDownClass()
        return result


def load_tests(loader: unittest.TestLoader, standard_tests: unittest.TestSuite, pattern: str | None) -> unittest.TestSuite:
    if os.environ.get("_AI_TPL_SERIAL_WORKER") == "1":
        return standard_tests
    cases = _iter_cases(standard_tests)
    if len(cases) <= 1:
        return standard_tests
    return _ParallelInstallerSuite(cases)


if __name__ == "__main__":
    unittest.main()
