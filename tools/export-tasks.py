#!/usr/bin/env python3
"""Export tasks from a feature's 4. Tasks.md or 1. Mini Spec.md to JSON, Markdown, gh commands, or GitHub Issues."""

import sys

sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import NoReturn

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from docs_validation import (  # noqa: E402
        MINI_SPEC_FILE,
        SPEC_PACK_FILES,
        parse_execution_tasks as dv_parse_execution_tasks,
        parse_frontmatter as dv_parse_frontmatter,
        read_markdown,
        validate_clarify_gate,
        validate_feature_folder,
    )
except ImportError as exc:
    print(
        f"FAIL: export-tasks.py requires docs_validation.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update' to restore the validator bundle): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

ROOT = SCRIPT_DIR.parent

REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.:/-]{0,49}$")
GH_TIMEOUT_SECONDS = 30
GH_SEARCH_LIMIT = 500


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def walk_safe_inside_root(start_dir: Path, parts: tuple[str, ...], raw_label: str) -> Path:
    if ROOT.is_symlink():
        fail(f"repository root cannot be a symlink: {ROOT}")
    cur = start_dir
    for part in parts:
        if part in ("", "."):
            continue
        if cur.is_symlink():
            fail(f"symlink path component refused in '{raw_label}': {cur}")
        if part == "..":
            if cur == ROOT:
                fail(f"path escapes repository root: {raw_label}")
            cur = cur.parent
            continue
        cur = cur / part
        if cur.is_symlink():
            rel = cur.relative_to(ROOT).as_posix() if cur.is_relative_to(ROOT) else str(cur)
            fail(f"symlink path component refused in '{raw_label}': {rel}")
    return cur


def match_root_prefix(abs_path: Path) -> tuple[str, ...] | None:
    chain = list(reversed(abs_path.parents)) + [abs_path]
    for candidate in chain:
        try:
            if candidate.is_symlink():
                continue
            if candidate.exists() and candidate.resolve() == ROOT:
                return abs_path.parts[len(candidate.parts) :]
        except OSError:
            continue
    return None


def resolve_safe_repo_path(raw_arg: str, must_exist: bool) -> Path:
    if not raw_arg or not raw_arg.strip():
        fail("empty path argument is not allowed")
    raw_path = Path(raw_arg)

    if raw_path.is_absolute():
        tail_parts = match_root_prefix(raw_path)
        if tail_parts is None:
            fail(f"path escapes repository root: {raw_arg}")
        resolved_lexical = walk_safe_inside_root(ROOT, tail_parts, raw_arg)
    else:
        cwd = Path.cwd()
        try:
            cwd_resolved = cwd.resolve()
        except OSError as exc:
            fail(f"unable to resolve working directory: {exc}")

        if cwd_resolved.is_relative_to(ROOT):
            start_rel = cwd_resolved.relative_to(ROOT).parts
            start_dir = walk_safe_inside_root(ROOT, start_rel, str(cwd))
            resolved_lexical = walk_safe_inside_root(start_dir, raw_path.parts, raw_arg)
        else:
            cwd_joined = cwd / raw_path
            tail_parts = match_root_prefix(cwd_joined)
            if tail_parts is not None:
                resolved_lexical = walk_safe_inside_root(ROOT, tail_parts, raw_arg)
            else:
                resolved_lexical = walk_safe_inside_root(ROOT, raw_path.parts, raw_arg)

    if must_exist:
        if not resolved_lexical.exists():
            fail(f"path does not exist: {raw_arg}")
        if not resolved_lexical.resolve().is_relative_to(ROOT):
            fail(f"path escapes repository root: {raw_arg}")
    else:
        parent_probe = resolved_lexical.parent
        while not parent_probe.exists() and parent_probe != ROOT:
            parent_probe = parent_probe.parent
        if not parent_probe.resolve().is_relative_to(ROOT):
            fail(f"output path escapes repository root: {raw_arg}")

    return resolved_lexical


