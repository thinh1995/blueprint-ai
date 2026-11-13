#!/usr/bin/env python3
"""Validate per-task evidence provenance and verified reference inventories."""

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from docs_validation import parse_frontmatter as _dv_parse_frontmatter  # noqa: E402
except ImportError:
    _dv_parse_frontmatter = None  # type: ignore[assignment]

DEFAULT_ROOT = SCRIPT_DIR.parent
VALID_EVIDENCE_STATUSES = {"draft", "completed", "template"}
PLACEHOLDER_VALUES = {"", "todo", "tbd", "pending", "n/a", "none", "-", "draft"}


def _fallback_parse_frontmatter(markdown_text: str) -> dict[str, str]:
    text = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", text, flags=re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in (match.group(1) or "").split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, raw_val = line.split(":", 1)
        val = raw_val.strip()
        if val and val[0] in {'"', "'"} and len(val) >= 2:
            q = val[0]
            end = val.rfind(q)
            if end > 0 and (not val[end + 1 :].strip() or val[end + 1 :].strip().startswith("#")):
                val = val[1:end].strip()
        else:
            val = re.split(r"[ \t]+#", val, maxsplit=1)[0].strip()
        if key.strip():
            data[key.strip()] = val
    return data


def read_bytes_nofollow(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"{path}: symlink refused")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{path}: unable to open regular file safely ({exc})") from exc
    try:
        st = os.fstat(fd)
        if not os.path.stat.S_ISREG(st.st_mode):
            raise ValueError(f"{path}: expected regular file")
        chunks: list[bytes] = []
        while True:
            buf = os.read(fd, 65536)
            if not buf:
                break
            chunks.append(buf)
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_text_nofollow(path: Path) -> str:
    raw = read_bytes_nofollow(path)
    try:
        return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: invalid UTF-8 encoding ({exc})") from exc


def parse_evidence_frontmatter(text: str, path: Path) -> dict[str, str]:
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    if not re.match(r"^---[ \t]*\n.*?\n---[ \t]*(?:\n|$)", normalized, flags=re.S):
        raise ValueError(f"{path}: missing frontmatter")
    if _dv_parse_frontmatter is not None:
        return _dv_parse_frontmatter(normalized)
    return _fallback_parse_frontmatter(normalized)


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
        # Also verify raw tail components inside root have no symlinks.
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
        help="Validate draft evidence artifact paths against the working tree before commit (forbidden for completed records).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    if args.allow_working_tree and args.require_completed:
        raise ValueError("--allow-working-tree cannot be combined with --require-completed")

    if args.root.is_symlink():
        raise ValueError(f"repository root cannot be a symlink: {args.root}")
    root = args.root.resolve()

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

    internal_evidence_dir = root / "docs/internal/task-evidence"
    corrections: dict[str, object] = {"schema_version": 1, "corrections": {}}
    if (
        args.evidence_dir
        and len(evidence_dirs) == 1
        and evidence_dirs[0].exists()
        and internal_evidence_dir.exists()
        and evidence_dirs[0].resolve() == internal_evidence_dir.resolve()
    ):
        corrections_path = walk_inside_root_no_symlinks(
            root,
            Path("docs/internal/task-evidence/evidence-corrections.json"),
            "evidence-corrections.json",
        )
        if corrections_path.exists():
            corrections = json.loads(read_text_nofollow(corrections_path))
            if corrections.get("schema_version") != 1 or not isinstance(corrections.get("corrections"), dict):
                raise ValueError("evidence corrections file is invalid")

    completed_records = 0
    corrections_map: dict[str, dict[str, str]] = corrections["corrections"]  # type: ignore[assignment]

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
                if args.allow_working_tree and data.get("output_artifact_path"):
                    raw_art = data["output_artifact_path"].replace("\\", "/").strip()
                    if raw_art.lower() not in PLACEHOLDER_VALUES:
                        art_rel = Path(raw_art)
                        art_full = walk_inside_root_no_symlinks(root, art_rel, str(entry))
                        art_bytes = read_bytes_nofollow(art_full)
                        raw_sha = data.get("output_artifact_sha256", "").strip().lower()
                        if raw_sha and raw_sha not in PLACEHOLDER_VALUES:
                            if hashlib.sha256(art_bytes).hexdigest() != raw_sha:
                                raise ValueError(f"{entry}: working-tree output artifact checksum does not match")
                continue

            # status == "completed"
            if args.allow_working_tree:
                raise ValueError(
                    f"{entry}: --allow-working-tree is forbidden when evidence record has status: completed"
                )

            completed_records += 1
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
            artifact_rel = Path(raw_artifact_str)
            if artifact_rel.is_absolute():
                raise ValueError(f"{entry}: output artifact path escapes repository root")
            walk_inside_root_no_symlinks(root, artifact_rel, f"{entry} output_artifact_path")

            if not re.fullmatch(r"[0-9a-f]{40}", data["source_revision"]) or re.fullmatch(
                r"0+", data["source_revision"]
            ):
                raise ValueError(f"{entry}: source revision must be a full lowercase Git SHA")

            entry_resolved = entry.resolve()
            correction_key = (
                entry_resolved.relative_to(root).as_posix()
                if entry_resolved.is_relative_to(root)
                else None
            )
            correction = corrections_map.get(correction_key, {}) if correction_key else {}
            revision = correction.get("source_revision", data["source_revision"])
            if not re.fullmatch(r"[0-9a-f]{40}", revision) or re.fullmatch(r"0+", revision):
                raise ValueError(f"{entry}: correction source revision must be a full lowercase Git SHA")

            try:
                subprocess.check_call(
                    ["git", "rev-parse", "--verify", f"{revision}^{{commit}}"],
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                raise ValueError(f"{entry}: source revision is unavailable: {data['source_revision']}") from exc

            source_spec = f"{revision}:{artifact_rel.as_posix()}"
            try:
                artifact_bytes = subprocess.check_output(
                    ["git", "show", source_spec],
                    cwd=root,
                    stderr=subprocess.DEVNULL,
                )
            except (OSError, subprocess.CalledProcessError) as exc:
                raise ValueError(
                    f"{entry}: output artifact is unavailable at source revision: {source_spec}"
                ) from exc

            digest = hashlib.sha256(artifact_bytes).hexdigest()
            if digest != data["output_artifact_sha256"].lower():
                raise ValueError(f"{entry}: output artifact checksum does not match")

    if args.require_completed and completed_records == 0:
        raise ValueError("no completed task evidence record found")

    inventory_rel = Path("docs/current/02 - Architecture/Generated Reference Inventory.md")
    if (root / "docs").exists() or (root / "docs").is_symlink():
        inventory = walk_inside_root_no_symlinks(root, inventory_rel, "Generated Reference Inventory.md")
        if inventory.is_symlink():
            raise ValueError(f"{inventory}: symlink refused")
        if inventory.is_file():
            inv_data = parse_evidence_frontmatter(read_text_nofollow(inventory), inventory)
            if inv_data.get("verified", "").strip().lower() == "true":
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

    if not args.evidence_dir and legacy_evidence_dir.is_dir():
        print(f"WARN: validating legacy evidence directory during migration: {legacy_evidence_dir.relative_to(root)}")
    print("PASS: task evidence and inventory validation")


if __name__ == "__main__":
    try:
        main()
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
