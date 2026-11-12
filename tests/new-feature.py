#!/usr/bin/env python3
"""Scaffold a numbered 4-file feature specification pack under docs/current/05 - Product Features/."""

import sys

sys.dont_write_bytecode = True

import argparse
import json
import os
import re
from pathlib import Path
from typing import NoReturn

ROOT = Path(__file__).resolve().parent.parent

SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEQ_PREFIX_RE = re.compile(r"^(\d{3})-")
FRONTMATTER_RE = re.compile(r"\A(---\r?\n)(.*?)(\r?\n---(?:\r?\n|\Z))", re.S)
APPROVAL_FIELD_RE = re.compile(
    r"^(approved_by|approved_at|approval_evidence|source_revision):[ \t]*.*$",
    re.M,
)

CANONICAL_SPECS = (
    "1. Product Spec.md",
    "2. Tech Spec.md",
    "3. QA Spec.md",
    "4. Tasks.md",
)

BUILTIN_PRESETS = (
    "general",
    "web-api",
    "cli-tool",
    "ai-agent",
)

AI_ADDENDUM_ROWS = (
    "AI addendum: model / policy / prompt version",
    "AI addendum: Tool permissions, timeout, retry, fallback",
    "AI addendum: knowledge provenance, citation, retention",
    "AI addendum: human escalation and evaluation threshold",
)


def fail(message: str) -> NoReturn:
    print(f"FAIL: {message}", file=sys.stderr)
    sys.exit(1)


def ensure_no_symlinks(root: Path, rel_parts: tuple[str, ...], must_exist: bool = True) -> Path:
    if root.is_symlink():
        fail(f"repository root cannot be a symlink: {root}")
    cur = root
    for part in rel_parts:
        cur = cur / part
        if cur.is_symlink():
            rel = "/".join(rel_parts)
            fail(f"symlink path component refused along '{rel}': {cur.relative_to(root)}")
    if must_exist:
        if not cur.exists():
            fail(f"required path does not exist: {'/'.join(rel_parts)}")
        if not cur.resolve().is_relative_to(root):
            fail(f"path escapes repository root: {'/'.join(rel_parts)}")
    return cur


def resolve_preset_name(cli_preset: str | None) -> str:
    if cli_preset is not None:
        if not SLUG_RE.fullmatch(cli_preset):
            fail(
                f"invalid preset name '{cli_preset}' "
                "(expected lowercase kebab-case matching ^[a-z0-9]+(?:-[a-z0-9]+)*$)"
            )
        return cli_preset

    manifest_path = ROOT / "template-manifest.json"
    if manifest_path.is_symlink():
        fail("template-manifest.json cannot be a symlink")
    if manifest_path.exists():
        if not manifest_path.is_file():
            fail("template-manifest.json is not a regular file")
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            fail(f"unable to parse template-manifest.json: {exc}")
        if not isinstance(manifest, dict):
            fail("template-manifest.json root must be a JSON object")
        if "default_preset" in manifest and manifest["default_preset"] is not None:
            default_preset = manifest["default_preset"]
            if not isinstance(default_preset, str) or not SLUG_RE.fullmatch(default_preset):
                fail(
                    f"invalid default_preset in template-manifest.json: {default_preset!r} "
                    "(expected lowercase kebab-case matching ^[a-z0-9]+(?:-[a-z0-9]+)*$)"
                )
            return default_preset

    return "general"


def validate_custom_preset_dir(custom_dir: Path, preset_name: str) -> list[Path]:
    if custom_dir.is_symlink():
        fail(f"custom preset directory cannot be a symlink: docs/templates/presets/{preset_name}")
    if not custom_dir.is_dir():
        fail(f"custom preset path is not a directory: docs/templates/presets/{preset_name}")
    if not custom_dir.resolve().is_relative_to(ROOT):
        fail(f"custom preset directory escapes repository root: docs/templates/presets/{preset_name}")

    md_files: list[Path] = []
    for entry in sorted(custom_dir.iterdir(), key=lambda p: p.name):
        if entry.is_symlink():
            fail(
                f"symlink refused inside custom preset '{preset_name}': "
                f"docs/templates/presets/{preset_name}/{entry.name}"
            )
        if entry.name == ".DS_Store":
            continue
        if not entry.is_file() or entry.suffix != ".md":
            fail(
                f"custom preset '{preset_name}' may only contain regular .md files "
                f"(found '{entry.name}')"
            )
        if not entry.resolve().is_relative_to(ROOT):
            fail(f"custom preset file escapes repository root: {entry.name}")
        md_files.append(entry)
    return md_files


