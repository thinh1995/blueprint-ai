#!/usr/bin/env python3
"""Shared zero-dependency core primitives for SDD tools and validators."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import json
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

SDD_CORE_API_VERSION = 1

EMPTY_TREE_SHA1 = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
REGULAR_GIT_BLOB_MODES = frozenset({"100644", "100755"})

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

FORBIDDEN_URI_SCHEMES = ("file:", "javascript:", "data:", "vbscript:", "obsidian:")
ALLOWED_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
WIKILINK_RE = re.compile(r"(!?)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("PEM private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AWS access key ID", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("GitHub personal/app token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
    ("GitHub fine-grained token", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{20,}\b")),
    ("API secret key", re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
)
CREDENTIALED_URI_RE = re.compile(r"[A-Za-z][A-Za-z0-9+.-]*://([^/\s:@]+):([^/\s@]+)@")
ALLOWED_CREDENTIAL_PLACEHOLDERS = {
    "user:pass",
    "username:password",
    "<user>:<pass>",
    "<user>:<password>",
    "<username>:<password>",
    "placeholder:placeholder",
    "***:***",
    "redacted:redacted",
}
FORBIDDEN_APPROVED_PLACEHOLDERS = {
    "draft",
    "todo",
    "tbd",
    "pending",
    "n/a",
    "none",
    "-",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_bytes_nofollow(path: Path) -> tuple[bytes, int]:
    """Read a regular file via O_NOFOLLOW + fstat(S_ISREG), returning (bytes, mode)."""
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


def read_text_nofollow(path: Path) -> str:
    """Read UTF-8 (with optional BOM) regular file via O_NOFOLLOW and normalize line endings."""
    raw, _mode = read_bytes_nofollow(path)
    try:
        return raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{path}: invalid UTF-8 encoding ({exc})") from exc


def _write_all_fd(fd: int, data: bytes) -> None:
    view = memoryview(data)
    total = 0
    while total < len(view):
        written = os.write(fd, view[total:])
        if written <= 0:
            raise OSError("short write")
        total += written


def atomic_write_bytes(path: Path, data: bytes, mode: int = 0o644) -> None:
    """Atomically write bytes via sibling temporary file + fsync + chmod + os.replace."""
    require(not path.is_symlink(), f"{path}: symlink refused before write")
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        _write_all_fd(fd, data)
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


def write_new_exclusive(path: Path, data: bytes, mode: int = 0o644) -> None:
    """Create a brand-new regular file using O_CREAT | O_EXCL | O_NOFOLLOW."""
    if path.exists() or path.is_symlink():
        raise ValueError(f"refusing to overwrite existing path: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, mode)
    except FileExistsError as exc:
        raise ValueError(f"refusing to overwrite existing path: {path}") from exc
    except OSError as exc:
        raise ValueError(f"{path}: unable to create regular file safely ({exc})") from exc
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


def walk_lexical_no_symlink(
    root_resolved: Path,
    start_dir: Path,
    rel_target: str,
    escape_msg: str,
    symlink_msg: str,
    err_prefix: str,
) -> Path:
    """Lexically traverse rel_target from start_dir inside root_resolved, refusing symlinks."""
    require(not root_resolved.is_symlink(), f"{err_prefix}: repository root cannot be a symlink")
    require(start_dir.is_relative_to(root_resolved), escape_msg)
    cur = root_resolved
    for part in start_dir.relative_to(root_resolved).parts:
        cur = cur / part
        require(not cur.is_symlink(), symlink_msg)
    for part in rel_target.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            require(cur != root_resolved, escape_msg)
            cur = cur.parent
            continue
        cur = cur / part
        require(not cur.is_symlink(), symlink_msg)
    try:
        resolved = cur.resolve()
    except OSError as exc:
        raise ValueError(f"{err_prefix}: invalid link target {rel_target} ({exc})") from exc
    require(resolved.is_relative_to(root_resolved), escape_msg)
    return resolved


def verify_git_root_no_symlink(git_root: Path, git_top: Path, *, err_prefix: str) -> Path:
    """Verify no symlinked directory sits between git_top and git_root."""
    require(not git_root.is_symlink(), f"{err_prefix}: project root cannot be a symlink: {git_root}")
    abs_git_root = Path(os.path.abspath(git_root))
    tail_parts: tuple[str, ...] | None = None
    for candidate in (abs_git_root, *abs_git_root.parents):
        try:
            if candidate.is_symlink():
                continue
            if candidate.exists() and candidate.resolve() == git_top:
                tail_parts = abs_git_root.parts[len(candidate.parts) :]
                break
        except OSError:
            continue
    if tail_parts is None:
        raise ValueError(f"{err_prefix}: symlinked directory between git toplevel and project root refused")
    return walk_lexical_no_symlink(
        git_top,
        git_top,
        "/".join(tail_parts),
        escape_msg=f"{err_prefix}: project root escapes git toplevel",
        symlink_msg=f"{err_prefix}: symlinked directory between git toplevel and project root refused",
        err_prefix=err_prefix,
    )


def resolve_git_toplevel(root: Path) -> Path | None:
    """Return resolved Git repository toplevel containing root, or None if unavailable."""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if proc.returncode != 0:
        return None
    raw_top = proc.stdout.strip()
    if not raw_top:
        return None
    try:
        return Path(raw_top).resolve()
    except OSError:
        return None


def is_source_template_repository(root: Path) -> bool:
    """Return True if root is the canonical ai-project-template source repository."""
    manifest_path = root / "template-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        return False
    lib_path = root / "lib" / "installer_lib.py"
    internal_dir = root / "docs" / "internal"
    if lib_path.is_symlink() or not lib_path.is_file() or internal_dir.is_symlink() or not internal_dir.is_dir():
        return False
    try:
        manifest = json.loads(read_text_nofollow(manifest_path))
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (
        isinstance(manifest, dict)
        and manifest.get("template") == "ai-agent-obsidian-project-template"
        and "requested_models" not in manifest
        and "selected_models" not in manifest
    )


def strip_outer_backticks(value: str) -> str:
    """Unwrap matching outer backtick code spans around a scalar table cell."""
    stripped = value.strip()
    match = re.fullmatch(r"(`+)([^`]*)\1", stripped)
    if match:
        return match.group(2).strip()
    return stripped


def strip_fenced_code(markdown_text: str) -> str:
    """Remove CommonMark fenced code blocks while preserving line structure."""
    text = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    out_lines: list[str] = []
    fence_char = ""
    fence_len = 0
    for line in text.split("\n"):
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


def strip_code(markdown_text: str) -> str:
    """Remove fenced blocks and CommonMark inline code spans before scanning markers."""
    without_fences = strip_fenced_code(markdown_text)
    return re.sub(r"(`+)([^\n]*?)\1", "", without_fences)


def strip_frontmatter_and_bom(markdown_text: str) -> str:
    """Strip UTF-8 BOM, normalize CRLF/CR to LF, and strip leading YAML frontmatter."""
    text = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", text, flags=re.DOTALL)
    if match:
        return text[match.end() :]
    return text


def _strip_yaml_scalar(raw_val: str) -> str:
    val = raw_val.strip()
    if not val or val.startswith("#"):
        return ""
    if val[0] in {'"', "'"}:
        quote = val[0]
        idx = 1
        out: list[str] = []
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
                    return "".join(out).strip()
                break
            out.append(ch)
            idx += 1
        if len(val) >= 2 and val[-1] == quote:
            return val[1:-1].strip()
        return val
    return re.split(r"[ \t]+#", val, maxsplit=1)[0].strip()


def iter_frontmatter_entries(markdown_text: str) -> list[tuple[str, str]]:
    text = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", text, flags=re.DOTALL)
    if not match:
        return []
    entries: list[tuple[str, str]] = []
    for line in (match.group(1) or "").split("\n"):
        if line.startswith((" ", "\t")):
            continue
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("-") or ":" not in line:
            continue
        key, raw_val = line.split(":", 1)
        key = key.strip()
        if key:
            entries.append((key, raw_val))
    return entries


def parse_frontmatter(markdown_text: str) -> dict[str, str]:
    """Parse optional leading top-level YAML scalar frontmatter (skipping indented block/list lines)."""
    return {key: _strip_yaml_scalar(raw_val) for key, raw_val in iter_frontmatter_entries(markdown_text)}


def split_table_row(line: str) -> list[str] | None:
    """Split a pipe-delimited Markdown table row while respecting escaped '\\|' pipes."""
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    m_tail = re.search(r"(\\*)\|$", stripped)
    if m_tail and len(m_tail.group(1)) % 2 == 1:
        return None
    cells: list[str] = []
    last = 1
    for m in re.finditer(r"(\\*)\|", stripped[1:]):
        bs = m.group(1)
        if len(bs) % 2 == 1:
            continue
        pipe_idx = 1 + m.end() - 1
        raw_cell = stripped[last:pipe_idx]
        unescaped = re.sub(
            r"(\\*)\|",
            lambda pm: pm.group(0) if len(pm.group(1)) % 2 == 0 else pm.group(1)[:-1] + "|",
            raw_cell,
        )
        cells.append(unescaped.strip())
        last = pipe_idx + 1
    return cells or None


def parse_markdown_link_destination(raw_inside: str) -> str:
    """Extract destination from inside '[label](...)', stripping optional \"title\", 'title', or (title)."""
    inside = raw_inside.strip()
    if inside.startswith("<"):
        gt = inside.find(">")
        if gt != -1:
            return inside[1:gt].strip()
    no_title = re.sub(r"""[ \t]+(?:"[^"\r\n]*"|'[^'\r\n]*')$""", "", inside).strip()
    m_paren_title = re.match(r"^(\S+?)[ \t]+\([^)\r\n]*\)$", no_title)
    if m_paren_title:
        return m_paren_title.group(1).strip()
    return no_title


