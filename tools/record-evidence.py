#!/usr/bin/env python3
"""Record per-task execution evidence with secret scanning, ANSI stripping, and AC hydration."""

import sys

sys.dont_write_bytecode = True

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import shlex
import stat
import subprocess
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

INLINE_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PEM private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub personal/app token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("API secret key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
)
INLINE_CREDENTIALED_URI_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://([^/\s:@]+):([^/\s@]+)@")
INLINE_ALLOWED_CREDENTIAL_PLACEHOLDERS = {
    "user:pass",
    "username:password",
    "<user>:<pass>",
    "<user>:<password>",
    "<username>:<password>",
    "placeholder:placeholder",
    "***:***",
    "redacted:redacted",
}
INLINE_FORBIDDEN_PLACEHOLDERS = {"draft", "todo", "tbd", "pending", "n/a", "none", "-"}

_DV_MODULE = None
_DV_IMPORT_ERR: str | None = None
try:
    import docs_validation as _dv  # noqa: E402

    _DV_MODULE = _dv
except ImportError as exc:
    _DV_IMPORT_ERR = str(exc)

SECRET_PATTERNS = getattr(_DV_MODULE, "SECRET_PATTERNS", INLINE_SECRET_PATTERNS)
CREDENTIALED_URI_RE = getattr(_DV_MODULE, "CREDENTIALED_URI_RE", INLINE_CREDENTIALED_URI_RE)
ALLOWED_CREDENTIAL_PLACEHOLDERS = getattr(
    _DV_MODULE, "ALLOWED_CREDENTIAL_PLACEHOLDERS", INLINE_ALLOWED_CREDENTIAL_PLACEHOLDERS
)
FORBIDDEN_APPROVED_PLACEHOLDERS = getattr(
    _DV_MODULE, "FORBIDDEN_APPROVED_PLACEHOLDERS", INLINE_FORBIDDEN_PLACEHOLDERS
)

DEFAULT_ROOT = SCRIPT_DIR.parent
TASK_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,80}$")
AC_ID_RE = re.compile(r"^AC-\d+$")
TASK_ROW_ID_RE = re.compile(r"^T-\d+$")
ANSI_CSI_RE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
ANSI_OSC_RE = re.compile(r"\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)")
ANSI_ESC_RE = re.compile(r"\x1b[@-Z\\-_]")
DISALLOWED_CONTROL_RE = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _is_source_template_repository(root: Path) -> bool:
    if _DV_MODULE is not None and hasattr(_DV_MODULE, "is_source_template_repository"):
        return bool(_DV_MODULE.is_source_template_repository(root))
    manifest_path = root / "template-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return False
    if not (root / "lib" / "installer_lib.py").is_file() or not (root / "docs" / "internal").is_dir():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        isinstance(manifest, dict)
        and manifest.get("template") == "ai-agent-obsidian-project-template"
        and "requested_models" not in manifest
        and "selected_models" not in manifest
    )


def _resolve_git_toplevel(root: Path) -> Path | None:
    if _DV_MODULE is not None and hasattr(_DV_MODULE, "resolve_git_toplevel"):
        return _DV_MODULE.resolve_git_toplevel(root)
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return Path(proc.stdout.strip()).resolve()
    except OSError:
        return None


def _require_feature_helpers() -> object:
    required = (
        "MINI_SPEC_FILE",
        "_extract_section_table_rows",
        "parse_execution_tasks",
        "parse_frontmatter",
        "read_markdown",
        "resolve_active_feature_dir",
    )
    if _DV_MODULE is None:
        raise ValueError(
            f"record-evidence.py --feature requires docs_validation.py in {SCRIPT_DIR} "
            f"(run 'setup.sh --update' to restore the validator bundle): {_DV_IMPORT_ERR}"
        )
    missing = [name for name in required if not hasattr(_DV_MODULE, name)]
    if missing:
        raise ValueError(
            f"record-evidence.py --feature requires an up-to-date docs_validation.py in {SCRIPT_DIR} "
            f"(missing: {', '.join(missing)}; run 'setup.sh --update' to restore the validator bundle)"
        )
    return _DV_MODULE


def _fallback_parse_frontmatter(text: str) -> dict[str, str]:
    if _DV_MODULE is not None and hasattr(_DV_MODULE, "parse_frontmatter"):
        return _DV_MODULE.parse_frontmatter(text)
    normalized = text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", normalized, flags=re.S)
    if not match:
        return {}
    data: dict[str, str] = {}
    for line in (match.group(1) or "").split("\n"):
        if line.startswith((" ", "\t")):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-") or ":" not in line:
            continue
        key, raw_val = line.split(":", 1)
        val = raw_val.strip()
        if not val or val.startswith("#"):
            parsed_val = ""
        elif val[0] in {'"', "'"}:
            quote = val[0]
            idx = 1
            out: list[str] = []
            parsed_val = None
            while idx < len(val):
                ch = val[idx]
                if quote == '"' and ch == "\\" and idx + 1 < len(val):
                    nxt = val[idx + 1]
                    escapes = {'"': '"', "\\": "\\", "n": "\n", "r": "\r", "t": "\t", "/": "/"}
                    out.append(escapes.get(nxt, nxt))
                    idx += 2
                    continue
                if quote == "'" and ch == "'" and idx + 1 < len(val) and val[idx + 1] == "'":
                    out.append("'")
                    idx += 2
                    continue
                if ch == quote:
                    trailing = val[idx + 1 :].strip()
                    if not trailing or trailing.startswith("#"):
                        parsed_val = "".join(out).strip()
                    break
                out.append(ch)
                idx += 1
            if parsed_val is None:
                parsed_val = val[1:-1].strip() if len(val) >= 2 and val[-1] == quote else val
        else:
            parsed_val = re.split(r"[ \t]+#", val, maxsplit=1)[0].strip()
        if key.strip():
            data[key.strip()] = parsed_val
    return data


