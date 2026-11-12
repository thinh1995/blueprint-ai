#!/usr/bin/env python3
"""Export tasks from a feature's 4. Tasks.md to JSON, Markdown, gh commands, or GitHub Issues."""

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

ROOT = Path(__file__).resolve().parent.parent

FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|\Z)", re.S)
TASK_ID_RE = re.compile(r"^T-\d+$")
AC_ID_RE = re.compile(r"\bAC-\d+\b")
UNESCAPED_PIPE_RE = re.compile(r"(?<!\\)\|")
SEPARATOR_CELL_RE = re.compile(r"^:?-{3,}:?$")
REPO_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
GLOB_CHARS = frozenset("*?[")

VALID_STATUSES = frozenset({"todo", "in-progress", "done", "blocked"})
REQUIRED_COLUMNS = (
    "task id",
    "status",
    "[p]",
    "depends on",
    "related ac",
    "owned paths",
    "summary",
    "verification",
)


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


def parse_frontmatter(text: str, rel_label: str) -> dict[str, str]:
    match = FRONTMATTER_RE.match(text)
    if not match:
        fail(f"{rel_label}: missing YAML frontmatter")
    data: dict[str, str] = {}
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            val = value.strip()
            if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
                val = val[1:-1].strip()
            data[key.strip()] = val
    return data