def iter_markdown_link_targets(cleaned: str) -> list[str]:
    """Extract standard Markdown '[label](dest)' link targets from code-stripped Markdown text."""
    targets: list[str] = []
    idx = 0
    n = len(cleaned)
    while idx < n:
        lb = cleaned.find("[", idx)
        if lb == -1:
            break
        bs = 0
        k = lb - 1
        while k >= 0 and cleaned[k] == "\\":
            bs += 1
            k -= 1
        if bs % 2 == 1:
            idx = lb + 1
            continue
        rb = lb + 1
        while rb < n and cleaned[rb] not in "\r\n":
            if cleaned[rb] == "\\" and rb + 1 < n and cleaned[rb + 1] not in "\r\n":
                rb += 2
                continue
            if cleaned[rb] in "[]":
                break
            rb += 1
        if rb >= n or cleaned[rb] != "]" or rb + 1 >= n or cleaned[rb + 1] != "(":
            idx = lb + 1
            continue
        p = rb + 2
        while p < n and cleaned[p] in " \t":
            p += 1
        if p < n and cleaned[p] == "<":
            gt = p + 1
            while gt < n and cleaned[gt] not in ">\r\n":
                if cleaned[gt] == "\\" and gt + 1 < n and cleaned[gt + 1] not in "\r\n":
                    gt += 2
                    continue
                gt += 1
            if gt < n and cleaned[gt] == ">":
                tail_m = re.match(
                    r"""^[ \t]*(?:(?:"[^"\r\n]*"|'[^'\r\n]*'|\([^)\r\n]*\))[ \t]*)?\)""",
                    cleaned[gt + 1 :],
                )
                if tail_m is not None:
                    targets.append(cleaned[p + 1 : gt].strip())
                    idx = gt + 1 + tail_m.end()
                    continue
        else:
            depth = 1
            q = p
            while q < n and depth > 0 and cleaned[q] not in "\r\n":
                if cleaned[q] == "\\" and q + 1 < n and cleaned[q + 1] not in "\r\n":
                    q += 2
                    continue
                if cleaned[q] == "(":
                    depth += 1
                elif cleaned[q] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                q += 1
            if depth == 0:
                targets.append(parse_markdown_link_destination(cleaned[p:q]))
                idx = q + 1
                continue
        idx = rb + 1
    return targets


