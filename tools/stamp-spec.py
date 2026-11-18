#!/usr/bin/env python3
"""Atomically stamp feature spec approval, Spec Amendment (--amend), and supersession."""

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REQUIRED_DV_SYMBOLS = (
    "APPROVAL_FIELDS",
    "FORBIDDEN_APPROVED_PLACEHOLDERS",
    "HEX40_RE",
    "MINI_SPEC_FILE",
    "NUMBERED_SPEC_FILES",
    "_find_any_approved_history",
    "_resolve_superseded_by_single",
    "_validate_governance_frontmatter",
    "_validate_supersedes_field",
    "_verify_source_revision_and_baseline",
    "_walk_lexical_no_symlink",
    "is_source_template_repository",
    "parse_frontmatter",
    "read_markdown",
    "require",
    "resolve_active_feature_dir",
    "resolve_git_toplevel",
    "validate_clarify_gate",
    "validate_feature_specs",
    "validate_links",
    "validate_mermaid",
)

try:
    import docs_validation as _dv  # noqa: E402
except ImportError as exc:
    print(
        f"FAIL: stamp-spec.py requires docs_validation.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update' to restore the validator bundle): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

missing_dv = [sym for sym in REQUIRED_DV_SYMBOLS if not hasattr(_dv, sym)]
if missing_dv:
    print(
        f"FAIL: stamp-spec.py requires an up-to-date docs_validation.py in {SCRIPT_DIR} "
        f"(missing: {', '.join(missing_dv)}; run 'setup.sh --update' to restore the validator bundle)",
        file=sys.stderr,
    )
    sys.exit(1)

FORBIDDEN_APPROVED_PLACEHOLDERS = _dv.FORBIDDEN_APPROVED_PLACEHOLDERS
HEX40_RE = _dv.HEX40_RE
MINI_SPEC_FILE = _dv.MINI_SPEC_FILE
NUMBERED_SPEC_FILES = _dv.NUMBERED_SPEC_FILES
_find_any_approved_history = _dv._find_any_approved_history
_resolve_superseded_by_single = _dv._resolve_superseded_by_single
_validate_governance_frontmatter = _dv._validate_governance_frontmatter
_validate_supersedes_field = _dv._validate_supersedes_field
_verify_source_revision_and_baseline = _dv._verify_source_revision_and_baseline
_walk_lexical_no_symlink = _dv._walk_lexical_no_symlink
is_source_template_repository = _dv.is_source_template_repository
parse_frontmatter = _dv.parse_frontmatter
read_markdown = _dv.read_markdown
require = _dv.require
resolve_active_feature_dir = _dv.resolve_active_feature_dir
resolve_git_toplevel = _dv.resolve_git_toplevel
validate_clarify_gate = _dv.validate_clarify_gate
validate_feature_specs = _dv.validate_feature_specs
validate_links = _dv.validate_links
validate_mermaid = _dv.validate_mermaid

DEFAULT_ROOT = SCRIPT_DIR.parent
FRONTMATTER_RE = re.compile(r"\A(\ufeff?---\r?\n)(.*?)(\r?\n---(?:\r?\n|\Z))", re.S)
ISO_DATE_OR_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)


def _read_bytes_nofollow(path: Path) -> tuple[bytes, int]:
    require(not path.is_symlink(), f"{path}: symlink refused")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{path}: unable to open regular file safely ({exc})") from exc
    try:
        st = os.fstat(fd)
        require(stat.S_ISREG(st.st_mode), f"{path}: expected regular file")
        chunks: list[bytes] = []
        while True:
            buf = os.read(fd, 65536)
            if not buf:
                break
            chunks.append(buf)
        return b"".join(chunks), stat.S_IMODE(st.st_mode)
    finally:
        os.close(fd)


def _atomic_write_bytes(path: Path, data: bytes, mode: int) -> None:
    require(not path.is_symlink(), f"{path}: symlink refused before write")
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        view = memoryview(data)
        total = 0
        while total < len(view):
            written = os.write(fd, view[total:])
            if written <= 0:
                raise OSError("short write while writing temporary file")
            total += written
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, path)
    except BaseException:
        if fd >= 0:
            try:
                os.close(fd)
            except OSError:
                pass
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def _validate_free_scalar(value: str, flag_name: str) -> str:
    cleaned = value.strip()
    require(bool(cleaned), f"{flag_name} must not be empty")
    require(
        cleaned.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
        f"{flag_name} forbids placeholder value '{cleaned}'",
    )
    require(
        not any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned),
        f"{flag_name} cannot contain control characters or newlines",
    )
    require("\\" not in cleaned, f"{flag_name} cannot contain raw backslash '\\'")
    return cleaned