def list_presets() -> int:
    ensure_no_symlinks(ROOT, ("docs", "templates"), must_exist=True)
    presets_root = ensure_no_symlinks(ROOT, ("docs", "templates", "presets"), must_exist=False)

    custom_names: list[str] = []
    if presets_root.exists():
        if not presets_root.is_dir():
            fail("docs/templates/presets exists and is not a directory")
        for entry in sorted(presets_root.iterdir(), key=lambda p: p.name):
            if entry.name == ".DS_Store":
                continue
            if entry.is_symlink():
                fail(f"symlink refused in docs/templates/presets: {entry.name}")
            if entry.is_dir() and SLUG_RE.fullmatch(entry.name):
                validate_custom_preset_dir(entry, entry.name)
                custom_names.append(entry.name)

    for name in BUILTIN_PRESETS:
        if name in custom_names:
            print(f"{name} (built-in, custom override in docs/templates/presets/{name})")
        else:
            print(f"{name} (built-in)")
    for name in custom_names:
        if name not in BUILTIN_PRESETS:
            print(f"{name} (custom: docs/templates/presets/{name})")
    return 0


def replace_table_row_by_first_cell(text: str, first_cell: str, col2: str, col3: str) -> str:
    pattern = re.compile(r"^\|\s*" + re.escape(first_cell) + r"\s*\|.*\|[ \t]*$", re.M)
    replacement = f"| {first_cell} | {col2} | {col3} |"
    updated, count = pattern.subn(lambda _m: replacement, text, count=1)
    if count == 0:
        fail(f"expected template table row '{first_cell}' not found in 2. Tech Spec.md")
    return updated


def replace_qa_rows(
    text: str,
    preconditions: str,
    steps: str,
    expected: str,
    automated: str,
    test_cmd: str,
    extra_edge_bullets: list[str],
) -> str:
    cov_pattern = re.compile(r"^\|\s*QA-01\s*\|\s*AC-01\s*\|.*\|[ \t]*$", re.M)
    cov_row = f"| QA-01 | AC-01 | {preconditions} | {steps} | {expected} | {automated} |"
    text, count = cov_pattern.subn(lambda _m: cov_row, text, count=1)
    if count == 0:
        fail("expected QA-01/AC-01 coverage row not found in 3. QA Spec.md")

    trace_pattern = re.compile(r"^\|\s*AC-01\s*\|\s*QA-01\s*\|.*\|[ \t]*$", re.M)
    trace_row = f"| AC-01 | QA-01 | {test_cmd} | qa |"
    text, count = trace_pattern.subn(lambda _m: trace_row, text, count=1)
    if count == 0:
        fail("expected AC-01/QA-01 traceability row not found in 3. QA Spec.md")

    if extra_edge_bullets:
        marker = "\n## Validation evidence"
        idx = text.find(marker)
        bullet_block = "\n".join(f"- {item}" for item in extra_edge_bullets)
        if idx != -1:
            prefix = text[:idx].rstrip("\n")
            text = f"{prefix}\n{bullet_block}\n{text[idx:]}"
        else:
            text = text.rstrip("\n") + "\n" + bullet_block + "\n"

    return text


def replace_execution_task_rows(text: str, rows: list[str]) -> str:
    section_match = re.search(r"^##[ \t]+Execution tasks[ \t]*$", text, re.M)
    if not section_match:
        fail("expected '## Execution tasks' section not found in 4. Tasks.md")

    head = text[: section_match.end()]
    tail = text[section_match.end() :]
    lines = tail.splitlines(keepends=True)

    header_idx = None
    sep_idx = None
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        if stripped.startswith("|") and stripped.endswith("|"):
            if header_idx is None:
                header_idx = idx
            elif sep_idx is None:
                sep_idx = idx
                break

    if header_idx is None or sep_idx is None:
        fail("expected Markdown table under '## Execution tasks' in 4. Tasks.md")

    end_idx = sep_idx + 1
    while end_idx < len(lines):
        stripped = lines[end_idx].strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            end_idx += 1
        else:
            break

    new_rows = [row + "\n" for row in rows]
    rebuilt_tail = "".join(lines[: sep_idx + 1] + new_rows + lines[end_idx:])
    return head + rebuilt_tail