def build_export_rows(
    raw_text: str,
    rel_label: str,
    feature_slug: str,
    include_done: bool,
) -> list[dict[str, object]]:
    try:
        validated = dv_parse_execution_tasks(rel_label, raw_text, require_table=True) or []
    except ValueError as exc:
        fail(str(exc))

    exported: list[dict[str, object]] = []
    for row in validated:
        task_id = str(row["task_id"])
        row_status = str(row["status"])
        parallel = bool(row["parallel"])
        depends_on = list(row["depends_on"])  # type: ignore[arg-type]
        related_ac = list(row["related_ac"])  # type: ignore[arg-type]
        owned_paths = list(row["owned_paths"])  # type: ignore[arg-type]
        summary = str(row["summary"])
        verification = str(row["verification"])

        ac_rendered = ", ".join(related_ac) if related_ac else "-"
        title = f"[{feature_slug}][{task_id}] {summary}"
        body = "\n".join(
            [
                "## Summary",
                "",
                summary,
                "",
                "## Metadata",
                "",
                f"- Feature: `{feature_slug}`",
                f"- Source: `{rel_label}`",
                f"- Task ID: `{task_id}`",
                f"- Status: `{row_status}`",
                f"- Parallel: `{'yes' if parallel else 'no'}`",
                f"- Depends on: `{', '.join(depends_on) if depends_on else '-'}`",
                f"- Related AC: `{ac_rendered}`",
                f"- Owned paths: `{', '.join(owned_paths)}`",
                f"- Verification: `{verification}`",
            ]
        )

        exported.append(
            {
                "task_id": task_id,
                "title": title,
                "feature": feature_slug,
                "status": row_status,
                "parallel": parallel,
                "depends_on": depends_on,
                "related_ac": related_ac,
                "owned_paths": owned_paths,
                "summary": summary,
                "verification": verification,
                "body": body,
            }
        )

    if include_done:
        return exported
    return [item for item in exported if item["status"] != "done"]


def format_markdown(
    feature_slug: str,
    fm_status: str,
    source_rel: str,
    tasks: list[dict[str, object]],
) -> str:
    lines = [
        f"# Exported Tasks — {feature_slug}",
        "",
        f"- Source: `{source_rel}`",
        f"- Spec status: `{fm_status}`",
        f"- Exported tasks: {len(tasks)}",
    ]
    for task in tasks:
        depends = ", ".join(task["depends_on"]) if task["depends_on"] else "-"  # type: ignore[arg-type]
        acs = ", ".join(task["related_ac"]) if task["related_ac"] else "-"  # type: ignore[arg-type]
        paths = ", ".join(task["owned_paths"])  # type: ignore[arg-type]
        lines.extend(
            [
                "",
                f"### {task['title']}",
                f"- Task ID: `{task['task_id']}`",
                f"- Status: `{task['status']}`",
                f"- Parallel: `{'yes' if task['parallel'] else 'no'}`",
                f"- Depends on: `{depends}`",
                f"- Related AC: `{acs}`",
                f"- Owned paths: `{paths}`",
                f"- Verification: `{task['verification']}`",
            ]
        )
    return "\n".join(lines) + "\n"


def format_gh_commands(repo: str, tasks: list[dict[str, object]], labels: list[str]) -> str:
    if not tasks:
        return ""
    commands: list[str] = []
    for task in tasks:
        parts = [
            "gh",
            "issue",
            "create",
            "--repo",
            shlex.quote(repo),
            "--title",
            shlex.quote(str(task["title"])),
            "--body",
            shlex.quote(str(task["body"])),
        ]
        for lbl in labels:
            parts.append(shlex.quote(f"--label={lbl}"))
        commands.append(" ".join(parts))
    return "\n".join(commands) + "\n"


def validate_repo_slug(repo: str) -> str:
    if not REPO_RE.fullmatch(repo):
        fail(f"invalid --repo '{repo}' (expected OWNER/REPO matching ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$)")
    owner, name = repo.split("/", 1)
    if owner in (".", "..") or name in (".", ".."):
        fail(f"invalid --repo '{repo}' (owner/repo segments cannot be '.' or '..')")
    return repo