def _validate_at_scalar(raw_at: str) -> str:
    cleaned = _validate_free_scalar(raw_at, "--at")
    require(
        bool(ISO_DATE_OR_DT_RE.fullmatch(cleaned)),
        f"--at must be an ISO-8601 date (YYYY-MM-DD) or timestamp (got '{cleaned}')",
    )
    try:
        if len(cleaned) == 10:
            dt.date.fromisoformat(cleaned)
        else:
            iso_norm = cleaned[:-1] + "+00:00" if cleaned.endswith("Z") else cleaned
            dt.datetime.fromisoformat(iso_norm)
    except ValueError as exc:
        raise ValueError(f"--at is not a valid ISO-8601 date/timestamp '{cleaned}': {exc}") from exc
    return cleaned


def _update_frontmatter_fields(
    raw_text: str,
    rel_label: str,
    updates: list[tuple[str, str]],
) -> str:
    match = FRONTMATTER_RE.match(raw_text)
    require(match is not None, f"{rel_label}: missing YAML frontmatter block")
    assert match is not None
    fm_open, fm_body, fm_close = match.groups()
    newline = "\r\n" if "\r\n" in fm_open or "\r\n" in fm_body else "\n"
    lines = fm_body.splitlines()

    update_map = dict(updates)
    replaced: set[str] = set()
    out_lines: list[str] = []
    status_idx: int | None = None

    for line in lines:
        if not line.startswith((" ", "\t")) and ":" in line and not line.lstrip().startswith(("#", "-")):
            key = line.split(":", 1)[0].strip()
            if key in update_map:
                out_lines.append(f"{key}: {update_map[key]}")
                replaced.add(key)
                if key == "status":
                    status_idx = len(out_lines) - 1
                continue
            if key == "status":
                status_idx = len(out_lines)
        out_lines.append(line)

    missing_lines = [f"{k}: {v}" for k, v in updates if k not in replaced]
    if missing_lines:
        insert_at = (status_idx + 1) if status_idx is not None else len(out_lines)
        out_lines = out_lines[:insert_at] + missing_lines + out_lines[insert_at:]

    return fm_open + newline.join(out_lines) + fm_close + raw_text[match.end() :]


def _scan_docs_current_no_symlinks(root: Path) -> tuple[Path, Path, list[Path]]:
    docs = _walk_lexical_no_symlink(
        root,
        root,
        "docs",
        escape_msg="docs escapes project root",
        symlink_msg="docs must not be a symlink",
        err_prefix="stamp-spec",
    )
    current = _walk_lexical_no_symlink(
        root,
        root,
        "docs/current",
        escape_msg="docs/current escapes project root",
        symlink_msg="docs/current must not be a symlink",
        err_prefix="stamp-spec",
    )
    require(current.is_dir(), "docs/current is missing")

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(current, followlinks=False):
        dp = Path(dirpath)
        for dname in sorted(dirnames):
            cand_dir = dp / dname
            require(
                not cand_dir.is_symlink(),
                f"{cand_dir.relative_to(root).as_posix()}: symlinked directory inside docs/current refused",
            )
        for fname in sorted(filenames):
            if fname.endswith(".md"):
                cand_file = dp / fname
                require(
                    not cand_file.is_symlink(),
                    f"{cand_file.relative_to(root).as_posix()}: Markdown document must not be a symlink",
                )
                files.append(cand_file)
    files.sort()
    require(bool(files), "docs/current has no Markdown documents")
    return docs, current, files


def _verify_tree_no_symlinks(tree_root: Path, repo_root: Path) -> None:
    require(not tree_root.is_symlink(), f"{tree_root.relative_to(repo_root)}: symlink refused")
    for dirpath, dirnames, filenames in os.walk(tree_root, followlinks=False):
        dp = Path(dirpath)
        for name in dirnames + filenames:
            cand = dp / name
            require(
                not cand.is_symlink(),
                f"{cand.relative_to(repo_root).as_posix()}: symlink inside docs/ refused during --dry-run",
            )