def apply_builtin_overlay(preset_name: str, docs: dict[str, str]) -> dict[str, str]:
    if preset_name == "general":
        return docs

    tech = docs["2. Tech Spec.md"]
    qa = docs["3. QA Spec.md"]
    tasks = docs["4. Tasks.md"]

    if preset_name == "web-api":
        tech = re.sub(
            r"^(- Affected modules, routes, jobs, schemas, or integrations:)[ \t]*$",
            r"\1 HTTP routes, request/response contracts, auth/tenant middleware, and persistence migrations.",
            tech,
            count=1,
            flags=re.M,
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Specify HTTP method/route, request/response schema, status codes, idempotency key, and pagination.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Specify forward/backward-compatible migration steps, backfill safety, and rollback script.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Specify structured request logs, latency/5xx metrics, and alert threshold.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Specify zero-downtime rollout sequence, feature flag guard, and rollback trigger.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Specify upstream timeout, bounded retry budget, and degraded error response.",
            "engineering",
        )
        for ai_row in AI_ADDENDUM_ROWS:
            tech = replace_table_row_by_first_cell(
                tech, ai_row, "Not applicable (web-api preset).", "n/a"
            )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Implement versioned HTTP route contract, auth/tenant boundary check, and persistence handler.",
            "`pytest tests/api/`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Authenticated caller and isolated tenant fixture.",
            steps="Send valid request, malformed 4xx payload, cross-tenant/unauthorized call, burst rate-limit calls, and migration rollback check.",
            expected="2xx response on valid call; deterministic 400/401/403/429 errors; zero cross-tenant leakage; clean rollback.",
            automated="yes",
            test_cmd="`pytest tests/api/`",
            extra_edge_bullets=[
                "Web-API preset: verify 401/403 auth & cross-tenant boundary, 4xx schema validation, rate-limit (429) enforcement, and migration rollback.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/api/contracts/` | Define HTTP route contract, status codes, pagination, and schema migration plan. | `pytest tests/api/test_contracts.py` |",
                "| T-02 | todo | no | T-01 | AC-01 | `src/api/handlers/` | Implement endpoint handler with auth/tenant enforcement, 4xx validation, and rate-limit hooks. | `pytest tests/api/test_handlers.py` |",
            ],
        )

    elif preset_name == "cli-tool":
        tech = re.sub(
            r"^(- Affected modules, routes, jobs, schemas, or integrations:)[ \t]*$",
            r"\1 CLI entrypoint, argument parser, filesystem guards, and exit-code contract (web/tenancy not applicable).",
            tech,
            count=1,
            flags=re.M,
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Specify CLI flags/args, exit codes (0 success, 1 runtime failure, 2 usage error), and stdin/stdout/stderr contract.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Not applicable (cli-tool preset; document config/output format compatibility if persisted).",
            "n/a",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Specify deterministic stdout output and actionable stderr diagnostics (web telemetry not applicable).",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Specify --dry-run preview, atomic file writes (O_EXCL), symlink refusal, and safe cleanup on error.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Offline-first stdlib execution; fail fast with explicit message when optional external CLI is absent.",
            "engineering",
        )
        for ai_row in AI_ADDENDUM_ROWS:
            tech = replace_table_row_by_first_cell(
                tech, ai_row, "Not applicable (cli-tool preset).", "n/a"
            )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Implement CLI flag parser, stdin/stdout/stderr stream contract, atomic writes, and symlink/traversal guards.",
            "`pytest tests/test_cli.py`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Isolated temporary directory with fixture files.",
            steps="Run valid invocation, invalid flags, --dry-run mode, repeated idempotent run, and ../ or symlink traversal input.",
            expected="Exit 0 on valid/--dry-run (no writes on --dry-run); deterministic non-zero exit on invalid flags or unsafe paths.",
            automated="yes",
            test_cmd="`pytest tests/test_cli.py`",
            extra_edge_bullets=[
                "CLI-tool preset: verify invalid flags, non-zero exit codes (1/2), --dry-run zero-mutation guarantee, idempotency, and symlink/path-traversal refusal (web multi-tenancy not applicable).",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/cli/parser.py` | Implement CLI argument parser, exit codes, --dry-run handling, and atomic/symlink filesystem guards. | `pytest tests/test_cli.py -k parser` |",
                "| T-02 | todo | no | T-01 | AC-01 | `tests/test_cli.py` | Add CLI integration tests covering stdout/stderr contract, idempotency, and path-traversal refusal. | `pytest tests/test_cli.py` |",
            ],
        )

    elif preset_name == "ai-agent":
        tech = re.sub(
            r"^(- Affected modules, routes, jobs, schemas, or integrations:)[ \t]*$",
            r"\1 Agent orchestrator, prompt/policy config, retrieval grounding pipeline, tool allowlist, and evaluation harness.",
            tech,
            count=1,
            flags=re.M,
        )
        tech = tech.replace(
            "For every diagram, record:",
            "AI-agent preset reminder: include Mermaid sequence, state/failure, and data-boundary diagrams with quoted special-character labels.\n\nFor every diagram, record:",
            1,
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Specify agent request/response envelope, grounded citation schema, and escalation status contract.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Specify prompt/policy artifact versioning and evaluation fixture schema compatibility.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Specify trace IDs, model/prompt version tags, tool timeout/error counters, and escalation-rate alerts.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Specify pinned prompt/model rollback procedure and safe kill-switch fallback to human handoff.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Specify model/retrieval timeout, bounded retry policy, and deterministic fallback when provider fails.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: model / policy / prompt version",
            "Pin exact model ID, system policy revision, and versioned prompt template identifier.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: Tool permissions, timeout, retry, fallback",
            "Define explicit read/write tool allowlist, per-tool timeout, retry cap, and safe fallback on failure.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: knowledge provenance, citation, retention",
            "Restrict retrieval to approved tenant-scoped sources, enforce inline source citations, and set trace retention.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: human escalation and evaluation threshold",
            "Define confidence/safety escalation trigger, human handoff context payload, and release eval pass threshold.",
            "qa",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Implement grounded retrieval with source citations, strict tool allowlist/timeout policy, and human escalation gate.",
            "`pytest tests/agent_eval/`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Pinned prompt/policy config and curated evaluation corpus.",
            steps="Run grounded query, missing-source query, prompt-injection payload, unauthorized tool invocation, and escalation case.",
            expected="Grounded response cites approved sources; ungrounded, injected, or unauthorized tool cases refuse safely or escalate to human.",
            automated="yes",
            test_cmd="`pytest tests/agent_eval/`",
            extra_edge_bullets=[
                "AI-agent preset: verify hallucination/no-source refusal, untrusted-input prompt-injection resistance, unauthorized tool-call block, and human handoff payload.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/agent/policy/` | Define pinned model/prompt version config, tool allowlist, timeout/fallback, and human escalation rules. | `pytest tests/agent_eval/test_policy.py` |",
                "| T-02 | todo | yes | T-01 | AC-01 | `src/agent/retrieval/` | Implement tenant-scoped retrieval grounding and mandatory source-citation formatter. | `pytest tests/agent_eval/test_retrieval.py` |",
                "| T-03 | todo | no | T-02 | AC-01 | `tests/agent_eval/` | Add evaluation suite covering no-source refusal, prompt injection, blocked tool calls, and human handoff. | `pytest tests/agent_eval/` |",
            ],
        )

    docs["2. Tech Spec.md"] = tech
    docs["3. QA Spec.md"] = qa
    docs["4. Tasks.md"] = tasks
    return docs