def _read_bytes_nofollow(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"{path}: symlink refused")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"{path}: unable to open regular file safely ({exc})") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
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


def _walk_inside_root_no_symlinks(root: Path, raw_rel: str, label: str) -> Path:
    if root.is_symlink():
        raise ValueError(f"repository root cannot be a symlink: {root}")
    cleaned = raw_rel.strip()
    if not cleaned:
        raise ValueError(f"{label}: path must not be empty")
    if cleaned.startswith(":"):
        raise ValueError(f"{label}: path cannot start with ':' ({raw_rel})")
    if "\\" in cleaned or any(ord(ch) < 32 or ord(ch) == 127 for ch in cleaned):
        raise ValueError(f"{label}: path contains invalid characters ({raw_rel})")
    if cleaned.startswith("/") or cleaned.startswith("~"):
        raise ValueError(f"{label}: path must be relative to repository root ({raw_rel})")
    rel_path = Path(cleaned)
    cur = root
    for part in rel_path.parts:
        if part in ("", "."):
            continue
        if part == "..":
            if cur == root:
                raise ValueError(f"{label}: path escapes repository root ({raw_rel})")
            cur = cur.parent
            continue
        cur = cur / part
        if cur.is_symlink():
            raise ValueError(f"{label}: symlink path component refused: {cur.relative_to(root)}")
    if cur.exists() and not cur.resolve().is_relative_to(root):
        raise ValueError(f"{label}: path escapes repository root ({raw_rel})")
    return cur


def _validate_metadata_scalar(
    raw: str,
    flag_name: str,
    *,
    required: bool,
    allow_backslash: bool = False,
) -> str:
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in raw):
        raise ValueError(f"{flag_name} cannot contain control characters or newlines")
    cleaned = raw.strip()
    if not cleaned:
        if required:
            raise ValueError(f"{flag_name} must not be empty")
        return ""
    if cleaned.lower() in FORBIDDEN_APPROVED_PLACEHOLDERS:
        raise ValueError(f"{flag_name} forbids placeholder value '{cleaned}'")
    if not allow_backslash and "\\" in cleaned:
        raise ValueError(f"{flag_name} cannot contain raw backslash '\\'")
    return cleaned


def _format_table_cell(value: str) -> str:
    if any((ord(ch) < 32 and ch not in ("\n", "\r", "\t")) or ord(ch) == 127 for ch in value):
        raise ValueError("table cell value cannot contain control characters")
    flattened = re.sub(r"[\r\n]+", " ", value).strip()
    return re.sub(
        r"(\\*)\|",
        lambda m: m.group(0) if len(m.group(1)) % 2 == 1 else m.group(1) + r"\|",
        flattened,
    )


def _strip_ansi_and_control(text: str) -> str:
    cleaned = ANSI_OSC_RE.sub("", text)
    cleaned = ANSI_CSI_RE.sub("", cleaned)
    cleaned = ANSI_ESC_RE.sub("", cleaned)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    return DISALLOWED_CONTROL_RE.sub("", cleaned)


def _scan_secrets(raw_text: str, label: str) -> None:
    for variant_name, text in (("raw", raw_text), ("ANSI-stripped", _strip_ansi_and_control(raw_text))):
        for sec_label, pat in SECRET_PATTERNS:
            if pat.search(text):
                raise ValueError(
                    f"{label}: high-confidence secret detected ({sec_label} in {variant_name} content); "
                    "redact credentials before recording evidence"
                )
        for uri_match in CREDENTIALED_URI_RE.finditer(text):
            user_part = uri_match.group(1).strip()
            pass_part = uri_match.group(2).strip()
            pair = f"{user_part}:{pass_part}".lower()
            if pair in ALLOWED_CREDENTIAL_PLACEHOLDERS:
                continue
            if (user_part.startswith("<") and pass_part.endswith(">")) or "${" in pair or "{{" in pair:
                continue
            raise ValueError(
                f"{label}: high-confidence credentialed URI detected in {variant_name} content; redact before recording"
            )