def _run_strict_docs_validation(
    root: Path,
    *,
    external_root: Path | None = None,
    git_root: Path | None = None,
) -> list[str]:
    docs, current, files = _scan_docs_current_no_symlinks(root)
    validate_links(root, docs, files, external_root=external_root)
    validate_mermaid(root, files)
    clarify_warnings = validate_clarify_gate(root, files, strict=True, git_root=git_root)
    spec_warnings = validate_feature_specs(
        root,
        current / "05 - Product Features",
        require_tasks=True,
        strict=True,
        git_root=git_root,
    )
    return list(dict.fromkeys(clarify_warnings + spec_warnings))


def _resolve_head_sha(root: Path) -> str:
    git_top = resolve_git_toplevel(root)
    require(git_top is not None, "stamp-spec.py requires a Git repository with committed HEAD")
    try:
        proc = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(root), "rev-parse", "--verify", "HEAD^{commit}"],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError(f"git binary unavailable to resolve HEAD: {exc}") from exc
    require(
        proc.returncode == 0,
        "git rev-parse --verify HEAD^{commit} failed (create an initial commit before stamping specs)",
    )
    sha = proc.stdout.strip().lower()
    require(
        bool(HEX40_RE.fullmatch(sha)) and not re.fullmatch(r"0+", sha),
        f"invalid HEAD commit SHA returned by git: '{sha}'",
    )
    return sha


def _collect_pack_layout(feature_dir: Path, root: Path) -> tuple[list[Path], bool]:
    rel_feature = feature_dir.relative_to(root).as_posix()
    p_mini = feature_dir / MINI_SPEC_FILE
    numbered = [feature_dir / name for name in sorted(NUMBERED_SPEC_FILES)]
    for cand in (p_mini, *numbered):
        require(
            not cand.is_symlink(),
            f"{cand.relative_to(root).as_posix()}: spec file must not be a symlink",
        )
    if p_mini.is_file():
        mixed = [p.name for p in numbered if p.exists()]
        require(
            not mixed,
            f"{rel_feature}: cannot mix '{MINI_SPEC_FILE}' with 4-file spec pack ({', '.join(mixed)})",
        )
        return [p_mini], True
    missing = [p.name for p in numbered if not p.is_file()]
    require(
        not missing,
        f"{rel_feature}: incomplete Tier L feature pack (missing: {', '.join(missing)})",
    )
    return numbered, False


def _read_pack_specs(
    root: Path,
    spec_files: list[Path],
) -> tuple[dict[Path, tuple[bytes, int]], dict[Path, str], dict[Path, dict[str, str]]]:
    raw_bytes: dict[Path, tuple[bytes, int]] = {}
    texts: dict[Path, str] = {}
    fms: dict[Path, dict[str, str]] = {}
    for spec_path in spec_files:
        raw_b, mode = _read_bytes_nofollow(spec_path)
        raw_bytes[spec_path] = (raw_b, mode)
        text = raw_b.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
        _validate_governance_frontmatter(spec_path.relative_to(root), text)
        texts[spec_path] = text
        fms[spec_path] = parse_frontmatter(text)
    return raw_bytes, texts, fms


def _build_planned_write(
    root: Path,
    spec_path: Path,
    raw_bytes_map: dict[Path, tuple[bytes, int]],
    updates: list[tuple[str, str]],
) -> tuple[Path, str, bytes, int]:
    raw_b, mode = raw_bytes_map[spec_path]
    updated_str = _update_frontmatter_fields(
        raw_b.decode("utf-8-sig"),
        spec_path.relative_to(root).as_posix(),
        updates,
    )
    return spec_path, updated_str, raw_b, mode


def _emit_warnings(warnings: list[str]) -> None:
    for warning in warnings:
        print(f"WARN: {warning}", file=sys.stderr)


