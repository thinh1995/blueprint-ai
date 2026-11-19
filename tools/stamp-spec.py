#!/usr/bin/env python3
"""Atomically stamp feature spec approval, Spec Amendment (--amend), and supersession."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

REQUIRED_CORE_SYMBOLS = (
    "FORBIDDEN_APPROVED_PLACEHOLDERS",
    "HEX40_RE",
    "HEX64_RE",
    "SDD_CORE_API_VERSION",
    "atomic_write_bytes",
    "is_source_template_repository",
    "parse_frontmatter",
    "read_bytes_nofollow",
    "require",
    "resolve_git_toplevel",
    "verify_git_root_no_symlink",
    "walk_lexical_no_symlink",
)

try:
    import _sdd_core  # noqa: E402
except ImportError as exc:
    print(
        f"FAIL: stamp-spec.py requires tools/_sdd_core.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if user-owned): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

missing_core = [sym for sym in REQUIRED_CORE_SYMBOLS if not hasattr(_sdd_core, sym)]
if getattr(_sdd_core, "SDD_CORE_API_VERSION", 0) < 1 or missing_core:
    print(
        f"FAIL: stamp-spec.py requires an up-to-date tools/_sdd_core.py (SDD_CORE_API_VERSION >= 1) in {SCRIPT_DIR} "
        "(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if tools/_sdd_core.py is user-owned)",
        file=sys.stderr,
    )
    sys.exit(1)

REQUIRED_DV_SYMBOLS = (
    "APPROVAL_FIELDS",
    "FORBIDDEN_APPROVED_PLACEHOLDERS",
    "HEX40_RE",
    "HEX64_RE",
    "MINI_SPEC_FILE",
    "NUMBERED_SPEC_FILES",
    "_find_all_approved_entries",
    "_find_any_approved_history",
    "_hist_contract_sha_for_entry",
    "_resolve_superseded_by_single",
    "_validate_governance_frontmatter",
    "_validate_supersedes_field",
    "_verify_source_revision_and_baseline",
    "_walk_lexical_no_symlink",
    "compute_contract_sha256",
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
        f"(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if docs_validation.py is user-owned): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

missing_dv = [sym for sym in REQUIRED_DV_SYMBOLS if not hasattr(_dv, sym)]
if missing_dv:
    print(
        f"FAIL: stamp-spec.py requires an up-to-date docs_validation.py in {SCRIPT_DIR} "
        f"(missing: {', '.join(missing_dv)}; run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if docs_validation.py is user-owned)",
        file=sys.stderr,
    )
    sys.exit(1)

FORBIDDEN_APPROVED_PLACEHOLDERS = _sdd_core.FORBIDDEN_APPROVED_PLACEHOLDERS
HEX40_RE = _sdd_core.HEX40_RE
MINI_SPEC_FILE = _dv.MINI_SPEC_FILE
NUMBERED_SPEC_FILES = _dv.NUMBERED_SPEC_FILES
_atomic_write_bytes = _sdd_core.atomic_write_bytes
_find_all_approved_entries = _dv._find_all_approved_entries
_find_any_approved_history = _dv._find_any_approved_history
_hist_contract_sha_for_entry = _dv._hist_contract_sha_for_entry
_read_bytes_nofollow = _sdd_core.read_bytes_nofollow
_resolve_superseded_by_single = _dv._resolve_superseded_by_single
_validate_governance_frontmatter = _dv._validate_governance_frontmatter
_validate_supersedes_field = _dv._validate_supersedes_field
_verify_git_root_no_symlink = _sdd_core.verify_git_root_no_symlink
_verify_source_revision_and_baseline = _dv._verify_source_revision_and_baseline
_walk_lexical_no_symlink = _sdd_core.walk_lexical_no_symlink
compute_contract_sha256 = _dv.compute_contract_sha256
is_source_template_repository = _sdd_core.is_source_template_repository
parse_frontmatter = _sdd_core.parse_frontmatter
read_markdown = _dv.read_markdown
require = _sdd_core.require
resolve_active_feature_dir = _dv.resolve_active_feature_dir
resolve_git_toplevel = _sdd_core.resolve_git_toplevel
validate_clarify_gate = _dv.validate_clarify_gate
validate_feature_specs = _dv.validate_feature_specs
validate_links = _dv.validate_links
validate_mermaid = _dv.validate_mermaid

DEFAULT_ROOT = SCRIPT_DIR.parent
FRONTMATTER_RE = re.compile(r"\A(\ufeff?---\r?\n)(.*?)(\r?\n---(?:\r?\n|\Z))", re.S)
ISO_DATE_OR_DT_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?)?$"
)


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


def _parse_iso_to_utc_epoch(raw_at: str) -> tuple[str, int] | None:
    cleaned = raw_at.strip()
    if not cleaned or not ISO_DATE_OR_DT_RE.fullmatch(cleaned):
        return None
    try:
        if len(cleaned) == 10:
            d = dt.date.fromisoformat(cleaned)
            utc_dt = dt.datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=dt.timezone.utc)
            return cleaned, int(utc_dt.timestamp())
        iso_norm = cleaned[:-1] + "+00:00" if cleaned.endswith("Z") else cleaned
        parsed = dt.datetime.fromisoformat(iso_norm)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        else:
            parsed = parsed.astimezone(dt.timezone.utc)
        return cleaned[:10], int(math.floor(parsed.timestamp()))
    except ValueError:
        return None


def _update_frontmatter_fields(
    raw_text: str,
    rel_label: str,
    updates: list[tuple[str, str | None]],
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
                new_val = update_map[key]
                replaced.add(key)
                if new_val is None:
                    continue
                out_lines.append(f"{key}: {new_val}")
                if key == "status":
                    status_idx = len(out_lines) - 1
                continue
            if key == "status":
                status_idx = len(out_lines)
        out_lines.append(line)

    missing_lines = [f"{k}: {v}" for k, v in updates if k not in replaced and v is not None]
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
        "git rev-parse --verify HEAD^{commit} failed (create an initial commit before stamping specs with --mode head-sha)",
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
    updates: list[tuple[str, str | None]],
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


def _resolve_pack_approved_at(
    root: Path,
    pack_files: list[Path],
    pack_texts: dict[Path, str],
    pack_fms: dict[Path, dict[str, str]],
    *,
    raw_at_arg: str | None,
    amend: bool,
    effective_mode: str,
    approved_by: str,
    approval_evidence: str,
    head_sha: str,
    new_contract_shas: dict[Path, str],
) -> str:
    hist_by_spec: dict[Path, list[tuple[str, str, dict[str, str]]]] = {
        p: _find_all_approved_entries(root, p.relative_to(root).as_posix())
        for p in pack_files
    }

    if raw_at_arg is not None:
        approved_at = _validate_at_scalar(raw_at_arg)
        target_meta = (approved_by, approved_at, approval_evidence)
        for spec_path in pack_files:
            rel_posix = spec_path.relative_to(root).as_posix()
            candidates: list[tuple[str, dict[str, str]]] = [
                (h_raw, h_fm) for _sha, h_raw, h_fm in hist_by_spec[spec_path]
            ]
            if amend:
                candidates.append((pack_texts[spec_path], pack_fms[spec_path]))
            for cand_raw, cand_fm in candidates:
                cand_meta = (
                    cand_fm.get("approved_by", "").strip(),
                    cand_fm.get("approved_at", "").strip(),
                    cand_fm.get("approval_evidence", "").strip(),
                )
                if cand_meta != target_meta:
                    continue
                if effective_mode == "self":
                    cand_csha = _hist_contract_sha_for_entry(
                        spec_path.name, rel_posix, cand_raw, cand_fm
                    )
                    if cand_csha != new_contract_shas[spec_path]:
                        raise ValueError(
                            f"{rel_posix}: approval metadata (approved_by, approved_at='{approved_at}', approval_evidence) "
                            "collides with a prior approved contract; omit --at or advance --at / --evidence on --amend"
                        )
                elif amend and cand_fm.get("source_revision", "").strip() != head_sha:
                    raise ValueError(
                        f"{rel_posix}: approval metadata (approved_by, approved_at='{approved_at}', approval_evidence) "
                        "collides with a prior approved revision; omit --at or advance --at / --evidence on --amend"
                    )
        return approved_at

    prior_raw_ats: list[str] = []
    for spec_path in pack_files:
        disk_at = pack_fms[spec_path].get("approved_at", "").strip()
        if disk_at:
            prior_raw_ats.append(disk_at)
        for _sha, _h_raw, h_fm in hist_by_spec[spec_path]:
            h_at = h_fm.get("approved_at", "").strip()
            if h_at:
                prior_raw_ats.append(h_at)

    parsed_priors = [
        parsed
        for raw_item in prior_raw_ats
        for parsed in (_parse_iso_to_utc_epoch(raw_item),)
        if parsed is not None
    ]
    now_utc = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    now_epoch = int(now_utc.timestamp())
    today_local = dt.date.today().isoformat()
    today_utc = now_utc.date().isoformat()

    has_same_or_future_day = any(
        d_prefix >= today_local or d_prefix >= today_utc or p_ep >= now_epoch
        for d_prefix, p_ep in parsed_priors
    )
    if not amend and not has_same_or_future_day:
        return today_local

    max_prior_epoch = max((p_ep for _d, p_ep in parsed_priors), default=None)
    target_epoch = max(
        now_epoch,
        (max_prior_epoch + 1) if max_prior_epoch is not None else now_epoch,
    )
    return dt.datetime.fromtimestamp(target_epoch, tz=dt.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


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
        default=None,
        help="ISO-8601 approval date (YYYY-MM-DD) or timestamp (defaults to today, or monotonic UTC timestamp on same-day --amend).",
    )
    parser.add_argument(
        "--mode",
        choices=("self", "head-sha"),
        default=None,
        help="Provenance mode: 'self' writes source_revision: self + contract_sha256 (default on initial approval); 'head-sha' writes 40-hex Git HEAD SHA (preserved by default on legacy --amend).",
    )
    parser.add_argument(
        "--amend",
        action="store_true",
        help="Refresh approval metadata and source_revision/contract_sha256 on an already-approved pack (Spec Amendment).",
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
    stamp_target_label: str,
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
    print(f"DRY-RUN: would {action} {rel_feature} at {stamp_target_label} (files: {len(planned_writes)})")
    for orig_path, _new_text, _orig_b, _mode in planned_writes:
        print(f"  {orig_path.relative_to(root).as_posix()}")
    if superseded_rel and not has_sup_writes:
        print(f"  (preserved already-superseded {superseded_rel})")
    return 0


def _apply_and_validate_writes(
    root: Path,
    rel_feature: str,
    stamp_target_label: str,
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
    print(f"PASS: {action} {rel_feature} at {stamp_target_label} (files updated: {len(planned_writes)})")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require(not args.root.is_symlink(), f"project root cannot be a symlink: {args.root}")
    probe_git_top = resolve_git_toplevel(args.root)
    if probe_git_top is not None:
        if args.root.resolve().is_relative_to(probe_git_top):
            _verify_git_root_no_symlink(args.root, probe_git_top, err_prefix="stamp-spec")
    root = args.root.resolve()

    if not args.dry_run and is_source_template_repository(root):
        raise ValueError(
            "refusing to stamp feature specs inside the source ai-project-template repository "
            "(install into a target project first, or pass --dry-run to preview)"
        )

    approved_by = _validate_free_scalar(args.by, "--by")
    approval_evidence = _validate_free_scalar(args.evidence, "--evidence")
    if args.at is not None:
        _validate_at_scalar(args.at)

    _scan_docs_current_no_symlinks(root)

    feature_dir = resolve_active_feature_dir(
        root,
        args.feature,
        require_approved=False,
        exclude_all_done=False,
    )
    rel_feature = feature_dir.relative_to(root).as_posix()
    pack_files, is_mini = _collect_pack_layout(feature_dir, root)
    pack_raw_bytes, pack_texts, pack_fms = _read_pack_specs(root, pack_files)

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

    if not args.amend:
        effective_mode = args.mode or "self"
    elif args.mode is not None:
        effective_mode = args.mode
    else:
        existing_revs = [pack_fms[p].get("source_revision", "").strip().lower() for p in pack_files]
        if existing_revs and all(
            HEX40_RE.fullmatch(r) and not re.fullmatch(r"0+", r) for r in existing_revs
        ):
            effective_mode = "head-sha"
        else:
            effective_mode = "self"

    head_sha = ""
    new_contract_shas: dict[Path, str] = {}
    if effective_mode == "head-sha":
        head_sha = _resolve_head_sha(root)
        stamp_target_label = head_sha
    else:
        if not args.dry_run:
            require(
                resolve_git_toplevel(root) is not None,
                "stamp-spec.py --mode self requires a Git repository",
            )
        for spec_path in pack_files:
            new_contract_shas[spec_path] = compute_contract_sha256(
                spec_path.name,
                spec_path.relative_to(root),
                pack_texts[spec_path],
            )
        stamp_target_label = "self"

    approved_at = _resolve_pack_approved_at(
        root,
        pack_files,
        pack_texts,
        pack_fms,
        raw_at_arg=args.at,
        amend=args.amend,
        effective_mode=effective_mode,
        approved_by=approved_by,
        approval_evidence=approval_evidence,
        head_sha=head_sha,
        new_contract_shas=new_contract_shas,
    )

    base_approval_updates: list[tuple[str, str | None]] = [
        ("status", "approved"),
        ("approved_by", json.dumps(approved_by, ensure_ascii=False)),
        ("approved_at", json.dumps(approved_at, ensure_ascii=False)),
        ("approval_evidence", json.dumps(approval_evidence, ensure_ascii=False)),
    ]
    planned_writes: list[tuple[Path, str, bytes, int]] = []
    for spec_path in pack_files:
        rev_updates: list[tuple[str, str | None]] = (
            [("source_revision", "self"), ("contract_sha256", new_contract_shas[spec_path])]
            if effective_mode == "self"
            else [("source_revision", head_sha), ("contract_sha256", None)]
        )
        planned_writes.append(
            _build_planned_write(root, spec_path, pack_raw_bytes, [*base_approval_updates, *rev_updates])
        )

    sup_writes, superseded_rel = _plan_supersession_writes(root, feature_dir, is_mini, pack_fms)
    planned_writes.extend(sup_writes)

    if args.dry_run:
        return _run_dry_run(
            root,
            rel_feature,
            stamp_target_label,
            args.amend,
            planned_writes,
            superseded_rel,
            bool(sup_writes),
        )
    return _apply_and_validate_writes(
        root,
        rel_feature,
        stamp_target_label,
        args.amend,
        planned_writes,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