def hydrate_spec_content(content: str, title: str) -> str:
    hydrated = content.replace("[Feature name]", title)
    match = FRONTMATTER_RE.match(hydrated)
    if match:
        fm_open, fm_body, fm_close = match.groups()
        status_match = re.search(r"^status:[ \t]*(.*?)[ \t]*$", fm_body, re.M)
        status_val = status_match.group(1).strip().strip("'\"").lower() if status_match else ""
        if status_val == "draft":
            fm_body = APPROVAL_FIELD_RE.sub(r"\1:", fm_body)
            hydrated = fm_open + fm_body + fm_close + hydrated[match.end() :]
    return hydrated


def write_new_file_exclusive(path: Path, content: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a 4-file Spec-Driven Development feature pack."
    )
    parser.add_argument(
        "slug",
        nargs="?",
        help="Lowercase kebab-case feature slug (e.g. user-auth).",
    )
    parser.add_argument(
        "--title",
        help="Human-readable feature title (defaults to title-cased slug).",
    )
    parser.add_argument(
        "--preset",
        help="Built-in preset (general, web-api, cli-tool, ai-agent) or custom preset under docs/templates/presets/<name>.",
    )
    parser.add_argument(
        "--plain",
        action="store_true",
        help="Create <slug> without an auto-allocated NNN- numeric prefix.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview target directory and files without modifying the filesystem.",
    )
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List built-in and custom presets and exit.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)

    if args.list_presets:
        return list_presets()

    if not args.slug:
        fail("missing required <slug> argument (or pass --list-presets)")

    slug = args.slug
    if not SLUG_RE.fullmatch(slug):
        fail(
            f"invalid feature slug '{slug}' "
            "(expected lowercase kebab-case matching ^[a-z0-9]+(?:-[a-z0-9]+)*$)"
        )

    if args.title is not None:
        title = args.title.strip()
        if not title or "\n" in title or "\r" in title:
            fail("--title must be a non-empty single-line string")
    else:
        title = " ".join(part.capitalize() for part in slug.split("-"))

    preset_name = resolve_preset_name(args.preset)

    features_root = ensure_no_symlinks(
        ROOT, ("docs", "current", "05 - Product Features"), must_exist=True
    )
    if not features_root.is_dir():
        fail("docs/current/05 - Product Features is not a directory")

    template_dir = ensure_no_symlinks(
        ROOT, ("docs", "templates", "feature-spec-template"), must_exist=True
    )
    if not template_dir.is_dir():
        fail("docs/templates/feature-spec-template is not a directory")

    base_docs: dict[str, str] = {}
    for spec_name in CANONICAL_SPECS:
        spec_path = ensure_no_symlinks(
            ROOT, ("docs", "templates", "feature-spec-template", spec_name), must_exist=True
        )
        if not spec_path.is_file():
            fail(f"canonical spec template is not a regular file: {spec_path.relative_to(ROOT)}")
        base_docs[spec_name] = spec_path.read_text(encoding="utf-8")

    presets_root = ensure_no_symlinks(ROOT, ("docs", "templates", "presets"), must_exist=False)
    if presets_root.exists() and not presets_root.is_dir():
        fail("docs/templates/presets exists and is not a directory")
    custom_dir = presets_root / preset_name

    ordered_files: list[tuple[str, str]] = []
    if custom_dir.exists() or custom_dir.is_symlink():
        custom_files = validate_custom_preset_dir(custom_dir, preset_name)
        custom_map = {path.name: path.read_text(encoding="utf-8") for path in custom_files}
        merged = dict(base_docs)
        for spec_name in CANONICAL_SPECS:
            if spec_name in custom_map:
                merged[spec_name] = custom_map[spec_name]
        if "README.md" in custom_map:
            ordered_files.append(("README.md", hydrate_spec_content(custom_map["README.md"], title)))
        for spec_name in CANONICAL_SPECS:
            ordered_files.append((spec_name, hydrate_spec_content(merged[spec_name], title)))
        for extra_name in sorted(custom_map):
            if extra_name not in CANONICAL_SPECS and extra_name != "README.md":
                ordered_files.append((extra_name, hydrate_spec_content(custom_map[extra_name], title)))
    else:
        if preset_name not in BUILTIN_PRESETS:
            fail(
                f"unknown preset '{preset_name}' "
                f"(not in built-in presets {', '.join(BUILTIN_PRESETS)} and "
                f"custom directory docs/templates/presets/{preset_name} does not exist)"
            )
        overlaid = apply_builtin_overlay(preset_name, dict(base_docs))
        for spec_name in CANONICAL_SPECS:
            ordered_files.append((spec_name, hydrate_spec_content(overlaid[spec_name], title)))

    max_seq = 0
    for entry in sorted(features_root.iterdir(), key=lambda p: p.name):
        if entry.is_symlink():
            fail(f"symlink refused inside 05 - Product Features: {entry.name}")
        if not entry.is_dir():
            continue
        base_slug = SEQ_PREFIX_RE.sub("", entry.name)
        if entry.name == slug or base_slug == slug:
            fail(f"duplicate feature slug '{slug}' (conflicts with existing '{entry.name}')")
        seq_match = SEQ_PREFIX_RE.match(entry.name)
        if seq_match:
            max_seq = max(max_seq, int(seq_match.group(1)))

    if args.plain:
        folder_name = slug
    else:
        next_seq = max_seq + 1
        if next_seq > 999:
            fail("feature sequence number exceeded 999; pass --plain or archive old features")
        folder_name = f"{next_seq:03d}-{slug}"

    target_dir = features_root / folder_name
    if target_dir.exists() or target_dir.is_symlink():
        fail(f"target path already exists: {target_dir.relative_to(ROOT).as_posix()}")

    rel_target_dir = target_dir.relative_to(ROOT).as_posix()
    if args.dry_run:
        print(f"DRY-RUN: would scaffold {rel_target_dir} (preset: {preset_name}, title: {title})")
        for filename, _content in ordered_files:
            print(f"  {rel_target_dir}/{filename}")
        return 0

    target_dir.mkdir(parents=False, exist_ok=False)
    for filename, content in ordered_files:
        write_new_file_exclusive(target_dir / filename, content)

    print(f"OK: scaffolded {rel_target_dir} (preset: {preset_name}, files: {len(ordered_files)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
