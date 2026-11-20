#!/usr/bin/env python3
"""Validate per-task evidence provenance and verified reference inventories."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import hashlib
import json
import re
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REQUIRED_CORE_SYMBOLS = (
    "GitCatFileBatch",
    "HEX40_RE",
    "REGULAR_GIT_BLOB_MODES",
    "SDD_CORE_API_VERSION",
    "parse_frontmatter",
    "read_bytes_nofollow",
    "read_text_nofollow",
    "resolve_git_toplevel",
)

try:
    import _sdd_core  # noqa: E402
except ImportError as exc:
    print(
        f"FAIL: validate-task-evidence.py requires tools/_sdd_core.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if user-owned): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

missing_core = [sym for sym in REQUIRED_CORE_SYMBOLS if not hasattr(_sdd_core, sym)]
if getattr(_sdd_core, "SDD_CORE_API_VERSION", 0) < 1 or missing_core:
    print(
        f"FAIL: validate-task-evidence.py requires an up-to-date tools/_sdd_core.py (SDD_CORE_API_VERSION >= 1) in {SCRIPT_DIR} "
        "(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if tools/_sdd_core.py is user-owned)",
        file=sys.stderr,
    )
    sys.exit(1)

DEFAULT_ROOT = SCRIPT_DIR.parent
VALID_EVIDENCE_STATUSES = {"draft", "completed", "template"}
PLACEHOLDER_VALUES = {"", "todo", "tbd", "pending", "n/a", "none", "-", "draft"}
HEX40_RE = _sdd_core.HEX40_RE
REGULAR_GIT_BLOB_MODES = _sdd_core.REGULAR_GIT_BLOB_MODES
GitCatFileBatch = _sdd_core.GitCatFileBatch
read_text_nofollow = _sdd_core.read_text_nofollow
_resolve_git_toplevel = _sdd_core.resolve_git_toplevel


def read_bytes_nofollow(path: Path) -> bytes:
    raw, _mode = _sdd_core.read_bytes_nofollow(path)
    return raw


def parse_evidence_frontmatter(text: str, path: Path) -> dict[str, str]:
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not re.match(r"^---[ \t]*\n.*?\n---[ \t]*(?:\n|$)", normalized, flags=re.S):
        raise ValueError(f"{path}: missing frontmatter")
    return _sdd_core.parse_frontmatter(normalized)


def walk_inside_root_no_symlinks(root: Path, rel_path: Path, label: str) -> Path:
    if root.is_symlink():
        raise ValueError(f"repository root cannot be a symlink: {root}")
    if rel_path.is_absolute():
        raise ValueError(f"{label}: path must be relative to repository root: {rel_path}")
    cur = root
    for part in rel_path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if cur == root:
                raise ValueError(f"{label}: path escapes repository root: {rel_path}")
            cur = cur.parent
            continue
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"{label}: symlink path component refused: {cur.relative_to(root)}")
    if cur.exists() and not cur.resolve().is_relative_to(root.resolve()):
        raise ValueError(f"{label}: path escapes repository root: {rel_path}")
    return cur


def resolve_evidence_dir_safe(root: Path, raw_dir: str) -> Path:
    candidate = Path(raw_dir)
    if not candidate.is_absolute():
        return walk_inside_root_no_symlinks(root, candidate, "--evidence-dir")

    if candidate.is_symlink():
        raise ValueError(f"--evidence-dir: symlink refused: {candidate}")
    root_resolved = root.resolve()
    try:
        cand_resolved = candidate.resolve()
    except OSError as exc:
        raise ValueError(f"--evidence-dir: invalid path {candidate} ({exc})") from exc
    if cand_resolved.is_relative_to(root_resolved):
        rel = cand_resolved.relative_to(root_resolved)
        for parent in reversed(candidate.parents):
            if not parent.is_symlink() and parent.exists() and parent.resolve() == root_resolved:
                raw_rel = Path(*candidate.parts[len(parent.parts) :])
                return walk_inside_root_no_symlinks(root_resolved, raw_rel, "--evidence-dir")
        return walk_inside_root_no_symlinks(root_resolved, rel, "--evidence-dir")
    return candidate


def require_fields(data: dict[str, str], keys: list[str], path: Path) -> None:
    missing = [key for key in keys if not data.get(key)]
    if missing:
        raise ValueError(f"{path}: missing completed-task fields: {', '.join(missing)}")


def _compute_git_rel_lexical(git_top: Path, root: Path, target_inside_root: Path, label: str) -> str:
    if not root.is_relative_to(git_top):
        raise ValueError(f"{label}: repository root {root} escapes Git toplevel {git_top}")
    walk_inside_root_no_symlinks(git_top, root.relative_to(git_top), "repository root")
    if not target_inside_root.is_relative_to(root):
        raise ValueError(f"{label}: path escapes repository root: {target_inside_root}")
    git_rel = target_inside_root.relative_to(git_top).as_posix()
    if not git_rel or git_rel.startswith(":"):
        raise ValueError(f"{label}: invalid Git relative path '{git_rel}'")
    return git_rel


def _assert_not_gitignored(git_top: Path, git_rel: str, entry: Path) -> None:
    if git_rel.startswith(":"):
        raise ValueError(f"{entry}: path cannot start with ':' ({git_rel})")
    try:
        proc = subprocess.run(
            ["git", "-C", str(git_top), "check-ignore", "-q", "--", git_rel],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError(f"{entry}: git binary unavailable for check-ignore ({exc})") from exc
    if proc.returncode == 0:
        raise ValueError(f"{entry}: path is ignored by .gitignore: {git_rel}")
    if proc.returncode != 1:
        err = proc.stderr.strip() or f"exit {proc.returncode}"
        raise ValueError(f"{entry}: git check-ignore failed for '{git_rel}': {err}")


def _verify_regular_tree_mode(
    batch: GitCatFileBatch,
    entry: Path,
    rev_ref: str,
    rev_label: str,
    git_rel: str,
    unavailable_msg: str,
) -> None:
    mode = batch.tree_entry_mode(rev_ref, git_rel)
    if mode is None:
        raise ValueError(unavailable_msg)
    if mode not in REGULAR_GIT_BLOB_MODES:
        kind = "symlink" if mode == "120000" else ("gitlink" if mode == "160000" else "non-regular entry")
        raise ValueError(
            f"{entry}: refused {kind} (mode {mode}) for '{git_rel}' at {rev_label} ({rev_ref}); expected regular file (100644/100755)"
        )


def _verify_40hex_git_artifact(
    git_top: Path | None,
    root: Path,
    entry: Path,
    revision: str,
    artifact_full: Path,
    expected_sha256: str,
    raw_source_rev: str,
    *,
    batch: GitCatFileBatch | None = None,
) -> None:
    if not HEX40_RE.fullmatch(revision) or re.fullmatch(r"0+", revision):
        raise ValueError(f"{entry}: source revision must be a full lowercase Git SHA")
    if git_top is None:
        raise ValueError(f"{entry}: source revision is unavailable: {raw_source_rev}")
    artifact_git_rel = _compute_git_rel_lexical(git_top, root, artifact_full, f"{entry} output_artifact_path")

    def _run_with_batch(active_batch: GitCatFileBatch) -> None:
        try:
            chk = active_batch.check(f"{revision}^{{commit}}")
        except OSError as exc:
            raise ValueError(f"{entry}: source revision is unavailable: {raw_source_rev}") from exc
        if chk is None or chk[1] != "commit":
            raise ValueError(f"{entry}: source revision is unavailable: {raw_source_rev}")

        source_spec = f"{revision}:{artifact_git_rel}"
        unavailable_msg = f"{entry}: output artifact is unavailable at source revision: {source_spec}"
        _verify_regular_tree_mode(
            active_batch,
            entry,
            revision,
            "source revision",
            artifact_git_rel,
            unavailable_msg,
        )
        try:
            artifact_bytes = active_batch.read_blob(source_spec)
        except OSError as exc:
            raise ValueError(unavailable_msg) from exc
        if artifact_bytes is None:
            raise ValueError(unavailable_msg)

        digest = hashlib.sha256(artifact_bytes).hexdigest()
        if digest != expected_sha256.strip().lower():
            raise ValueError(f"{entry}: output artifact checksum does not match")

    if batch is not None:
        _run_with_batch(batch)
    else:
        with GitCatFileBatch(git_top) as owned_batch:
            _run_with_batch(owned_batch)


def _verify_self_committed_git_artifact(
    git_top: Path | None,
    root: Path,
    entry: Path,
    artifact_full: Path,
    expected_sha256: str,
    *,
    batch: GitCatFileBatch | None = None,
) -> None:
    if git_top is None:
        raise ValueError(f"{entry}: source_revision 'self' requires a Git repository")
    if not entry.is_relative_to(root):
        raise ValueError(f"{entry}: source_revision 'self' requires evidence inside repository root")
    entry_git_rel = _compute_git_rel_lexical(git_top, root, entry, str(entry))
    artifact_git_rel = _compute_git_rel_lexical(git_top, root, artifact_full, f"{entry} output_artifact_path")

    if not artifact_full.is_file() or artifact_full.is_symlink():
        raise ValueError(f"{entry}: output artifact is missing or not a regular file: {artifact_git_rel}")
    read_bytes_nofollow(artifact_full)

    _assert_not_gitignored(git_top, entry_git_rel, entry)
    _assert_not_gitignored(git_top, artifact_git_rel, entry)

    head_proc = subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(git_top), "rev-parse", "--verify", "HEAD^{commit}"],
        capture_output=True,
        text=True,
    )
    if head_proc.returncode != 0:
        raise ValueError(f"{entry}: source_revision 'self' requires committed HEAD")

    ls_proc = subprocess.run(
        [
            "git",
            "--literal-pathspecs",
            "-C",
            str(git_top),
            "ls-files",
            "--error-unmatch",
            "--",
            entry_git_rel,
            artifact_git_rel,
        ],
        capture_output=True,
        text=True,
    )
    if ls_proc.returncode != 0:
        raise ValueError(
            f"{entry}: source_revision 'self' requires both evidence and artifact to be tracked in Git"
        )

    st_proc = subprocess.run(
        [
            "git",
            "--literal-pathspecs",
            "-C",
            str(git_top),
            "status",
            "--porcelain",
            "-z",
            "--",
            entry_git_rel,
            artifact_git_rel,
        ],
        capture_output=True,
    )
    if st_proc.returncode != 0 or st_proc.stdout != b"":
        raise ValueError(
            f"{entry}: source_revision 'self' requires clean committed working tree and index for evidence and artifact"
        )

    def _run_with_batch(active_batch: GitCatFileBatch) -> None:
        for label, git_rel in (("evidence", entry_git_rel), ("artifact", artifact_git_rel)):
            ho_proc = subprocess.run(
                ["git", "--literal-pathspecs", "-C", str(git_top), "hash-object", "--", git_rel],
                capture_output=True,
                text=True,
            )
            chk_head = active_batch.check(f"HEAD:{git_rel}")
            if (
                ho_proc.returncode != 0
                or chk_head is None
                or chk_head[1] != "blob"
                or ho_proc.stdout.strip() != chk_head[0]
            ):
                raise ValueError(
                    f"{entry}: working-tree {label} '{git_rel}' does not match committed HEAD blob"
                )

        log_proc = subprocess.run(
            [
                "git",
                "--literal-pathspecs",
                "-C",
                str(git_top),
                "log",
                "-n",
                "1",
                "--format=%H",
                "--",
                entry_git_rel,
            ],
            capture_output=True,
            text=True,
        )
        ev_rev = log_proc.stdout.strip().lower() if log_proc.returncode == 0 else ""
        if not HEX40_RE.fullmatch(ev_rev) or re.fullmatch(r"0+", ev_rev):
            raise ValueError(f"{entry}: unable to resolve latest commit for '{entry_git_rel}'")

        expected_lower = expected_sha256.strip().lower()
        for rev_label, rev_ref in (("evidence commit", ev_rev), ("HEAD", "HEAD")):
            _verify_regular_tree_mode(
                active_batch,
                entry,
                rev_ref,
                rev_label,
                entry_git_rel,
                f"{entry}: evidence '{entry_git_rel}' is unavailable at {rev_label} ({rev_ref})",
            )
            unavail_art = (
                f"{entry}: output artifact '{artifact_git_rel}' is unavailable at {rev_label} ({rev_ref})"
            )
            _verify_regular_tree_mode(
                active_batch,
                entry,
                rev_ref,
                rev_label,
                artifact_git_rel,
                unavail_art,
            )
            blob_bytes = active_batch.read_blob(f"{rev_ref}:{artifact_git_rel}")
            if blob_bytes is None:
                raise ValueError(unavail_art)
            if hashlib.sha256(blob_bytes).hexdigest() != expected_lower:
                raise ValueError(
                    f"{entry}: output artifact checksum does not match at {rev_label} ({rev_ref}:{artifact_git_rel})"
                )

    if batch is not None:
        _run_with_batch(batch)
    else:
        with GitCatFileBatch(git_top) as owned_batch:
            _run_with_batch(owned_batch)


def _verify_working_tree_artifact(
    entry: Path,
    artifact_full: Path,
    expected_sha256: str,
    *,
    require_digest: bool,
) -> None:
    art_bytes = read_bytes_nofollow(artifact_full)
    if not require_digest:
        return
    raw_digest = hashlib.sha256(art_bytes).hexdigest()
    lf_digest = (
        hashlib.sha256(art_bytes.replace(b"\r\n", b"\n")).hexdigest()
        if b"\r\n" in art_bytes
        else raw_digest
    )
    if expected_sha256.strip().lower() not in {raw_digest, lf_digest}:
        raise ValueError(f"{entry}: working-tree output artifact checksum does not match")


def _git_has_head_object(git_top: Path, git_rel: str, *, batch: GitCatFileBatch | None = None) -> bool:
    if batch is not None:
        return batch.tree_entry_mode("HEAD", git_rel) is not None
    with GitCatFileBatch(git_top) as owned_batch:
        return owned_batch.tree_entry_mode("HEAD", git_rel) is not None


def _load_evidence_corrections(
    root: Path,
    evidence_dirs: list[Path],
    explicit_evidence_dir: str | None,
) -> dict[str, dict[str, str]]:
    internal_evidence_dir = root / "docs/internal/task-evidence"
    if not (
        explicit_evidence_dir
        and len(evidence_dirs) == 1
        and evidence_dirs[0].exists()
        and internal_evidence_dir.exists()
        and not internal_evidence_dir.is_symlink()
        and evidence_dirs[0].resolve() == internal_evidence_dir.resolve()
    ):
        return {}
    corrections_path = walk_inside_root_no_symlinks(
        root,
        Path("docs/internal/task-evidence/evidence-corrections.json"),
        "evidence-corrections.json",
    )
    if not corrections_path.exists():
        return {}
    corrections = json.loads(read_text_nofollow(corrections_path))
    if corrections.get("schema_version") != 1 or not isinstance(corrections.get("corrections"), dict):
        raise ValueError("evidence corrections file is invalid")
    for corr_key, corr_val in corrections["corrections"].items():
        if not isinstance(corr_val, dict):
            raise ValueError(f"evidence corrections entry '{corr_key}' must be an object")
        if "source_revision" in corr_val:
            corr_rev = str(corr_val["source_revision"]).strip()
            if corr_rev.lower() == "self":
                raise ValueError(f"evidence-corrections.json forbids 'self' for '{corr_key}'")
            if not HEX40_RE.fullmatch(corr_rev) or re.fullmatch(r"0+", corr_rev):
                raise ValueError(f"evidence-corrections.json invalid source_revision for '{corr_key}'")
    return corrections["corrections"]  # type: ignore[return-value]


def _validate_draft_working_tree(
    root: Path,
    git_top: Path | None,
    entry: Path,
    data: dict[str, str],
) -> None:
    if git_top is not None and entry.is_relative_to(root):
        _assert_not_gitignored(
            git_top,
            _compute_git_rel_lexical(git_top, root, entry, str(entry)),
            entry,
        )
    if not data.get("output_artifact_path"):
        return
    raw_art = data["output_artifact_path"].replace("\\", "/").strip()
    if raw_art.startswith(":"):
        raise ValueError(f"{entry}: output_artifact_path cannot start with ':'")
    if raw_art.lower() in PLACEHOLDER_VALUES:
        return
    art_full = walk_inside_root_no_symlinks(root, Path(raw_art), str(entry))
    if git_top is not None and entry.is_relative_to(root):
        _assert_not_gitignored(
            git_top,
            _compute_git_rel_lexical(git_top, root, art_full, str(entry)),
            entry,
        )
    raw_sha = data.get("output_artifact_sha256", "").strip().lower()
    _verify_working_tree_artifact(
        entry,
        art_full,
        raw_sha,
        require_digest=bool(raw_sha and raw_sha not in PLACEHOLDER_VALUES),
    )


def _validate_self_evidence(
    root: Path,
    git_top: Path | None,
    entry: Path,
    artifact_full: Path,
    expected_sha256: str,
    allow_working_tree: bool,
    *,
    batch: GitCatFileBatch | None = None,
) -> None:
    if not allow_working_tree:
        _verify_self_committed_git_artifact(
            git_top, root, entry, artifact_full, expected_sha256, batch=batch
        )
        return
    if git_top is None:
        raise ValueError(f"{entry}: source_revision 'self' requires a Git repository")
    if not entry.is_relative_to(root):
        raise ValueError(f"{entry}: source_revision 'self' requires evidence inside repository root")
    entry_git_rel = _compute_git_rel_lexical(git_top, root, entry, str(entry))
    artifact_git_rel = _compute_git_rel_lexical(git_top, root, artifact_full, f"{entry} output_artifact_path")
    _assert_not_gitignored(git_top, entry_git_rel, entry)
    _assert_not_gitignored(git_top, artifact_git_rel, entry)

    head_proc = subprocess.run(
        ["git", "--literal-pathspecs", "-C", str(git_top), "rev-parse", "--verify", "HEAD^{commit}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if head_proc.returncode == 0 and any(
        _git_has_head_object(git_top, rel, batch=batch)
        for rel in (entry_git_rel, artifact_git_rel)
    ):
        _verify_self_committed_git_artifact(
            git_top, root, entry, artifact_full, expected_sha256, batch=batch
        )
        return
    _verify_working_tree_artifact(entry, artifact_full, expected_sha256, require_digest=True)


def _validate_completed_entry(
    root: Path,
    git_top: Path | None,
    entry: Path,
    text: str,
    data: dict[str, str],
    corrections_map: dict[str, dict[str, str]],
    allow_working_tree: bool,
    *,
    batch: GitCatFileBatch | None = None,
) -> None:
    require_fields(
        data,
        [
            "task_id",
            "recorded_at",
            "recorded_by",
            "source_revision",
            "completed_at",
            "reviewer",
            "environment",
            "output_artifact_sha256",
            "output_artifact_path",
        ],
        entry,
    )
    if not re.search(r"\| AC-[^|]+\|\s*[^|\s].*\|\s*[^|\s].*\|\s*[^|\s].*\|", text):
        raise ValueError(f"{entry}: completed task needs a non-empty AC validation row")

    raw_artifact_str = data["output_artifact_path"].replace("\\", "/").strip()
    if raw_artifact_str.startswith(":"):
        raise ValueError(f"{entry}: output_artifact_path cannot start with ':'")
    artifact_rel = Path(raw_artifact_str)
    if artifact_rel.is_absolute():
        raise ValueError(f"{entry}: output artifact path escapes repository root")
    artifact_full = walk_inside_root_no_symlinks(root, artifact_rel, f"{entry} output_artifact_path")

    correction_key = entry.relative_to(root).as_posix() if entry.is_relative_to(root) else None
    correction = corrections_map.get(correction_key, {}) if correction_key else {}
    raw_src_rev = data["source_revision"].strip()

    if "source_revision" in correction:
        revision = str(correction["source_revision"]).strip()
        _verify_40hex_git_artifact(
            git_top,
            root,
            entry,
            revision,
            artifact_full,
            data["output_artifact_sha256"],
            raw_src_rev,
            batch=batch,
        )
    elif raw_src_rev == "self":
        _validate_self_evidence(
            root,
            git_top,
            entry,
            artifact_full,
            data["output_artifact_sha256"],
            allow_working_tree,
            batch=batch,
        )
    elif HEX40_RE.fullmatch(raw_src_rev) and not re.fullmatch(r"0+", raw_src_rev):
        _verify_40hex_git_artifact(
            git_top,
            root,
            entry,
            raw_src_rev,
            artifact_full,
            data["output_artifact_sha256"],
            raw_src_rev,
            batch=batch,
        )
    else:
        raise ValueError(
            f"{entry}: source revision must be 'self' or a full lowercase 40-hex Git SHA (got '{raw_src_rev}')"
        )


def _validate_verified_inventory(root: Path) -> None:
    if not ((root / "docs").exists() or (root / "docs").is_symlink()):
        return
    inventory = walk_inside_root_no_symlinks(
        root,
        Path("docs/current/02 - Architecture/Generated Reference Inventory.md"),
        "Generated Reference Inventory.md",
    )
    if inventory.is_symlink():
        raise ValueError(f"{inventory}: symlink refused")
    if not inventory.is_file():
        return
    inv_data = parse_evidence_frontmatter(read_text_nofollow(inventory), inventory)
    if inv_data.get("verified", "").strip().lower() != "true":
        return
    require_fields(
        inv_data,
        [
            "generated_at",
            "source_revision",
            "generation_command",
            "artifact_path",
            "scope",
            "verified_at",
            "verified_by",
            "verification_method",
            "verification_evidence",
            "artifact_checksum",
            "valid_until",
        ],
        inventory,
    )
    try:
        expiry = dt.date.fromisoformat(inv_data["valid_until"][:10])
    except ValueError as exc:
        raise ValueError(f"{inventory}: valid_until must start with ISO date") from exc
    if expiry < dt.date.today():
        raise ValueError(f"{inventory}: verified inventory is expired")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root (defaults to parent directory of this script).",
    )
    parser.add_argument("--evidence-dir", help="Validate only this evidence directory.")
    parser.add_argument("--require-completed", action="store_true")
    parser.add_argument(
        "--allow-working-tree",
        action="store_true",
        help="Validate draft or uncommitted source_revision: self evidence against the working tree before commit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.allow_working_tree and args.require_completed:
        raise ValueError("--allow-working-tree cannot be combined with --require-completed")

    if args.root.is_symlink():
        raise ValueError(f"repository root cannot be a symlink: {args.root}")
    root = args.root.resolve()
    git_top = _resolve_git_toplevel(root)

    default_evidence_dir = root / "task-evidence"
    legacy_evidence_dir = root / "docs/current/00 - Onboarding/task-evidence"

    if args.evidence_dir:
        evidence_dirs = [resolve_evidence_dir_safe(root, args.evidence_dir)]
    else:
        walk_inside_root_no_symlinks(root, Path("task-evidence"), "task-evidence")
        evidence_dirs = [default_evidence_dir]
        if legacy_evidence_dir.is_symlink():
            raise ValueError(f"symlink refused: {legacy_evidence_dir}")
        if legacy_evidence_dir.is_dir():
            walk_inside_root_no_symlinks(
                root, Path("docs/current/00 - Onboarding/task-evidence"), "legacy task-evidence"
            )
            evidence_dirs.append(legacy_evidence_dir)

    if not any(path.is_dir() and not path.is_symlink() for path in evidence_dirs) and args.require_completed:
        raise ValueError(f"evidence directory does not exist: {evidence_dirs[0]}")

    corrections_map = _load_evidence_corrections(root, evidence_dirs, args.evidence_dir)
    completed_records = 0

    def _scan_dirs(active_batch: GitCatFileBatch | None) -> None:
        nonlocal completed_records
        for evidence_dir in evidence_dirs:
            if evidence_dir.is_symlink():
                raise ValueError(f"{evidence_dir}: symlink refused for evidence directory")
            if not evidence_dir.is_dir():
                continue
            for entry in sorted(evidence_dir.iterdir(), key=lambda p: p.name):
                if not entry.name.endswith(".md") or entry.name.startswith("_"):
                    continue
                if entry.is_symlink():
                    raise ValueError(f"{entry}: symlink refused in evidence directory")
                if not entry.is_file():
                    continue

                text = read_text_nofollow(entry)
                data = parse_evidence_frontmatter(text, entry)
                status = data.get("status", "").strip().lower()
                if status not in VALID_EVIDENCE_STATUSES:
                    raise ValueError(
                        f"{entry}: invalid or missing frontmatter status '{status or 'missing'}' "
                        f"(expected one of: {', '.join(sorted(VALID_EVIDENCE_STATUSES))})"
                    )

                if status == "template":
                    continue
                if status == "draft":
                    if args.allow_working_tree:
                        _validate_draft_working_tree(root, git_top, entry, data)
                    continue

                completed_records += 1
                _validate_completed_entry(
                    root,
                    git_top,
                    entry,
                    text,
                    data,
                    corrections_map,
                    args.allow_working_tree,
                    batch=active_batch,
                )

    if git_top is not None:
        with GitCatFileBatch(git_top) as shared_batch:
            _scan_dirs(shared_batch)
    else:
        _scan_dirs(None)

    if args.require_completed and completed_records == 0:
        raise ValueError("no completed task evidence record found")

    _validate_verified_inventory(root)

    if not args.evidence_dir and legacy_evidence_dir.is_dir():
        print(f"WARN: validating legacy evidence directory during migration: {legacy_evidence_dir.relative_to(root)}")
    print("PASS: task evidence and inventory validation")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