def validate_labels(raw_labels: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in raw_labels:
        if any(ord(ch) < 32 for ch in raw) or "," in raw or not LABEL_RE.fullmatch(raw):
            fail(
                f"invalid --label '{raw}' "
                "(expected 1-50 chars matching ^[A-Za-z0-9][A-Za-z0-9 _.:/-]{0,49}$, no leading '-' or commas)"
            )
        if raw not in cleaned:
            cleaned.append(raw)
    return cleaned


def write_output_exclusive(out_path: Path, content: str) -> None:
    if out_path.exists() or out_path.is_symlink():
        rel = out_path.relative_to(ROOT).as_posix()
        fail(f"refusing to overwrite existing output path: {rel}")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(out_path, flags, 0o644)
    except FileExistsError:
        rel = out_path.relative_to(ROOT).as_posix()
        fail(f"refusing to overwrite existing output path: {rel}")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
    except Exception:
        try:
            out_path.unlink()
        except OSError:
            pass
        raise


def apply_github_issues(
    repo: str,
    feature_slug: str,
    tasks: list[dict[str, object]],
    labels: list[str],
) -> None:
    gh_bin = shutil.which("gh")
    if not gh_bin:
        fail("gh CLI binary not found in PATH; install GitHub CLI or omit --apply-gh for offline export")
    if not tasks:
        return

    def _run_gh(cmd: list[str], action: str, context_label: str) -> str:
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
                timeout=GH_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            fail(f"gh issue {action} timed out after {GH_TIMEOUT_SECONDS}s for {context_label}")
        except subprocess.CalledProcessError as exc:
            err_msg = (exc.stderr or exc.stdout or "").strip() or f"exit status {exc.returncode}"
            fail(f"gh issue {action} failed for {context_label}: {err_msg}")
        except OSError as exc:
            fail(f"unable to invoke gh CLI: {exc}")
        return proc.stdout.strip()

    list_cmd = [
        gh_bin,
        "issue",
        "list",
        "--repo",
        repo,
        "--search",
        f"[{feature_slug}][ in:title",
        "--state",
        "all",
        "--limit",
        str(GH_SEARCH_LIMIT),
        "--json",
        "number,title,state,url",
    ]
    raw_json = _run_gh(list_cmd, "list", feature_slug) or "[]"
    try:
        existing_items = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        fail(f"gh issue list returned invalid JSON for {feature_slug}: {exc}")

    if not isinstance(existing_items, list):
        fail(f"gh issue list returned non-list JSON for {feature_slug}")
    if len(existing_items) >= GH_SEARCH_LIMIT:
        fail(
            f"gh issue list returned {len(existing_items)} items (reached --limit {GH_SEARCH_LIMIT}) "
            f"for '{feature_slug}'; refusing potentially incomplete deduplication"
        )

    for task in tasks:
        task_id = str(task["task_id"])
        prefix = f"[{feature_slug}][{task_id}]"

        matched = None
        for item in existing_items:
            if isinstance(item, dict) and str(item.get("title", "")).startswith(prefix):
                matched = item
                break

        if matched is not None:
            ref = matched.get("url") or f"#{matched.get('number', '?')}"
            print(f"SKIP: {prefix} already exists ({ref})")
            continue

        create_cmd = [
            gh_bin,
            "issue",
            "create",
            "--repo",
            repo,
            "--title",
            str(task["title"]),
            "--body",
            str(task["body"]),
        ]
        for lbl in labels:
            create_cmd.append(f"--label={lbl}")

        created_ref = _run_gh(create_cmd, "create", prefix) or "created"
        print(f"CREATED: {prefix} {created_ref}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export tasks from 4. Tasks.md or 1. Mini Spec.md offline or idempotently to GitHub Issues."
    )
    parser.add_argument(
        "target",
        help="Path to a feature directory, 4. Tasks.md, or 1. Mini Spec.md (inside repository root).",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown", "gh-commands"),
        default="json",
        dest="output_format",
        help="Offline export format (default: json).",
    )
    parser.add_argument(
        "--output",
        help="Write rendered output to a new repo-relative path (refuses overwrite or symlinks).",
    )
    parser.add_argument(
        "--include-done",
        action="store_true",
        help="Include tasks whose Status is 'done' (omitted by default).",
    )
    parser.add_argument(
        "--allow-draft",
        action="store_true",
        help="Allow exporting draft/example tasks when frontmatter status is not 'approved' (never overrides superseded or archived).",
    )
    parser.add_argument(
        "--apply-gh",
        action="store_true",
        help="Execute idempotent GitHub issue creation via gh CLI (requires --repo OWNER/REPO).",
    )
    parser.add_argument(
        "--repo",
        help="Target GitHub repository OWNER/REPO (required with --apply-gh; optional for --format gh-commands).",
    )
    parser.add_argument(
        "--label",
        action="append",
        default=[],
        dest="labels",
        help="Repeatable GitHub issue label (validated and passed as --label=<name>).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.repo is not None:
        validate_repo_slug(args.repo)
    if args.apply_gh and not args.repo:
        fail("--apply-gh requires explicit --repo OWNER/REPO")
    labels = validate_labels(args.labels)

    target_path = resolve_safe_repo_path(args.target, must_exist=True)
    if target_path.is_dir():
        mini_candidate = target_path / MINI_SPEC_FILE
        tasks4_candidate = target_path / "4. Tasks.md"
        for cand in (mini_candidate, tasks4_candidate):
            if cand.is_symlink():
                fail(f"symlink refused: {cand.relative_to(ROOT).as_posix()}")
        if mini_candidate.is_file() and tasks4_candidate.is_file():
            fail(
                f"cannot mix '{MINI_SPEC_FILE}' and '4. Tasks.md' in directory: "
                f"{target_path.relative_to(ROOT).as_posix()}"
            )
        if mini_candidate.is_file():
            tasks_path = mini_candidate
        elif tasks4_candidate.is_file():
            tasks_path = tasks4_candidate
        else:
            fail(
                f"neither 4. Tasks.md nor {MINI_SPEC_FILE} found in directory: "
                f"{target_path.relative_to(ROOT).as_posix()}"
            )
    elif target_path.is_file():
        if target_path.name not in {"4. Tasks.md", MINI_SPEC_FILE}:
            fail(
                f"expected a feature directory, '4. Tasks.md', or '{MINI_SPEC_FILE}', "
                f"got '{target_path.name}'"
            )
        tasks_path = target_path
    else:
        fail(f"target is neither a regular file nor directory: {args.target}")

    feature_dir = tasks_path.parent
    if feature_dir == ROOT:
        fail(f"{tasks_path.name} must reside inside a feature directory")

    out_path: Path | None = None
    if args.output is not None:
        out_path = resolve_safe_repo_path(args.output, must_exist=False)
        if out_path.exists() or out_path.is_symlink():
            fail(f"refusing to overwrite existing output path: {out_path.relative_to(ROOT).as_posix()}")

    source_rel = tasks_path.relative_to(ROOT).as_posix()
    feature_slug = feature_dir.name
    text = read_markdown(tasks_path)
    if not text.startswith("---"):
        fail(f"{source_rel}: missing YAML frontmatter")

    fm = dv_parse_frontmatter(text)
    fm_status = fm.get("status", "").strip().lower()
    if not fm_status:
        fail(f"{source_rel}: missing frontmatter 'status'")
    if fm_status in {"superseded", "archived"}:
        sup_by = fm.get("superseded_by", "").strip()
        sup_hint = f" (superseded_by: {sup_by})" if sup_by else ""
        fail(f"{source_rel}: refusing to export {fm_status} tasks{sup_hint}")
    if fm_status != "approved" and not args.allow_draft:
        fail(
            f"{source_rel}: refusing to export unapproved tasks (status: {fm_status}); "
            "pass --allow-draft to override"
        )

    pack_files = [
        feature_dir / name
        for name in sorted(SPEC_PACK_FILES)
        if (feature_dir / name).exists() or (feature_dir / name).is_symlink()
    ]
    for pf in pack_files:
        if pf.is_symlink():
            fail(f"symlink refused: {pf.relative_to(ROOT).as_posix()}")
        pf_fm = dv_parse_frontmatter(read_markdown(pf))
        pf_status = pf_fm.get("status", "").strip().lower()
        if pf_status in {"superseded", "archived"}:
            pf_sup = pf_fm.get("superseded_by", "").strip()
            pf_hint = f" (superseded_by: {pf_sup})" if pf_sup else ""
            fail(f"{pf.relative_to(ROOT).as_posix()}: refusing to export {pf_status} feature pack{pf_hint}")

    try:
        if not args.allow_draft:
            validate_clarify_gate(ROOT, pack_files, strict=False)
            validate_feature_folder(ROOT, feature_dir, require_tasks=True, strict=False)
        else:
            validate_feature_folder(ROOT, feature_dir, require_tasks=False, strict=False)
    except ValueError as exc:
        fail(str(exc))

    tasks = build_export_rows(
        raw_text=text,
        rel_label=source_rel,
        feature_slug=feature_slug,
        include_done=args.include_done,
    )

    repo_for_render = args.repo if args.repo else "OWNER/REPO"
    if args.output_format == "json":
        rendered = (
            json.dumps(
                {
                    "feature": feature_slug,
                    "status": fm_status,
                    "source": source_rel,
                    "tasks": tasks,
                },
                indent=2,
            )
            + "\n"
        )
    elif args.output_format == "markdown":
        rendered = format_markdown(feature_slug, fm_status, source_rel, tasks)
    else:
        rendered = format_gh_commands(repo_for_render, tasks, labels)

    if out_path is not None:
        write_output_exclusive(out_path, rendered)
    elif not args.apply_gh:
        sys.stdout.write(rendered)

    if args.apply_gh:
        apply_github_issues(args.repo, feature_slug, tasks, labels)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