def _assert_not_gitignored(git_top: Path, root: Path, target_path: Path, label: str) -> None:
    if not target_path.is_relative_to(git_top):
        return
    _walk_inside_root_no_symlinks(root, target_path.relative_to(root).as_posix(), label)
    git_rel = target_path.relative_to(git_top).as_posix()
    if git_rel.startswith(":"):
        raise ValueError(f"{label}: path cannot start with ':' ({git_rel})")
    try:
        proc = subprocess.run(
            ["git", "-C", str(git_top), "check-ignore", "-q", "--", git_rel],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        raise ValueError(f"git binary unavailable for check-ignore: {exc}") from exc
    if proc.returncode == 0:
        raise ValueError(f"{label}: target path '{git_rel}' is ignored by .gitignore")
    if proc.returncode != 1:
        err = proc.stderr.strip() or f"exit {proc.returncode}"
        raise ValueError(f"{label}: git check-ignore failed for '{git_rel}': {err}")


def _write_all_fd(fd: int, data: bytes) -> None:
    view = memoryview(data)
    total = 0
    while total < len(view):
        written = os.write(fd, view[total:])
        if written <= 0:
            raise OSError("short write")
        total += written


def _write_new_exclusive(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite existing path: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o644)
    try:
        _write_all_fd(fd, data)
    except BaseException:
        os.close(fd)
        try:
            path.unlink()
        except OSError:
            pass
        raise
    os.close(fd)


def _atomic_replace_bytes(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise ValueError(f"{path}: symlink refused before write")
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        _write_all_fd(fd, data)
        os.fsync(fd)
        os.close(fd)
        fd = -1
        os.chmod(tmp_path, 0o644)
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


def _parse_ac_list(raw_ac: str | None) -> tuple[bool, list[str]]:
    if raw_ac is None:
        return False, []
    cleaned = raw_ac.strip()
    if not cleaned:
        raise ValueError("--ac must not be empty")
    if cleaned.lower() == "all":
        return True, []
    tokens: list[str] = []
    for item in cleaned.split(","):
        tok = item.strip().upper()
        if not AC_ID_RE.fullmatch(tok):
            raise ValueError(f"invalid --ac token '{item.strip()}' (expected AC-xx or 'all')")
        if tok not in tokens:
            tokens.append(tok)
    if not tokens:
        raise ValueError("--ac must specify at least one AC-xx or 'all'")
    return False, tokens


def _render_evidence_markdown(
    *,
    status: str,
    task_id: str,
    recorded_at: str,
    recorded_by: str,
    source_revision: str,
    completed_at: str,
    reviewer: str,
    environment: str,
    artifact_sha256: str,
    artifact_rel_posix: str,
    feature_rel: str | None,
    ac_rows: list[tuple[str, str, str, str, str]],
) -> str:
    def _yaml_line(key: str, val: str, quote: bool = True) -> str:
        if not val:
            return f"{key}:"
        if quote:
            return f"{key}: {json.dumps(val, ensure_ascii=False)}"
        return f"{key}: {val}"

    fm_lines = [
        "---",
        f"status: {status}",
        _yaml_line("task_id", task_id, quote=True),
        _yaml_line("recorded_at", recorded_at, quote=True),
        _yaml_line("recorded_by", recorded_by, quote=True),
        _yaml_line("source_revision", source_revision, quote=False),
        _yaml_line("completed_at", completed_at, quote=True),
        _yaml_line("reviewer", reviewer, quote=True),
        _yaml_line("environment", environment, quote=True),
        _yaml_line("output_artifact_sha256", artifact_sha256, quote=False),
        _yaml_line("output_artifact_path", artifact_rel_posix, quote=True),
        "---",
    ]

    spec_source_col = f"`{feature_rel}`" if feature_rel else "N/A (Tier S / standalone task)"
    spec_why_col = (
        "Approved feature specification and AC contract" if feature_rel else "Task scope outside feature spec folder"
    )

    body_lines = [
        f"# Task Evidence — {task_id}",
        "",
        "Không tự bịa trích dẫn, đầu ra lệnh hoặc kết quả kiểm thử; mọi thông tin chưa thể kiểm chứng phải ghi rõ là `Unknown`.",
        "",
        "## Authority and sources read",
        "",
        "| Source | Revision / file:line | Why it is authoritative |",
        "|---|---|---|",
        "| User-approved requirement | Approved user instruction / task scope | Authoritative target behavior and acceptance scope. |",
        f"| Approved Product / Tech / QA / Mini Spec | {spec_source_col} | {spec_why_col} |",
        f"| Source / migration / inventory | `{source_revision or 'working-tree'}` | Recorded source state for verification. |",
        "",
        "## Acceptance criteria and validation",
        "",
        "| AC | Change / implementation | Test or validation command | Result / exit code | Run at |",
        "|---|---|---|---|---|",
    ]
    for ac_id, change_col, cmd_col, res_col, run_at_col in ac_rows:
        body_lines.append(
            f"| {_format_table_cell(ac_id)} | {_format_table_cell(change_col)} | "
            f"{_format_table_cell(cmd_col)} | {_format_table_cell(res_col)} | {_format_table_cell(run_at_col)} |"
        )

    art_summary = (
        f"`{artifact_rel_posix}` (SHA-256: `{artifact_sha256}`)"
        if artifact_rel_posix
        else "Unknown (no artifact captured yet)"
    )
    body_lines.extend(
        [
            "",
            "## Fact, assumption, unknown",
            "",
            "| Type | Statement | Evidence / owner for confirmation |",
            "|---|---|---|",
            f"| Fact | Executed validation recorded for `{task_id}` in `{environment}`. | {art_summary} |",
            "| Assumption | Local validation environment matches declared project runtime dependencies. | Confirmed by operator / reviewer |",
            "| Unknown | External production/CI runtime behavior outside local scope was not executed directly unless captured in artifact. | See artifact log / CI run |",
            "",
            "## Safety and completion",
            "",
            f"- Kiểm tra môi trường chạy (`local/dev`) và an toàn dữ liệu (không để lộ secret, khoá truy cập hay thông tin cá nhân PII trong log/báo cáo): `{environment}`; secret-scanned before persistence.",
            f"- Đường dẫn file lưu kết quả chạy lệnh (`output_artifact_path`) và mã băm SHA-256 (`output_artifact_sha256`), hoặc nêu rõ lý do nếu chưa có: {art_summary}",
            "- Danh sách file mã nguồn đã sửa và các ghi chú tài liệu đã đồng bộ: See git diff / task owned paths.",
            "- Rủi ro tồn đọng và phương án hoàn tác (rollback): Revert task commit(s) if regression is detected.",
            f"- Người rà soát / xác nhận hoàn tất (`reviewer`): {reviewer or 'Pending'}",
            "",
        ]
    )
    return "\n".join(fm_lines + body_lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-id", required=True, help="Task identifier slug (e.g. T-01 or v0.7.0-validation).")
    parser.add_argument("--feature", help="Optional active feature folder or slug for AC hydration.")
    parser.add_argument("--task", help="Task ID (T-xx) within --feature to scope AC attribution.")
    parser.add_argument("--ac", help="Comma-separated AC-xx IDs or 'all' to scope AC validation rows.")
    parser.add_argument("--status", choices=("draft", "completed"), default="draft", help="Evidence record status (default: draft).")
    parser.add_argument("--mode", choices=("self", "head-sha"), default="self", help="Provenance mode for completed records (default: self).")
    parser.add_argument("--run-cmd", help="Shell command to execute and capture to an immutable log artifact.")
    parser.add_argument("--artifact", help="Existing repo-relative artifact file to bind without running a command.")
    parser.add_argument("--artifact-path", help="Custom .log/.txt path strictly inside <evidence-dir>/artifacts/ for --run-cmd/--exec.")
    parser.add_argument("--command", help="Command label recorded in the AC table when using --artifact.")
    parser.add_argument("--result", help="Result/exit-code string recorded in the AC table when using --artifact.")
    parser.add_argument("--timeout", type=int, default=600, help="Subprocess timeout in seconds (default: 600).")
    parser.add_argument("--by", help="Operator/agent identity recorded in recorded_by (required for completed).")
    parser.add_argument("--reviewer", help="Reviewer/approver identity recorded in reviewer (required for completed).")
    parser.add_argument("--environment", default="local/dev", help="Execution environment label (default: local/dev).")
    parser.add_argument("--evidence-dir", default="task-evidence", help="Target evidence directory relative to root (default: task-evidence).")
    parser.add_argument("--output", help="Custom direct .md file path inside --evidence-dir.")
    parser.add_argument("--overwrite-draft", action="store_true", help="Allow overwriting an existing draft record (never completed).")
    parser.add_argument("--dry-run", action="store_true", help="Preview evidence output without running commands or writing files.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Repository root (defaults to parent directory of tools/).")
    parser.add_argument(
        "--exec",
        dest="exec_cmd",
        nargs=argparse.REMAINDER,
        help="Execute argv directly with shell=False (must appear at end of command).",
    )
    return parser.parse_args(argv)


def _parse_exec_and_validate_modes(args: argparse.Namespace) -> list[str] | None:
    exec_argv: list[str] | None = None
    if args.exec_cmd is not None:
        exec_argv = list(args.exec_cmd)
        if exec_argv and exec_argv[0] == "--":
            exec_argv = exec_argv[1:]
        if not exec_argv:
            raise ValueError("--exec requires at least one command argument")

    input_modes = sum(
        [
            args.run_cmd is not None,
            exec_argv is not None,
            args.artifact is not None,
        ]
    )
    if input_modes > 1:
        raise ValueError("--run-cmd, --exec, and --artifact are mutually exclusive")
    if args.status == "completed" and input_modes == 0:
        raise ValueError("--status completed requires one of --run-cmd, --exec, or --artifact")
    if args.artifact_path is not None and args.artifact is not None:
        raise ValueError("--artifact-path cannot be combined with --artifact")
    if args.dry_run and (args.run_cmd is not None or exec_argv is not None):
        raise ValueError("--dry-run cannot be combined with --run-cmd or --exec")
    if args.status == "completed" and args.mode == "head-sha" and (args.run_cmd is not None or exec_argv is not None):
        raise ValueError(
            "--mode head-sha cannot be combined with --run-cmd/--exec under --status completed "
            "(a newly created log does not exist at HEAD yet; use --mode self or commit the log first and pass --artifact)"
        )
    return exec_argv


def _resolve_output_and_artifact_paths(
    root: Path,
    evidence_dir: Path,
    today_str: str,
    args: argparse.Namespace,
    will_write_log: bool,
) -> tuple[Path, Path, Path | None]:
    if args.output is not None:
        out_path = _walk_inside_root_no_symlinks(root, args.output, "--output")
        if out_path.parent != evidence_dir:
            raise ValueError(
                f"--output must be a direct .md child inside {evidence_dir.relative_to(root).as_posix()}"
            )
        if out_path.suffix != ".md" or out_path.name.startswith("_"):
            raise ValueError(f"--output must be a non-underscore .md filename (got '{out_path.name}')")
    else:
        out_path = evidence_dir / f"{today_str}-{args.task_id}.md"

    artifacts_dir = evidence_dir / "artifacts"
    if artifacts_dir.is_symlink():
        raise ValueError(f"symlink refused for artifacts directory: {artifacts_dir.relative_to(root).as_posix()}")

    art_path: Path | None = None
    if will_write_log:
        if args.artifact_path is not None:
            art_path = _walk_inside_root_no_symlinks(root, args.artifact_path, "--artifact-path")
            if not art_path.is_relative_to(artifacts_dir) or art_path == artifacts_dir:
                raise ValueError(
                    f"--artifact-path must reside strictly inside {artifacts_dir.relative_to(root).as_posix()}/"
                )
            if art_path.suffix not in {".log", ".txt"} or art_path.name.startswith("."):
                raise ValueError(f"--artifact-path must end with .log or .txt (got '{art_path.name}')")
        else:
            art_path = artifacts_dir / f"{today_str}-{args.task_id}.log"
    elif args.artifact is not None:
        art_path = _walk_inside_root_no_symlinks(root, args.artifact, "--artifact")
        if not art_path.is_file() or art_path.is_symlink():
            raise ValueError(f"--artifact does not exist as a regular file: {args.artifact}")
    return out_path, artifacts_dir, art_path


def _check_artifact_log_collisions(
    root: Path,
    evidence_dir: Path,
    out_path: Path,
    art_path: Path,
    overwrite_draft: bool,
) -> None:
    if art_path.is_symlink():
        raise ValueError(f"symlink refused for artifact log: {art_path.relative_to(root).as_posix()}")
    art_rel_posix = art_path.relative_to(root).as_posix()
    if evidence_dir.is_dir():
        for existing_md in sorted(evidence_dir.iterdir(), key=lambda p: p.name):
            if not existing_md.name.endswith(".md") or existing_md.is_symlink() or not existing_md.is_file():
                continue
            md_fm = _fallback_parse_frontmatter(
                _read_bytes_nofollow(existing_md).decode("utf-8-sig", errors="replace")
            )
            ref_art = md_fm.get("output_artifact_path", "").replace("\\", "/").strip()
            if ref_art != art_rel_posix:
                continue
            ref_st = md_fm.get("status", "").strip().lower()
            if ref_st == "completed":
                raise ValueError(
                    f"refusing to overwrite artifact '{art_rel_posix}' referenced by completed record "
                    f"{existing_md.relative_to(root).as_posix()}"
                )
            if existing_md != out_path:
                raise ValueError(
                    f"refusing to overwrite artifact '{art_rel_posix}' already referenced by "
                    f"{existing_md.relative_to(root).as_posix()}"
                )
    if art_path.exists() and not overwrite_draft:
        raise ValueError(
            f"refusing to overwrite existing artifact log '{art_rel_posix}'; "
            "pass --artifact-path or --overwrite-draft for an unlinked draft log"
        )


def _resolve_feature_ac_scope(
    root: Path,
    feature_arg: str | None,
    task_arg: str | None,
    ac_arg: str | None,
    is_completed: bool,
) -> tuple[str | None, list[tuple[str, str]], list[str]]:
    ac_all_flag, explicit_acs = _parse_ac_list(ac_arg)
    if task_arg is not None and not TASK_ROW_ID_RE.fullmatch(task_arg.strip()):
        raise ValueError(f"invalid --task '{task_arg}' (expected T-xx)")

    if feature_arg is None:
        if task_arg is not None:
            raise ValueError("--task requires --feature")
        if ac_all_flag:
            raise ValueError("--ac all requires --feature")
        return None, [], explicit_acs if explicit_acs else ["AC-01"]

    dv = _require_feature_helpers()
    feature_dir = dv.resolve_active_feature_dir(
        root, feature_arg, require_approved=False, exclude_all_done=False
    )
    feature_rel = feature_dir.relative_to(root).as_posix()
    mini_path = feature_dir / dv.MINI_SPEC_FILE
    p1_path = feature_dir / "1. Product Spec.md"
    p4_path = feature_dir / "4. Tasks.md"
    ac_source = mini_path if mini_path.is_file() else p1_path
    if not ac_source.is_file():
        raise ValueError(f"{feature_rel}: missing 1. Mini Spec.md or 1. Product Spec.md for AC hydration")
    ac_rows_raw = dv._extract_section_table_rows(
        ac_source.relative_to(root),
        dv.read_markdown(ac_source),
        "Acceptance criteria",
        ("id",),
        require_table=True,
    ) or []

    feature_ac_list: list[tuple[str, str]] = []
    seen_ac_ids: set[str] = set()
    for row in ac_rows_raw:
        scenario = row.get("scenario", "").strip()
        for ac_tok in re.findall(r"\bAC-\d+\b", row.get("id", "")):
            if ac_tok not in seen_ac_ids:
                seen_ac_ids.add(ac_tok)
                feature_ac_list.append((ac_tok, scenario))
    if not feature_ac_list:
        raise ValueError(f"{ac_source.relative_to(root).as_posix()}: no AC-xx rows found")

    task_acs: list[str] = []
    if task_arg is not None:
        tid_clean = task_arg.strip()
        tasks_source = mini_path if mini_path.is_file() else p4_path
        if not tasks_source.is_file():
            raise ValueError(f"{feature_rel}: missing 1. Mini Spec.md or 4. Tasks.md for --task lookup")
        parsed_tasks = (
            dv.parse_execution_tasks(
                tasks_source.relative_to(root),
                dv.read_markdown(tasks_source),
                require_table=True,
            )
            or []
        )
        matched = [t for t in parsed_tasks if t["task_id"] == tid_clean]
        if not matched:
            raise ValueError(f"{tasks_source.relative_to(root).as_posix()}: task '{tid_clean}' not found")
        task_acs = list(matched[0]["related_ac"])

    if ac_arg is not None:
        if ac_all_flag:
            attributed_acs = [ac_id for ac_id, _ in feature_ac_list]
        else:
            unknown_acs = [ac for ac in explicit_acs if ac not in seen_ac_ids]
            if unknown_acs:
                raise ValueError(
                    f"{feature_rel}: unknown AC ID(s) in --ac: {', '.join(unknown_acs)}"
                )
            attributed_acs = explicit_acs
    elif task_arg is not None:
        attributed_acs = task_acs
    else:
        attributed_acs = []
        if is_completed:
            raise ValueError(
                "--feature with --status completed requires --task <T-xx>, --ac <AC-xx,...>, or --ac all "
                "to scope verified AC rows"
            )

    if is_completed and not attributed_acs:
        raise ValueError(
            f"{feature_rel}: selected scope produced zero AC-xx rows to mark completed"
        )
    return feature_rel, feature_ac_list, attributed_acs


def _capture_command_log(
    root: Path,
    run_cmd: str | None,
    exec_argv: list[str] | None,
    timeout: int,
    is_completed: bool,
) -> tuple[bytes, str, str, str]:
    if run_cmd is not None:
        cmd_display = run_cmd
        try:
            proc = subprocess.run(run_cmd, shell=True, cwd=root, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"--run-cmd timed out after {timeout}s: {run_cmd}") from exc
    else:
        assert exec_argv is not None
        cmd_display = shlex.join(exec_argv)
        try:
            proc = subprocess.run(exec_argv, shell=False, cwd=root, capture_output=True, timeout=timeout)
        except OSError as exc:
            raise ValueError(f"--exec failed to start '{exec_argv[0]}': {exc}") from exc
        except subprocess.TimeoutExpired as exc:
            raise ValueError(f"--exec timed out after {timeout}s: {cmd_display}") from exc

    raw_stdout = proc.stdout.decode("utf-8", errors="replace")
    raw_stderr = proc.stderr.decode("utf-8", errors="replace")
    raw_combined = (
        f"$ {cmd_display}\n"
        f"[exit_code={proc.returncode}]\n"
        f"{raw_stdout}"
        + (f"\n--- stderr ---\n{raw_stderr}" if raw_stderr else "")
    )
    _scan_secrets(raw_combined, "captured command output")
    if is_completed and proc.returncode != 0:
        raise ValueError(
            f"command exited with code {proc.returncode}; refusing to create completed evidence"
        )

    clean_log = _strip_ansi_and_control(raw_combined)
    if not clean_log.endswith("\n"):
        clean_log += "\n"
    log_bytes = clean_log.encode("utf-8")
    art_sha256 = hashlib.sha256(log_bytes).hexdigest()
    cmd_label = f"`{cmd_display}`"
    result_label = f"{'PASS' if proc.returncode == 0 else 'FAIL'} / {proc.returncode}"
    return log_bytes, art_sha256, cmd_label, result_label


def _hash_bound_artifact(
    git_top: Path | None,
    head_sha: str,
    mode: str,
    art_path: Path,
    art_rel_str: str,
) -> str:
    raw_art_bytes = _read_bytes_nofollow(art_path)
    _scan_secrets(raw_art_bytes.decode("utf-8", errors="replace"), art_rel_str)

    if mode == "head-sha" and git_top is not None and head_sha:
        art_git_rel = art_path.relative_to(git_top).as_posix()
        try:
            head_art_bytes = subprocess.check_output(
                ["git", "--literal-pathspecs", "-C", str(git_top), "show", f"{head_sha}:{art_git_rel}"],
                stderr=subprocess.DEVNULL,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise ValueError(
                f"--mode head-sha requires '{art_rel_str}' to exist at HEAD ({head_sha})"
            ) from exc
        ho_proc = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(git_top), "hash-object", "--", art_git_rel],
            capture_output=True,
            text=True,
        )
        rp_proc = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(git_top), "rev-parse", "--verify", f"HEAD:{art_git_rel}"],
            capture_output=True,
            text=True,
        )
        if ho_proc.returncode != 0 or rp_proc.returncode != 0 or ho_proc.stdout.strip() != rp_proc.stdout.strip():
            raise ValueError(
                f"working-tree '{art_rel_str}' differs from HEAD ({head_sha}); commit changes or use --mode self"
            )
        return hashlib.sha256(head_art_bytes).hexdigest()

    effective_bytes = raw_art_bytes
    if git_top is not None and b"\r\n" in raw_art_bytes and art_path.is_relative_to(git_top):
        art_git_rel = art_path.relative_to(git_top).as_posix()
        ho_clean = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(git_top), "hash-object", "--", art_git_rel],
            capture_output=True,
            text=True,
        )
        ho_raw = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(git_top), "hash-object", "--no-filters", "--", art_git_rel],
            capture_output=True,
            text=True,
        )
        if ho_clean.returncode == 0 and ho_raw.returncode == 0 and ho_clean.stdout.strip() != ho_raw.stdout.strip():
            effective_bytes = raw_art_bytes.replace(b"\r\n", b"\n")
    return hashlib.sha256(effective_bytes).hexdigest()