def _plan_supersession_writes(
    root: Path,
    new_dir: Path,
    is_new_mini: bool,
    new_pack_fms: dict[Path, dict[str, str]],
) -> tuple[list[tuple[Path, str, bytes, int]], str | None]:
    supersedes_vals = {p: fm.get("supersedes", "").strip() for p, fm in new_pack_fms.items()}
    if not any(supersedes_vals.values()):
        return [], None

    require(
        all(supersedes_vals.values()),
        f"{new_dir.relative_to(root).as_posix()}: all specs in a 4-file pack must declare frontmatter 'supersedes'",
    )
    old_dirs = {
        _validate_supersedes_field(root, p, fm, strict=False)
        for p, fm in new_pack_fms.items()
    }
    require(
        len(old_dirs) == 1,
        f"{new_dir.relative_to(root).as_posix()}: divergent 'supersedes' target folders across pack",
    )
    old_dir = next(iter(old_dirs))
    rel_old_dir = old_dir.relative_to(root).as_posix()
    old_files, is_old_mini = _collect_pack_layout(old_dir, root)
    old_raw_bytes, old_texts, old_fms = _read_pack_specs(root, old_files)

    old_statuses = {old_fms[p].get("status", "").strip().lower() for p in old_files}
    require(
        len(old_statuses) == 1,
        f"{rel_old_dir}: mixed feature pack status across superseded target specs",
    )
    old_status = next(iter(old_statuses))
    require(
        old_status != "archived",
        f"{rel_old_dir}: cannot supersede an archived feature pack",
    )
    require(
        old_status in {"draft", "approved", "superseded"},
        f"{rel_old_dir}: unsupported status '{old_status or 'missing'}' on supersedes target",
    )

    for old_spec in old_files:
        old_fm = old_fms[old_spec]
        old_rel = old_spec.relative_to(root).as_posix()
        hist = _find_any_approved_history(root, old_rel)
        was_approved = old_status == "approved" or bool(old_fm.get("source_revision", "").strip()) or (hist is not None)
        if was_approved:
            _verify_source_revision_and_baseline(
                root,
                old_spec,
                old_texts[old_spec],
                old_fm,
                strict=True,
                status_label=old_status,
                require_git_baseline=(hist is not None),
            )

    new_folder = new_dir.name
    if old_status == "superseded":
        for old_spec in old_files:
            _resolved, scope = _resolve_superseded_by_single(
                root,
                old_spec,
                old_fms[old_spec].get("superseded_by", ""),
            )
            require(
                scope == ("feature", new_folder),
                f"{old_spec.relative_to(root).as_posix()}: already superseded by '{scope[1]}' (not '{new_folder}')",
            )
        return [], rel_old_dir

    planned: list[tuple[Path, str, bytes, int]] = []
    for old_spec in old_files:
        if is_new_mini:
            target_rel = f"05 - Product Features/{new_folder}/{MINI_SPEC_FILE}"
        elif not is_old_mini:
            target_rel = f"05 - Product Features/{new_folder}/{old_spec.name}"
        else:
            target_rel = f"05 - Product Features/{new_folder}/1. Product Spec.md"
        require('"' not in target_rel, f"invalid double quote in superseded_by target '{target_rel}'")
        planned.append(
            _build_planned_write(
                root,
                old_spec,
                old_raw_bytes,
                [
                    ("status", "superseded"),
                    ("superseded_by", json.dumps(target_rel, ensure_ascii=False)),
                ],
            )
        )
    return planned, rel_old_dir


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "feature",
        help="Feature folder (<NNN-slug>), stripped slug (<slug>), or repo-relative path under docs/current/05 - Product Features/.",
    )
    parser.add_argument("--by", required=True, help="Approver name/role recorded in approved_by.")
    parser.add_argument(
        "--evidence",
        required=True,
        help="Approval reference (e.g. PR link, session ID, review note) recorded in approval_evidence.",
    )
    parser.add_argument(
        "--at",
        default=dt.date.today().isoformat(),
        help="ISO-8601 approval date (YYYY-MM-DD) or timestamp (defaults to today).",
    )
    parser.add_argument(
        "--amend",
        action="store_true",
        help="Refresh approval metadata and source_revision on an already-approved pack (Spec Amendment).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Stage edits in an isolated temporary copy of docs/ and run full strict validation without writing.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root containing docs/current (defaults to parent directory of tools/).",
    )
    return parser.parse_args(argv)


def _run_dry_run(
    root: Path,
    rel_feature: str,
    head_sha: str,
    amend: bool,
    planned_writes: list[tuple[Path, str, bytes, int]],
    superseded_rel: str | None,
    has_sup_writes: bool,
) -> int:
    docs_src = root / "docs"
    _verify_tree_no_symlinks(docs_src, root)

    with tempfile.TemporaryDirectory() as td:
        tmp_root = Path(td).resolve()
        shutil.copytree(docs_src, tmp_root / "docs", symlinks=True)

        for orig_path, new_text, _orig_b, mode in planned_writes:
            staged_path = tmp_root / orig_path.relative_to(root)
            _atomic_write_bytes(staged_path, new_text.encode("utf-8"), mode)

        warnings = _run_strict_docs_validation(
            tmp_root,
            external_root=root,
            git_root=root,
        )

    _emit_warnings(warnings)
    action = "amend" if amend else "approve"
    print(f"DRY-RUN: would {action} {rel_feature} at {head_sha} (files: {len(planned_writes)})")
    for orig_path, _new_text, _orig_b, _mode in planned_writes:
        print(f"  {orig_path.relative_to(root).as_posix()}")
    if superseded_rel and not has_sup_writes:
        print(f"  (preserved already-superseded {superseded_rel})")
    return 0