def strip_fenced_code(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    out_lines: list[str] = []
    fence_char = ""
    fence_len = 0
    for line in normalized.split("\n"):
        if not fence_char:
            m_bt = re.match(r"^[ \t]*(`{3,})([^`]*)$", line)
            m_td = None if m_bt else re.match(r"^[ \t]*(~{3,})(.*)$", line)
            m = m_bt or m_td
            if m:
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
                out_lines.append("")
                continue
            out_lines.append(line)
        else:
            if re.match(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$", line):
                fence_char = ""
                fence_len = 0
            out_lines.append("")
    return "\n".join(out_lines)


def split_md_row(line: str) -> list[str]:
    stripped = line.strip()
    parts = UNESCAPED_PIPE_RE.split(stripped)
    cells = parts[1:-1]
    return [cell.replace(r"\|", "|").strip() for cell in cells]


def strip_outer_backticks(value: str) -> str:
    stripped = value.strip()
    if len(stripped) >= 2 and stripped.startswith("`") and stripped.endswith("`"):
        inner = stripped[1:-1]
        if "`" not in inner:
            return inner.strip()
    return stripped


def validate_owned_paths(raw_cell: str, task_id: str, rel_label: str) -> list[str]:
    cleaned_paths: list[str] = []
    unwrapped = strip_outer_backticks(raw_cell)
    for item in unwrapped.split(","):
        token = strip_outer_backticks(item).strip()
        if not token:
            continue
        if token.startswith("/") or token.startswith("~"):
            fail(f"{rel_label} ({task_id}): owned path must be repo-relative, got '{token}'")
        if any(ch in token for ch in GLOB_CHARS):
            fail(f"{rel_label} ({task_id}): owned path must not use globs (*, ?, [): '{token}'")
        if "\\" in token:
            fail(f"{rel_label} ({task_id}): owned path must use POSIX '/' separators: '{token}'")
        trimmed = token.rstrip("/")
        raw_segments = trimmed.split("/") if trimmed else [""]
        if any(seg in ("", ".", "..") for seg in raw_segments):
            fail(f"{rel_label} ({task_id}): invalid traversal segment in owned path '{token}'")
        cleaned_paths.append(token)

    if not cleaned_paths:
        fail(f"{rel_label} ({task_id}): Owned paths must list at least one repo-relative path")
    return cleaned_paths


def detect_dependency_cycles(dep_graph: dict[str, list[str]], rel_label: str) -> None:
    state: dict[str, int] = {}

    def dfs(node: str, trail: list[str]) -> None:
        state[node] = 1
        for dep in dep_graph.get(node, []):
            dep_state = state.get(dep, 0)
            if dep_state == 1:
                cycle = " -> ".join(trail + [dep])
                fail(f"{rel_label}: dependency cycle detected in Execution tasks: {cycle}")
            if dep_state == 0:
                dfs(dep, trail + [dep])
        state[node] = 2

    for task_id in dep_graph:
        if state.get(task_id, 0) == 0:
            dfs(task_id, [task_id])


def parse_execution_tasks(
    text: str,
    rel_label: str,
    feature_slug: str,
    include_done: bool,
) -> list[dict[str, object]]:
    clean_text = strip_fenced_code(text)
    sec_match = re.search(r"^##[ \t]+Execution tasks[ \t]*$", clean_text, re.M)
    if not sec_match:
        fail(f"{rel_label}: missing '## Execution tasks' section")

    tail = clean_text[sec_match.end() :]
    next_heading = re.search(r"^#{1,2}[ \t]+\S", tail, re.M)
    section_body = tail[: next_heading.start()] if next_heading else tail

    table_lines: list[str] = []
    in_table = False
    for line in section_body.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            table_lines.append(stripped)
            in_table = True
        elif in_table:
            break

    if len(table_lines) < 2:
        fail(f"{rel_label}: missing Markdown table under '## Execution tasks'")

    headers = [h.lower() for h in split_md_row(table_lines[0])]
    sep_cells = [c.replace(" ", "") for c in split_md_row(table_lines[1])]
    if len(sep_cells) != len(headers) or not all(SEPARATOR_CELL_RE.fullmatch(c) for c in sep_cells):
        fail(f"{rel_label}: malformed separator row in '## Execution tasks' table")

    col_idx = {name: idx for idx, name in enumerate(headers)}
    missing_cols = [col for col in REQUIRED_COLUMNS if col not in col_idx]
    if missing_cols:
        fail(
            f"{rel_label}: Execution tasks table missing required column(s): "
            f"{', '.join(missing_cols)}"
        )

    parsed_rows: list[dict[str, object]] = []
    seen_ids: set[str] = set()

    for raw_line in table_lines[2:]:
        cells = split_md_row(raw_line)
        if len(cells) != len(headers):
            fail(
                f"{rel_label}: malformed task row (expected {len(headers)} columns, got {len(cells)}): "
                f"{raw_line}"
            )

        task_id = strip_outer_backticks(cells[col_idx["task id"]])
        if not TASK_ID_RE.fullmatch(task_id):
            fail(f"{rel_label}: invalid Task ID '{task_id}' (expected T-xx)")
        if task_id in seen_ids:
            fail(f"{rel_label}: duplicate Task ID '{task_id}'")
        seen_ids.add(task_id)

        row_status = strip_outer_backticks(cells[col_idx["status"]]).lower()
        if row_status not in VALID_STATUSES:
            fail(
                f"{rel_label} ({task_id}): invalid Status '{row_status}' "
                f"(expected one of: {', '.join(sorted(VALID_STATUSES))})"
            )

        p_val = strip_outer_backticks(cells[col_idx["[p]"]]).lower()
        if p_val not in ("yes", "no"):
            fail(f"{rel_label} ({task_id}): invalid [P] value '{p_val}' (expected yes or no)")
        parallel = p_val == "yes"

        dep_clean = cells[col_idx["depends on"]].replace("`", "").strip()
        if dep_clean in ("", "-"):
            depends_on: list[str] = []
        else:
            depends_on = [tok for tok in re.split(r"[,\s]+", dep_clean) if tok]
            for dep_id in depends_on:
                if not TASK_ID_RE.fullmatch(dep_id):
                    fail(f"{rel_label} ({task_id}): invalid Depends on reference '{dep_id}'")
                if dep_id == task_id:
                    fail(f"{rel_label} ({task_id}): task cannot depend on itself")

        related_ac = list(dict.fromkeys(AC_ID_RE.findall(cells[col_idx["related ac"]])))
        if not related_ac:
            fail(f"{rel_label} ({task_id}): Related AC must reference at least one AC-xx")

        owned_paths = validate_owned_paths(cells[col_idx["owned paths"]], task_id, rel_label)

        summary = cells[col_idx["summary"]].strip()
        if not summary:
            fail(f"{rel_label} ({task_id}): Summary must not be empty")

        verification = strip_outer_backticks(cells[col_idx["verification"]])
        if not verification:
            fail(f"{rel_label} ({task_id}): Verification must not be empty")

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
                f"- Related AC: `{', '.join(related_ac)}`",
                f"- Owned paths: `{', '.join(owned_paths)}`",
                f"- Verification: `{verification}`",
            ]
        )

        parsed_rows.append(
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

    for row in parsed_rows:
        t_id = str(row["task_id"])
        for dep_id in row["depends_on"]:  # type: ignore[attr-defined]
            if dep_id not in seen_ids:
                fail(f"{rel_label} ({t_id}): Depends on unknown Task ID '{dep_id}'")

    dep_graph = {
        str(row["task_id"]): list(row["depends_on"])  # type: ignore[arg-type]
        for row in parsed_rows
    }
    detect_dependency_cycles(dep_graph, rel_label)

    if include_done:
        return parsed_rows
    return [row for row in parsed_rows if row["status"] != "done"]


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
        acs = ", ".join(task["related_ac"])  # type: ignore[arg-type]
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


def format_gh_commands(repo: str, tasks: list[dict[str, object]]) -> str:
    if not tasks:
        return ""
    commands: list[str] = []
    for task in tasks:
        cmd = " ".join(
            [
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
        )
        commands.append(cmd)
    return "\n".join(commands) + "\n"


def validate_repo_slug(repo: str) -> str:
    if not REPO_RE.fullmatch(repo):
        fail(f"invalid --repo '{repo}' (expected OWNER/REPO matching ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$)")
    owner, name = repo.split("/", 1)
    if owner in (".", "..") or name in (".", ".."):
        fail(f"invalid --repo '{repo}' (owner/repo segments cannot be '.' or '..')")
    return repo


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
) -> None:
    gh_bin = shutil.which("gh")
    if not gh_bin:
        fail("gh CLI binary not found in PATH; install GitHub CLI or omit --apply-gh for offline export")

    def _run_gh(cmd: list[str], action: str, prefix: str) -> str:
        try:
            proc = subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as exc:
            err_msg = (exc.stderr or exc.stdout or "").strip() or f"exit status {exc.returncode}"
            fail(f"gh issue {action} failed for {prefix}: {err_msg}")
        except OSError as exc:
            fail(f"unable to invoke gh CLI: {exc}")
        return proc.stdout.strip()

    for task in tasks:
        task_id = str(task["task_id"])
        prefix = f"[{feature_slug}][{task_id}]"
        list_cmd = [
            gh_bin,
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            f"{prefix} in:title",
            "--json",
            "number,title,url",
        ]
        raw_json = _run_gh(list_cmd, "list", prefix) or "[]"
        try:
            existing_items = json.loads(raw_json)
        except json.JSONDecodeError as exc:
            fail(f"gh issue list returned invalid JSON for {prefix}: {exc}")

        if not isinstance(existing_items, list):
            fail(f"gh issue list returned non-list JSON for {prefix}")

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
        created_ref = _run_gh(create_cmd, "create", prefix) or "created"
        print(f"CREATED: {prefix} {created_ref}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export tasks from 4. Tasks.md offline or idempotently to GitHub Issues."
    )
    parser.add_argument(
        "target",
        help="Path to a feature directory or its 4. Tasks.md file (inside repository root).",
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
        help="Allow exporting tasks when frontmatter status is not 'approved'.",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.repo is not None:
        validate_repo_slug(args.repo)
    if args.apply_gh and not args.repo:
        fail("--apply-gh requires explicit --repo OWNER/REPO")

    target_path = resolve_safe_repo_path(args.target, must_exist=True)
    if target_path.is_dir():
        tasks_path = target_path / "4. Tasks.md"
        if tasks_path.is_symlink():
            fail(f"symlink refused: {tasks_path.relative_to(ROOT).as_posix()}")
        if not tasks_path.is_file():
            fail(f"4. Tasks.md not found in directory: {target_path.relative_to(ROOT).as_posix()}")
    elif target_path.is_file():
        if target_path.name != "4. Tasks.md":
            fail(f"expected a feature directory or '4. Tasks.md', got '{target_path.name}'")
        tasks_path = target_path
    else:
        fail(f"target is neither a regular file nor directory: {args.target}")

    if tasks_path.parent == ROOT:
        fail("4. Tasks.md must reside inside a feature directory")

    out_path: Path | None = None
    if args.output is not None:
        out_path = resolve_safe_repo_path(args.output, must_exist=False)
        if out_path.exists() or out_path.is_symlink():
            fail(f"refusing to overwrite existing output path: {out_path.relative_to(ROOT).as_posix()}")

    source_rel = tasks_path.relative_to(ROOT).as_posix()
    feature_slug = tasks_path.parent.name
    text = tasks_path.read_text(encoding="utf-8")

    fm = parse_frontmatter(text, source_rel)
    fm_status = fm.get("status", "").strip().lower()
    if not fm_status:
        fail(f"{source_rel}: missing frontmatter 'status'")
    if fm_status != "approved" and not args.allow_draft:
        fail(
            f"{source_rel}: refusing to export unapproved tasks (status: {fm_status}); "
            "pass --allow-draft to override"
        )

    tasks = parse_execution_tasks(
        text=text,
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
        rendered = format_gh_commands(repo_for_render, tasks)

    if out_path is not None:
        write_output_exclusive(out_path, rendered)
    elif not args.apply_gh:
        sys.stdout.write(rendered)

    if args.apply_gh:
        apply_github_issues(args.repo, feature_slug, tasks)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