def _build_ac_rows(
    feature_ac_list: list[tuple[str, str]],
    attributed_acs: list[str],
    task_id: str,
    cmd_label: str,
    result_label: str,
    run_at_str: str,
) -> list[tuple[str, str, str, str, str]]:
    has_run = bool(cmd_label or result_label)
    if feature_ac_list:
        attr_set = set(attributed_acs)
        return [
            (
                ac_id,
                scenario or f"Implemented `{task_id}`",
                cmd_label if ac_id in attr_set and has_run else "",
                result_label if ac_id in attr_set and has_run else "PENDING",
                run_at_str if ac_id in attr_set and has_run else "",
            )
            for ac_id, scenario in feature_ac_list
        ]
    return [
        (ac_id, f"Verified `{task_id}`", cmd_label, result_label, run_at_str)
        if has_run
        else (ac_id, "", "", "", "")
        for ac_id in attributed_acs
    ]


def _write_target_bytes(path: Path, data: bytes, had_existing: bool) -> None:
    if had_existing:
        _atomic_replace_bytes(path, data)
    else:
        _write_new_exclusive(path, data)


def _restore_or_unlink(path: Path, had_existing: bool, orig_bytes: bytes | None) -> None:
    if had_existing and orig_bytes is not None:
        try:
            _atomic_replace_bytes(path, orig_bytes)
        except BaseException:
            pass
    elif path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def _persist_and_self_validate(
    root: Path,
    evidence_dir: Path,
    artifacts_dir: Path,
    out_path: Path,
    art_path: Path | None,
    log_bytes: bytes | None,
    md_text: str,
    will_write_log: bool,
    is_completed: bool,
    mode: str,
) -> None:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    if will_write_log:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        if art_path is not None:
            art_path.parent.mkdir(parents=True, exist_ok=True)

    had_existing_out = out_path.exists()
    orig_out_bytes = _read_bytes_nofollow(out_path) if had_existing_out else None
    had_existing_log = bool(will_write_log and art_path is not None and art_path.exists())
    orig_log_bytes = _read_bytes_nofollow(art_path) if (had_existing_log and art_path is not None) else None

    try:
        if will_write_log and art_path is not None and log_bytes is not None:
            _write_target_bytes(art_path, log_bytes, had_existing_log)
        _write_target_bytes(out_path, md_text.encode("utf-8"), had_existing_out)

        validator_cmd = [
            sys.executable,
            "-B",
            str(SCRIPT_DIR / "validate-task-evidence.py"),
            "--root",
            str(root),
            "--evidence-dir",
            evidence_dir.relative_to(root).as_posix(),
        ]
        if not is_completed or mode == "self":
            validator_cmd.append("--allow-working-tree")
        val_proc = subprocess.run(validator_cmd, capture_output=True, text=True)
        if val_proc.returncode != 0:
            err = (val_proc.stderr or val_proc.stdout or "").strip()
            raise ValueError(f"evidence self-validation failed: {err}")
    except BaseException:
        _restore_or_unlink(out_path, had_existing_out, orig_out_bytes)
        if will_write_log and art_path is not None:
            _restore_or_unlink(art_path, had_existing_log, orig_log_bytes)
        raise


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.root.is_symlink():
        raise ValueError(f"repository root cannot be a symlink: {args.root}")
    root = args.root.resolve()

    if not TASK_ID_RE.fullmatch(args.task_id):
        raise ValueError(
            f"invalid --task-id '{args.task_id}' (expected ^[A-Za-z0-9][A-Za-z0-9._-]{{0,80}}$)"
        )
    if args.timeout < 1:
        raise ValueError("--timeout must be >= 1 second")

    exec_argv = _parse_exec_and_validate_modes(args)
    is_completed = args.status == "completed"
    recorded_by = _validate_metadata_scalar(args.by or "", "--by", required=is_completed)
    reviewer = _validate_metadata_scalar(args.reviewer or "", "--reviewer", required=is_completed)
    environment = _validate_metadata_scalar(args.environment, "--environment", required=True)

    evidence_dir = _walk_inside_root_no_symlinks(root, args.evidence_dir, "--evidence-dir")
    if evidence_dir.exists() and not evidence_dir.is_dir():
        raise ValueError(f"--evidence-dir is not a directory: {args.evidence_dir}")
    if not args.dry_run and _is_source_template_repository(root):
        canonical_internal = (root / "docs/internal/task-evidence").resolve()
        if evidence_dir.resolve() != canonical_internal:
            raise ValueError(
                "refusing to write outside docs/internal/task-evidence inside the source ai-project-template repository"
            )

    today_str = dt.date.today().isoformat()
    will_write_log = args.run_cmd is not None or exec_argv is not None
    out_path, artifacts_dir, art_path = _resolve_output_and_artifact_paths(
        root, evidence_dir, today_str, args, will_write_log
    )

    git_top = _resolve_git_toplevel(root)
    if is_completed and git_top is None:
        raise ValueError(f"--status completed with --mode {args.mode} requires a Git repository")
    if git_top is not None:
        if not root.is_relative_to(git_top):
            raise ValueError(f"repository root {root} escapes Git toplevel {git_top}")
        _assert_not_gitignored(git_top, root, out_path, "--output")
        if art_path is not None:
            _assert_not_gitignored(git_top, root, art_path, "--artifact-path" if will_write_log else "--artifact")

    head_sha = ""
    if args.mode == "head-sha" and git_top is not None:
        head_proc = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(git_top), "rev-parse", "--verify", "HEAD^{commit}"],
            capture_output=True,
            text=True,
        )
        if head_proc.returncode != 0:
            if is_completed:
                raise ValueError("--mode head-sha requires a committed HEAD")
        else:
            head_sha = head_proc.stdout.strip().lower()

    if out_path.is_symlink():
        raise ValueError(f"symlink refused for output path: {out_path.relative_to(root).as_posix()}")
    if out_path.exists():
        existing_fm = _fallback_parse_frontmatter(_read_bytes_nofollow(out_path).decode("utf-8-sig", errors="replace"))
        if existing_fm.get("status", "").strip().lower() == "completed":
            raise ValueError(f"refusing to overwrite locked completed evidence: {out_path.relative_to(root).as_posix()}")
        if not args.overwrite_draft:
            raise ValueError(
                f"evidence file already exists ({out_path.relative_to(root).as_posix()}); "
                "pass --overwrite-draft to replace an existing draft"
            )

    if will_write_log and art_path is not None:
        _check_artifact_log_collisions(root, evidence_dir, out_path, art_path, args.overwrite_draft)

    feature_rel, feature_ac_list, attributed_acs = _resolve_feature_ac_scope(
        root, args.feature, args.task, args.ac, is_completed
    )

    cmd_label = ""
    result_label = ""
    if args.artifact is not None:
        if args.command is not None:
            cmd_label = _validate_metadata_scalar(
                args.command, "--command", required=is_completed, allow_backslash=True
            )
        elif is_completed:
            raise ValueError("--artifact with --status completed requires --command")
        if args.result is not None:
            result_label = _validate_metadata_scalar(
                args.result, "--result", required=is_completed, allow_backslash=True
            )
        elif is_completed:
            raise ValueError("--artifact with --status completed requires --result")

    log_bytes: bytes | None = None
    art_sha256 = ""
    art_rel_str = art_path.relative_to(root).as_posix() if art_path is not None else ""
    run_at_str = dt.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %Z").strip()

    if will_write_log:
        log_bytes, art_sha256, cmd_label, result_label = _capture_command_log(
            root, args.run_cmd, exec_argv, args.timeout, is_completed
        )
    elif art_path is not None:
        art_sha256 = _hash_bound_artifact(git_top, head_sha, args.mode, art_path, art_rel_str)

    if args.mode == "head-sha":
        src_rev_val = head_sha if head_sha else "working-tree"
    else:
        src_rev_val = "self" if git_top is not None else "working-tree"

    completed_at_val = dt.datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z") if is_completed else ""
    ac_rows = _build_ac_rows(feature_ac_list, attributed_acs, args.task_id, cmd_label, result_label, run_at_str)
    md_text = _render_evidence_markdown(
        status=args.status,
        task_id=args.task_id,
        recorded_at=today_str,
        recorded_by=recorded_by,
        source_revision=src_rev_val,
        completed_at=completed_at_val,
        reviewer=reviewer,
        environment=environment,
        artifact_sha256=art_sha256,
        artifact_rel_posix=art_rel_str,
        feature_rel=feature_rel,
        ac_rows=ac_rows,
    )
    _scan_secrets(md_text, "rendered evidence")

    if args.dry_run:
        print(f"DRY-RUN: would write {out_path.relative_to(root).as_posix()} (status: {args.status}, mode: {args.mode})")
        if art_rel_str:
            print(f"  artifact: {art_rel_str} (sha256: {art_sha256 or 'pending'})")
        print(f"  attributed ACs: {', '.join(attributed_acs) if attributed_acs else 'none (draft pending)'}")
        return 0

    _persist_and_self_validate(
        root,
        evidence_dir,
        artifacts_dir,
        out_path,
        art_path,
        log_bytes,
        md_text,
        will_write_log,
        is_completed,
        args.mode,
    )

    print(
        f"PASS: recorded {out_path.relative_to(root).as_posix()} "
        f"(status: {args.status}, mode: {args.mode}"
        + (f", artifact: {art_rel_str}, sha256: {art_sha256}" if art_rel_str else "")
        + ")"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