def _apply_and_validate_writes(
    root: Path,
    rel_feature: str,
    head_sha: str,
    amend: bool,
    planned_writes: list[tuple[Path, str, bytes, int]],
) -> int:
    originals = [(path, orig_b, mode) for path, _new_text, orig_b, mode in planned_writes]
    try:
        for path, new_text, _orig_b, mode in planned_writes:
            _atomic_write_bytes(path, new_text.encode("utf-8"), mode)
        warnings = _run_strict_docs_validation(root)
    except BaseException as exc:
        for orig_path, orig_bytes, orig_mode in originals:
            try:
                _atomic_write_bytes(orig_path, orig_bytes, orig_mode)
            except BaseException:
                pass
        if isinstance(exc, KeyboardInterrupt):
            print("FAIL: interrupted; rolled back all spec changes", file=sys.stderr)
            return 130
        raise

    _emit_warnings(warnings)
    action = "amended" if amend else "approved"
    print(f"PASS: {action} {rel_feature} at {head_sha} (files updated: {len(planned_writes)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require(not args.root.is_symlink(), f"project root cannot be a symlink: {args.root}")
    probe_git_top = resolve_git_toplevel(args.root)
    if probe_git_top is not None and hasattr(_dv, "_verify_git_root_no_symlink"):
        if args.root.resolve().is_relative_to(probe_git_top):
            _dv._verify_git_root_no_symlink(args.root, probe_git_top, err_prefix="stamp-spec")
    root = args.root.resolve()

    if not args.dry_run and is_source_template_repository(root):
        raise ValueError(
            "refusing to stamp feature specs inside the source ai-project-template repository "
            "(install into a target project first, or pass --dry-run to preview)"
        )

    approved_by = _validate_free_scalar(args.by, "--by")
    approval_evidence = _validate_free_scalar(args.evidence, "--evidence")
    approved_at = _validate_at_scalar(args.at)

    _scan_docs_current_no_symlinks(root)
    head_sha = _resolve_head_sha(root)

    feature_dir = resolve_active_feature_dir(
        root,
        args.feature,
        require_approved=False,
        exclude_all_done=False,
    )
    rel_feature = feature_dir.relative_to(root).as_posix()
    pack_files, is_mini = _collect_pack_layout(feature_dir, root)
    pack_raw_bytes, _pack_texts, pack_fms = _read_pack_specs(root, pack_files)

    statuses = {pack_fms[p].get("status", "").strip().lower() for p in pack_files}
    require(
        len(statuses) == 1,
        f"{rel_feature}: mixed feature pack status across specs",
    )
    curr_status = next(iter(statuses))
    if args.amend:
        require(
            curr_status == "approved",
            f"{rel_feature}: --amend requires status 'approved' across all pack files (found '{curr_status}')",
        )
    else:
        require(
            curr_status == "draft",
            f"{rel_feature}: pack has status '{curr_status}' "
            "(expected 'draft'; pass --amend after explicit user re-approval to amend an approved pack)",
        )

    approval_updates = [
        ("status", "approved"),
        ("approved_by", json.dumps(approved_by, ensure_ascii=False)),
        ("approved_at", json.dumps(approved_at, ensure_ascii=False)),
        ("approval_evidence", json.dumps(approval_evidence, ensure_ascii=False)),
        ("source_revision", head_sha),
    ]
    planned_writes = [_build_planned_write(root, spec_path, pack_raw_bytes, approval_updates) for spec_path in pack_files]
    sup_writes, superseded_rel = _plan_supersession_writes(root, feature_dir, is_mini, pack_fms)
    planned_writes.extend(sup_writes)

    if args.dry_run:
        return _run_dry_run(root, rel_feature, head_sha, args.amend, planned_writes, superseded_rel, bool(sup_writes))
    return _apply_and_validate_writes(root, rel_feature, head_sha, args.amend, planned_writes)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