class GitCatFileBatch:
    """Streaming 'git cat-file --batch-check' / '--batch' session with frame & mode safety."""

    def __init__(self, git_top: Path) -> None:
        self.git_top = git_top
        self._check_proc: subprocess.Popen[bytes] | None = None
        self._blob_proc: subprocess.Popen[bytes] | None = None
        self.history_cache: dict[str, list[tuple[str, str, dict[str, str]]]] = {}

    @staticmethod
    def _guard_spec(spec: str) -> bytes:
        if (
            not isinstance(spec, str)
            or not spec
            or spec.startswith('"')
            or any(ch in spec for ch in ("\n", "\r", "\x00"))
        ):
            raise ValueError(f"unsafe git object spec refused: {spec!r}")
        return (spec + "\n").encode("utf-8")

    def _reset_proc(self, attr: str) -> None:
        proc: subprocess.Popen[bytes] | None = getattr(self, attr, None)
        setattr(self, attr, None)
        if proc is None:
            return
        for pipe in (proc.stdin, proc.stdout):
            if pipe is not None:
                try:
                    pipe.close()
                except OSError:
                    pass
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

    def _ensure_proc(self, mode_flag: str) -> subprocess.Popen[bytes]:
        attr = "_check_proc" if mode_flag == "--batch-check" else "_blob_proc"
        proc = getattr(self, attr)
        if proc is None or proc.poll() is not None:
            self._reset_proc(attr)
            proc = subprocess.Popen(
                ["git", "--literal-pathspecs", "-C", str(self.git_top), "cat-file", mode_flag],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
            setattr(self, attr, proc)
        return proc

    @staticmethod
    def _read_exact(stream, n: int, spec: str) -> bytes:
        chunks: list[bytes] = []
        rem = n
        while rem > 0:
            chunk = stream.read(rem)
            if not chunk:
                raise ValueError(f"truncated git cat-file --batch stream for {spec!r}")
            chunks.append(chunk)
            rem -= len(chunk)
        return b"".join(chunks)

    def check(self, spec: str) -> tuple[str, str, int] | None:
        payload = self._guard_spec(spec)
        try:
            proc = self._ensure_proc("--batch-check")
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(payload)
            proc.stdin.flush()
            line = proc.stdout.readline().rstrip(b"\r\n")
        except (OSError, BrokenPipeError):
            self._reset_proc("_check_proc")
            raise
        if not line or line.endswith(b" missing") or line.endswith(b" ambiguous"):
            return None
        parts = line.rsplit(b" ", 2)
        if len(parts) != 3 or not parts[2].isdigit():
            self._reset_proc("_check_proc")
            return None
        return (
            parts[0].decode("ascii", "replace"),
            parts[1].decode("ascii", "replace"),
            int(parts[2]),
        )

    def read_blob(self, spec: str) -> bytes | None:
        payload = self._guard_spec(spec)
        try:
            proc = self._ensure_proc("--batch")
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(payload)
            proc.stdin.flush()
            header = proc.stdout.readline().rstrip(b"\r\n")
            if not header or header.endswith(b" missing") or header.endswith(b" ambiguous"):
                return None
            parts = header.rsplit(b" ", 2)
            if len(parts) != 3 or not parts[2].isdigit():
                self._reset_proc("_blob_proc")
                raise ValueError(f"malformed git cat-file --batch header for {spec!r}")
            size = int(parts[2])
            data = self._read_exact(proc.stdout, size, spec)
            delim = self._read_exact(proc.stdout, 1, spec)
            if delim != b"\n":
                self._reset_proc("_blob_proc")
                raise ValueError(f"desynchronized git cat-file --batch delimiter for {spec!r}")
            if parts[1] != b"blob":
                return None
            return data
        except (OSError, BrokenPipeError, ValueError):
            self._reset_proc("_blob_proc")
            raise

    def tree_entry_mode(self, rev_ref: str, git_rel: str) -> str | None:
        """Return 6-char Git tree entry mode (e.g. '100644', '120000') for git_rel at rev_ref, or None."""
        if (
            not isinstance(rev_ref, str)
            or not rev_ref
            or rev_ref.startswith("-")
            or any(ch in rev_ref for ch in ("\n", "\r", "\x00"))
        ):
            raise ValueError(f"unsafe git revision ref refused: {rev_ref!r}")
        if (
            not isinstance(git_rel, str)
            or not git_rel
            or git_rel.startswith(":")
            or any(ch in git_rel for ch in ("\n", "\r", "\x00"))
        ):
            raise ValueError(f"unsafe git relative path refused: {git_rel!r}")
        proc = subprocess.run(
            ["git", "--literal-pathspecs", "-C", str(self.git_top), "ls-tree", "-z", rev_ref, "--", git_rel],
            capture_output=True,
        )
        if proc.returncode != 0 or not proc.stdout:
            return None
        target_b = git_rel.encode("utf-8")
        for record in proc.stdout.split(b"\0"):
            if not record or b"\t" not in record:
                continue
            meta_b, path_b = record.split(b"\t", 1)
            if path_b == target_b:
                meta_fields = meta_b.decode("ascii", "replace").split(" ")
                return meta_fields[0] if meta_fields else None
        return None

    def close(self) -> None:
        self._reset_proc("_check_proc")
        self._reset_proc("_blob_proc")

    def __enter__(self) -> GitCatFileBatch:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass
