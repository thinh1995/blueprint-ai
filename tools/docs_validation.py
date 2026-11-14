"""Shared, portable Markdown validation for repository and installed docs."""

import posixpath
import re
import subprocess
import sys
import urllib.parse
from collections.abc import Callable
from pathlib import Path, PurePosixPath

sys.dont_write_bytecode = True

MINI_SPEC_FILE = "1. Mini Spec.md"
NUMBERED_SPEC_FILES = {
    "1. Product Spec.md",
    "2. Tech Spec.md",
    "3. QA Spec.md",
    "4. Tasks.md",
}
SPEC_PACK_FILES = NUMBERED_SPEC_FILES | {MINI_SPEC_FILE}
VALID_SPEC_STATUSES = {"draft", "approved", "example", "superseded", "archived"}

APPROVAL_FIELDS = (
    "approved_by",
    "approved_at",
    "approval_evidence",
    "source_revision",
)
GOVERNANCE_KEYS = {"status", "superseded_by", "supersedes", *APPROVAL_FIELDS}
FORBIDDEN_APPROVED_PLACEHOLDERS = {
    "draft",
    "todo",
    "tbd",
    "pending",
    "n/a",
    "none",
    "-",
}
READINESS_SECTIONS = (
    "Open decisions",
    "Risks and open decisions",
    "Pre-implementation readiness checklist",
)
TASK_COLUMNS = (
    "task id",
    "status",
    "[p]",
    "depends on",
    "related ac",
    "owned paths",
    "summary",
    "verification",
)
VALID_TASK_STATUSES = {"todo", "in-progress", "done", "blocked"}
TRIAGE_SECTION_HEADING = "Brownfield security and tech-debt triage"
TRIAGE_COLUMNS = (
    "id",
    "category",
    "severity",
    "evidence",
    "risk / debt summary",
    "remediation route",
    "target spec or evidence",
    "status",
)
VALID_TRIAGE_STATUSES = {"open", "in progress", "mitigated", "accepted risk"}
MAX_SUPERSEDED_HOPS = 16
FORBIDDEN_SUPERSEDED_TERMINAL_STATUSES = {"archived", "template", "skipped", "example", ""}
FORBIDDEN_URI_SCHEMES = ("file:", "javascript:", "data:", "vbscript:", "obsidian:")
ALLOWED_EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:")
SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
SEQ_PREFIX_RE = re.compile(r"^(\d{3})-")
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_markdown(path: Path) -> str:
    """Read UTF-8 (with optional BOM) Markdown and normalize CRLF/CR line endings."""
    return path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")


# Backward-compatible alias for existing callers (e.g. validate-template-docs.py).
read = read_markdown


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


def _iter_frontmatter_entries(markdown_text: str) -> list[tuple[str, str]]:
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
    return {key: _strip_yaml_scalar(raw_val) for key, raw_val in _iter_frontmatter_entries(markdown_text)}


def _validate_governance_frontmatter(rel_path: Path | str, markdown_text: str) -> None:
    """Validate duplicate-free, scalar-only, properly-quoted syntax on governance frontmatter keys."""
    seen: set[str] = set()
    for key, raw_val in _iter_frontmatter_entries(markdown_text):
        if key not in GOVERNANCE_KEYS:
            continue
        require(key not in seen, f"{rel_path}: duplicate frontmatter key '{key}'")
        seen.add(key)

        val = raw_val.strip()
        if not val or val.startswith("#"):
            continue

        if val[0] in {'"', "'"}:
            quote = val[0]
            idx = 1
            closed = False
            allow_quote_escape = key in {"approved_by", "approved_at", "approval_evidence"}
            while idx < len(val):
                ch = val[idx]
                if ch == "\\":
                    if quote == '"' and allow_quote_escape and idx + 1 < len(val) and val[idx + 1] == '"':
                        idx += 2
                        continue
                    raise ValueError(f"{rel_path}: frontmatter '{key}' cannot contain raw backslash '\\'")
                if quote == "'" and ch == "'" and idx + 1 < len(val) and val[idx + 1] == "'" and allow_quote_escape:
                    idx += 2
                    continue
                if ch == quote:
                    trailing = val[idx + 1 :].strip()
                    require(
                        not trailing or trailing.startswith("#"),
                        f"{rel_path}: frontmatter '{key}' has unescaped interior quote or trailing characters",
                    )
                    closed = True
                    break
                idx += 1
            require(closed, f"{rel_path}: frontmatter '{key}' has unclosed quote")
        else:
            unquoted_val = re.split(r"[ \t]+#", val, maxsplit=1)[0].strip()
            require(
                unquoted_val[:1] not in {"[", "{", "|", ">", "!", "&", "*"},
                f"{rel_path}: frontmatter '{key}' must be a plain or quoted scalar (got '{unquoted_val}')",
            )
            require(
                not any(ch in unquoted_val for ch in ('"', "'", "\\")),
                f"{rel_path}: frontmatter '{key}' contains unescaped quote or backslash",
            )


def extract_mermaid_blocks(markdown_text: str, rel_label: str = "<markdown>") -> list[tuple[int, str]]:
    """Extract (start_line_1based, diagram_body) via a fence-length-aware state machine."""
    text = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    blocks: list[tuple[int, str]] = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    is_mermaid = False
    start_line = 0
    current_lines: list[str] = []

    for line_no, line in enumerate(text.split("\n"), start=1):
        if not in_fence:
            m_bt = re.match(r"^[ \t]*(`{3,})([^`]*)$", line)
            m_td = None if m_bt else re.match(r"^[ \t]*(~{3,})(.*)$", line)
            m = m_bt or m_td
            if m:
                in_fence = True
                fence_char = m.group(1)[0]
                fence_len = len(m.group(1))
                info = m.group(2).strip()
                info_token = info.split()[0].lower() if info else ""
                if info_token == "mermaid":
                    is_mermaid = True
                    start_line = line_no
                    current_lines = []
                else:
                    is_mermaid = False
        else:
            if re.match(rf"^[ \t]*{re.escape(fence_char)}{{{fence_len},}}[ \t]*$", line):
                if is_mermaid:
                    blocks.append((start_line, "\n".join(current_lines)))
                in_fence = False
                fence_char = ""
                fence_len = 0
                is_mermaid = False
                current_lines = []
            elif is_mermaid:
                current_lines.append(line)

    require(not (in_fence and is_mermaid), f"{rel_label}: malformed or unclosed Mermaid fence")
    return blocks


def _iter_h2_sections(markdown_text: str, heading: str) -> list[str]:
    target = heading.strip().lower()
    sections: list[str] = []
    current: list[str] | None = None
    for line in markdown_text.split("\n"):
        h_match = re.match(r"^(#{1,2})[ \t]+(.*?)[ \t]*$", line)
        if h_match:
            if current is not None:
                sections.append("\n".join(current))
                current = None
            if h_match.group(1) == "##" and h_match.group(2).strip().lower() == target:
                current = []
            continue
        if current is not None:
            current.append(line)
    if current is not None:
        sections.append("\n".join(current))
    return sections


def _split_table_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if not (stripped.startswith("|") and stripped.endswith("|") and not stripped.endswith(r"\|")):
        return None
    parts = re.split(r"(?<!\\)\|", stripped)[1:-1]
    if not parts:
        return None
    return [cell.replace(r"\|", "|").strip() for cell in parts]


def _is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(bool(re.fullmatch(r":?-{3,}:?", cell.replace(" ", ""))) for cell in cells)


def _extract_section_table_rows(
    rel_path: Path | str,
    raw_text: str,
    section_heading: str,
    required_columns: tuple[str, ...],
    require_table: bool,
    header_normalizer: Callable[[str], str] | None = None,
) -> list[dict[str, str]] | None:
    norm_fn = header_normalizer or (lambda h: re.sub(r"\s+", " ", h.strip().lower()))
    fenced_stripped = strip_fenced_code(raw_text)
    sections = _iter_h2_sections(fenced_stripped, section_heading)
    tables: list[tuple[list[str], list[dict[str, str]]]] = []
    for section_body in sections:
        lines = section_body.split("\n")
        idx = 0
        while idx < len(lines):
            header_cells = _split_table_row(lines[idx])
            if header_cells is not None and idx + 1 < len(lines):
                sep_cells = _split_table_row(lines[idx + 1])
                if (
                    sep_cells is not None
                    and len(sep_cells) == len(header_cells)
                    and _is_separator_row(sep_cells)
                ):
                    headers = [norm_fn(h) for h in header_cells]
                    rows: list[dict[str, str]] = []
                    idx += 2
                    while idx < len(lines):
                        row_cells = _split_table_row(lines[idx])
                        if row_cells is None:
                            break
                        require(
                            len(row_cells) == len(headers),
                            f"{rel_path}: malformed table row in '## {section_heading}' "
                            f"(expected {len(headers)} columns, got {len(row_cells)})",
                        )
                        rows.append(dict(zip(headers, row_cells)))
                        idx += 1
                    tables.append((headers, rows))
                    continue
            idx += 1

    if not tables:
        require(not require_table, f"{rel_path}: missing Markdown table in '## {section_heading}'")
        return None

    matched_rows: list[dict[str, str]] = []
    found_matching_table = False
    for headers, rows in tables:
        header_set = set(headers)
        if all(col in header_set for col in required_columns):
            found_matching_table = True
            matched_rows.extend(rows)

    if not found_matching_table:
        first_headers = set(tables[0][0])
        missing_cols = [col for col in required_columns if col not in first_headers]
        raise ValueError(
            f"{rel_path}: table in '## {section_heading}' is missing required column(s): "
            f"{', '.join(missing_cols)}"
        )
    return matched_rows


def _extract_acs_from_rows(rows: list[dict[str, str]] | None, column: str) -> set[str]:
    if not rows:
        return set()
    acs: set[str] = set()
    for row in rows:
        acs.update(re.findall(r"\bAC-\d+\b", row.get(column, "")))
    return acs


def _parse_markdown_link_destination(raw_inside: str) -> str:
    inside = raw_inside.strip()
    if inside.startswith("<"):
        gt = inside.find(">")
        if gt != -1:
            return inside[1:gt].strip()
    m_title = re.match(r'^(\S+?)(?:\s+(?:"[^"]*"|\'[^\']*\'|\([^)]*\)))?$', inside)
    if m_title:
        return m_title.group(1).strip()
    return inside


def _walk_lexical_no_symlink(
    root_resolved: Path,
    start_dir: Path,
    rel_target: str,
    escape_msg: str,
    symlink_msg: str,
    err_prefix: str,
) -> Path:
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


def _ensure_within_root_no_symlink(root_resolved: Path, start_dir: Path, rel_target: str, err_prefix: str) -> Path:
    return _walk_lexical_no_symlink(
        root_resolved,
        start_dir,
        rel_target,
        escape_msg=f"{err_prefix}: Markdown link target escapes project root {rel_target}",
        symlink_msg=f"{err_prefix}: symlinked link target refused {rel_target}",
        err_prefix=err_prefix,
    )


def validate_links(root: Path, docs_root: Path, files: list[Path]) -> None:
    root_resolved = root.resolve()
    docs_resolved = docs_root.resolve()
    relative_paths = {path.resolve().relative_to(docs_resolved).with_suffix("").as_posix() for path in files}
    stems: dict[str, list[Path]] = {}
    for path in files:
        stems.setdefault(path.stem, []).append(path)

    all_doc_assets: dict[str, Path] = {}
    assets_by_name: dict[str, list[Path]] = {}
    if docs_resolved.is_dir():
        for asset in sorted(docs_resolved.rglob("*")):
            if asset.is_symlink() or not asset.is_file():
                continue
            rel_posix = asset.relative_to(docs_resolved).as_posix()
            if "internal" in asset.relative_to(docs_resolved).parts:
                continue
            all_doc_assets[rel_posix] = asset
            assets_by_name.setdefault(asset.name, []).append(asset)

    wiki = re.compile(r"(!?)\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    markdown = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")

    for path in files:
        rel_doc_label = path.relative_to(root)
        path_resolved = path.resolve()
        content = strip_code(read_markdown(path))

        for match in wiki.finditer(content):
            is_embed = match.group(1) == "!"
            raw_target = match.group(2).strip()
            unquoted = urllib.parse.unquote(raw_target).strip().replace("\\", "/")
            double_unquoted = urllib.parse.unquote(unquoted).strip().lower()
            for bad_scheme in FORBIDDEN_URI_SCHEMES:
                require(
                    not unquoted.lower().startswith(bad_scheme) and not double_unquoted.startswith(bad_scheme),
                    f"{rel_doc_label}: unsupported URI scheme {bad_scheme} in [[{raw_target}]]",
                )
            require(
                not unquoted.startswith("/"),
                f"{rel_doc_label}: link target escapes project root [[{raw_target}]]",
            )
            if ".." in unquoted.split("/"):
                parent_check = (path_resolved.parent / unquoted).resolve()
                docs_check = (docs_resolved / unquoted).resolve()
                require(
                    parent_check.is_relative_to(root_resolved) and docs_check.is_relative_to(root_resolved),
                    f"{rel_doc_label}: link target escapes project root [[{raw_target}]]",
                )

            target_no_md = unquoted[:-3] if unquoted.lower().endswith(".md") else unquoted
            docs_stripped_no_md = (
                target_no_md[len("docs/") :] if target_no_md.startswith("docs/current/") else target_no_md
            )
            parent_rel = posixpath.normpath((path_resolved.parent.relative_to(docs_resolved) / target_no_md).as_posix())
            current_rel = posixpath.normpath(f"current/{target_no_md}")
            if (
                target_no_md in relative_paths
                or docs_stripped_no_md in relative_paths
                or (not parent_rel.startswith("..") and parent_rel in relative_paths)
                or (not current_rel.startswith("..") and current_rel in relative_paths)
            ):
                continue
            if "/" not in target_no_md and len(stems.get(target_no_md, [])) == 1:
                continue

            # Check vault asset files (for ![[diagram.png]] or [[assets/diagram.png]] or [[Note.md]]).
            docs_stripped_asset = unquoted[len("docs/") :] if unquoted.startswith("docs/current/") else unquoted
            parent_asset_rel = posixpath.normpath((path_resolved.parent.relative_to(docs_resolved) / unquoted).as_posix())
            current_asset_rel = posixpath.normpath(f"current/{unquoted}")
            if (
                unquoted in all_doc_assets
                or docs_stripped_asset in all_doc_assets
                or (not parent_asset_rel.startswith("..") and parent_asset_rel in all_doc_assets)
                or (not current_asset_rel.startswith("..") and current_asset_rel in all_doc_assets)
            ):
                continue
            if "/" not in unquoted and len(assets_by_name.get(unquoted, [])) == 1:
                continue

            prefix = "!" if is_embed else ""
            raise ValueError(f"{rel_doc_label}: unresolved or ambiguous link {prefix}[[{raw_target}]]")

        for match in markdown.finditer(content):
            dest = _parse_markdown_link_destination(match.group(1))
            if not dest or dest.startswith("#"):
                continue
            target_before_frag = dest.split("#", 1)[0].strip()
            if not target_before_frag:
                continue

            decoded = urllib.parse.unquote(target_before_frag).strip()
            decoded_twice_lower = urllib.parse.unquote(decoded).strip().lower()
            decoded_lower = decoded.lower()

            for bad_scheme in FORBIDDEN_URI_SCHEMES:
                require(
                    not decoded_lower.startswith(bad_scheme) and not decoded_twice_lower.startswith(bad_scheme),
                    f"{rel_doc_label}: unsupported Markdown URI scheme {bad_scheme}",
                )
            if decoded_lower.startswith(ALLOWED_EXTERNAL_SCHEMES):
                continue
            require(
                not SCHEME_RE.match(decoded),
                f"{rel_doc_label}: unsupported Markdown URI scheme in {target_before_frag}",
            )
            require(
                "\\" not in decoded and not decoded.startswith("/"),
                f"{rel_doc_label}: Markdown link target escapes project root {target_before_frag}",
            )

            resolved = _ensure_within_root_no_symlink(
                root_resolved,
                path_resolved.parent,
                decoded,
                str(rel_doc_label),
            )
            require(resolved.is_file(), f"{rel_doc_label}: missing Markdown link target {target_before_frag}")


def _strip_mermaid_preamble(rel_label: Path | str, diagram: str) -> str:
    cleaned = diagram.lstrip()
    if cleaned.startswith("---"):
        fm_match = re.match(r"^---[ \t]*\n.*?\n---[ \t]*(?:\n|$)", cleaned, flags=re.S)
        if fm_match:
            cleaned = cleaned[fm_match.end() :]
    while True:
        cleaned = cleaned.lstrip()
        if cleaned.startswith("%%{"):
            m_dir = re.match(r"^%%\{.*?\}%%[ \t]*(?:\n|$)", cleaned, flags=re.S)
            require(m_dir is not None, f"{rel_label}: unclosed Mermaid directive %%{{...}}%%")
            assert m_dir is not None
            cleaned = cleaned[m_dir.end() :]
            continue
        if cleaned.startswith("%%"):
            m_cmt = re.match(r"^%%[^\n]*(?:\n|$)", cleaned)
            cleaned = cleaned[m_cmt.end() :] if m_cmt else ""
            continue
        break
    return cleaned


def validate_mermaid(root: Path, files: list[Path]) -> None:
    for path in files:
        rel_label = path.relative_to(root)
        blocks = extract_mermaid_blocks(read_markdown(path), str(rel_label))
        for _line_no, diagram in blocks:
            require(bool(diagram.strip()), f"{rel_label}: empty Mermaid diagram")
            cleaned = _strip_mermaid_preamble(rel_label, diagram)
            require(bool(cleaned.strip()), f"{rel_label}: empty Mermaid diagram")
            require(
                bool(re.match(r"[A-Za-z][A-Za-z0-9_-]*", cleaned)),
                f"{rel_label}: Mermaid diagram has no type",
            )


def _parse_owned_paths(rel_path: Path | str, task_id: str, cell: str) -> tuple[list[PurePosixPath], list[str]]:
    paths: list[PurePosixPath] = []
    raw_tokens: list[str] = []
    unwrapped = strip_outer_backticks(cell)
    for raw_item in unwrapped.split(","):
        cleaned = strip_outer_backticks(raw_item.strip())
        if not cleaned:
            continue
        require(
            not any(ch in cleaned for ch in ("*", "?", "[")),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' cannot contain glob wildcards",
        )
        require(
            "\\" not in cleaned
            and "`" not in cleaned
            and not any(ord(ch) < 32 for ch in cleaned),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' contains invalid path characters",
        )
        require(
            not cleaned.startswith("/") and not cleaned.startswith("~"),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' must be relative to project root",
        )
        trimmed = cleaned.rstrip("/")
        raw_segments = trimmed.split("/") if trimmed else [""]
        require(
            not any(seg in {"", ".", ".."} for seg in raw_segments),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' contains invalid '.' or '..' segments",
        )
        paths.append(PurePosixPath(trimmed))
        raw_tokens.append(cleaned)

    require(bool(paths), f"{rel_path}: task {task_id} must declare at least one Owned path")
    return paths, raw_tokens


def parse_execution_tasks(
    rel_path: Path | str,
    raw_text: str,
    require_table: bool = True,
) -> list[dict[str, object]] | None:
    """Parse and validate '## Execution tasks' table rows with cycle and [P] overlap checks."""
    rows = _extract_section_table_rows(
        rel_path,
        raw_text,
        "Execution tasks",
        TASK_COLUMNS,
        require_table=require_table,
    )
    if rows is None:
        return None
    if require_table:
        require(
            bool(rows),
            f"{rel_path}: '## Execution tasks' must define at least one task row",
        )
    if not rows:
        return []

    task_order: list[str] = []
    seen_ids: set[str] = set()
    raw_deps: dict[str, list[str]] = {}
    parallel_flags: dict[str, str] = {}
    owned_paths_map: dict[str, list[PurePosixPath]] = {}
    parsed_tasks: list[dict[str, object]] = []

    for row in rows:
        tid = strip_outer_backticks(row["task id"]).strip()
        require(
            bool(re.fullmatch(r"T-\d+", tid)),
            f"{rel_path}: invalid Task ID '{tid}' (expected T-xx)",
        )
        require(tid not in seen_ids, f"{rel_path}: duplicate Task ID '{tid}'")
        seen_ids.add(tid)
        task_order.append(tid)

        status_val = strip_outer_backticks(row["status"]).strip().lower()
        require(
            status_val in VALID_TASK_STATUSES,
            f"{rel_path}: task {tid} has invalid Status '{row['status']}' "
            f"(expected one of: {', '.join(sorted(VALID_TASK_STATUSES))})",
        )

        p_val = strip_outer_backticks(row["[p]"]).strip().lower()
        require(
            p_val in {"yes", "no"},
            f"{rel_path}: task {tid} has invalid [P] value '{row['[p]']}' (expected yes or no)",
        )
        parallel_flags[tid] = p_val

        dep_cell = row["depends on"].replace("`", "").strip()
        if dep_cell in {"", "-"}:
            deps: list[str] = []
        else:
            deps = [tok for tok in re.split(r"[,\s]+", dep_cell) if tok]
            for dep in deps:
                require(
                    bool(re.fullmatch(r"T-\d+", dep)),
                    f"{rel_path}: task {tid} has invalid Depends on token '{dep}' (expected '-' or T-xx)",
                )
                require(dep != tid, f"{rel_path}: task {tid} cannot depend on itself")
        raw_deps[tid] = deps

        ac_cell_clean = strip_outer_backticks(row["related ac"]).strip()
        related_ac = list(dict.fromkeys(re.findall(r"\bAC-\d+\b", row["related ac"])))
        if not related_ac:
            require(
                ac_cell_clean == "-",
                f"{rel_path}: task {tid} Related AC must reference AC-xx or '-' (got '{row['related ac']}')",
            )

        posix_paths, raw_path_tokens = _parse_owned_paths(rel_path, tid, row["owned paths"])
        owned_paths_map[tid] = posix_paths

        summary = row["summary"].strip()
        require(bool(summary), f"{rel_path}: task {tid} Summary must not be empty")

        verification = strip_outer_backticks(row["verification"]).strip()
        require(bool(verification), f"{rel_path}: task {tid} Verification must not be empty")

        parsed_tasks.append(
            {
                "task_id": tid,
                "status": status_val,
                "parallel": p_val == "yes",
                "depends_on": deps,
                "related_ac": related_ac,
                "owned_paths": raw_path_tokens,
                "owned_paths_posix": [p.as_posix() for p in posix_paths],
                "summary": summary,
                "verification": verification,
            }
        )

    for tid in task_order:
        for dep in raw_deps[tid]:
            require(
                dep in seen_ids,
                f"{rel_path}: task {tid} depends on unknown Task ID '{dep}'",
            )

    visit_state: dict[str, int] = {}
    stack: list[str] = []

    def dfs(node: str) -> None:
        visit_state[node] = 1
        stack.append(node)
        for nxt in raw_deps[node]:
            nxt_state = visit_state.get(nxt, 0)
            if nxt_state == 1:
                cycle_idx = stack.index(nxt)
                cycle_str = " -> ".join(stack[cycle_idx:] + [nxt])
                raise ValueError(f"{rel_path}: task dependency cycle detected: {cycle_str}")
            if nxt_state == 0:
                dfs(nxt)
        stack.pop()
        visit_state[node] = 2

    for tid in task_order:
        if visit_state.get(tid, 0) == 0:
            dfs(tid)

    def reaches(start: str, target: str) -> bool:
        visited: set[str] = set()
        pending = list(raw_deps[start])
        while pending:
            curr = pending.pop()
            if curr == target:
                return True
            if curr not in visited:
                visited.add(curr)
                pending.extend(raw_deps[curr])
        return False

    for idx_a, tid_a in enumerate(task_order):
        if parallel_flags[tid_a] != "yes":
            continue
        for tid_b in task_order[idx_a + 1 :]:
            if parallel_flags[tid_b] != "yes":
                continue
            if reaches(tid_a, tid_b) or reaches(tid_b, tid_a):
                continue
            for pa in owned_paths_map[tid_a]:
                for pb in owned_paths_map[tid_b]:
                    if pa == pb or pa.is_relative_to(pb) or pb.is_relative_to(pa):
                        raise ValueError(
                            f"{rel_path}: parallel [P] tasks {tid_a} ('{pa.as_posix()}') and "
                            f"{tid_b} ('{pb.as_posix()}') have overlapping Owned paths"
                        )

    return parsed_tasks


def _normalize_ac_contract(rel_path: Path | str, raw_text: str) -> list[tuple[tuple[str, str], ...]]:
    rows = _extract_section_table_rows(
        rel_path,
        raw_text,
        "Acceptance criteria",
        ("id",),
        require_table=False,
    )
    if not rows:
        return []
    normalized: list[tuple[tuple[str, str], ...]] = []
    for row in rows:
        normalized.append(
            tuple(sorted((k, re.sub(r"\s+", " ", v.strip())) for k, v in row.items()))
        )
    return normalized


def _normalize_task_contract(rel_path: Path | str, raw_text: str) -> list[tuple[str, tuple[str, ...], str]]:
    tasks = parse_execution_tasks(rel_path, raw_text, require_table=False)
    if not tasks:
        return []
    out: list[tuple[str, tuple[str, ...], str]] = []
    for t in tasks:
        out.append(
            (
                str(t["task_id"]),
                tuple(t["owned_paths_posix"]),  # type: ignore[arg-type]
                re.sub(r"\s+", " ", str(t["verification"]).strip()),
            )
        )
    return out


def _find_earliest_approved_baseline(
    root: Path,
    posix_spec_path: str,
    source_revision: str,
) -> str | None:
    """Return historical file text at the earliest Git commit where status=approved & source_revision matches."""
    commit_candidates: list[str] = []
    for log_cmd in (
        ["git", "log", "--format=%H", "--reverse", "-S", source_revision, "--", posix_spec_path],
        ["git", "log", "--format=%H", "--reverse", "--", posix_spec_path],
    ):
        proc = subprocess.run(log_cmd, cwd=root, capture_output=True, text=True)
        if proc.returncode == 0 and proc.stdout.strip():
            for sha in proc.stdout.splitlines():
                sha_clean = sha.strip()
                if sha_clean and sha_clean not in commit_candidates:
                    commit_candidates.append(sha_clean)
        if commit_candidates:
            for sha in commit_candidates:
                show_proc = subprocess.run(
                    ["git", "show", f"{sha}:{posix_spec_path}"],
                    cwd=root,
                    capture_output=True,
                    text=True,
                )
                if show_proc.returncode != 0:
                    continue
                hist_raw = show_proc.stdout.replace("\r\n", "\n").replace("\r", "\n")
                hist_fm = parse_frontmatter(hist_raw)
                if (
                    hist_fm.get("status", "").strip().lower() == "approved"
                    and hist_fm.get("source_revision", "").strip() == source_revision
                ):
                    return hist_raw
            commit_candidates.clear()
    return None


def _find_any_approved_history(
    root: Path,
    posix_spec_path: str,
) -> tuple[str, dict[str, str]] | None:
    """Return (raw_text, frontmatter) of the earliest historical status=approved commit, if any."""
    if not (root / ".git").exists():
        return None
    proc = subprocess.run(
        ["git", "log", "--format=%H", "--reverse", "--", posix_spec_path],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    for sha in proc.stdout.splitlines():
        sha_clean = sha.strip()
        if not sha_clean:
            continue
        show_proc = subprocess.run(
            ["git", "show", f"{sha_clean}:{posix_spec_path}"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        if show_proc.returncode != 0:
            continue
        hist_raw = show_proc.stdout.replace("\r\n", "\n").replace("\r", "\n")
        hist_fm = parse_frontmatter(hist_raw)
        if hist_fm.get("status", "").strip().lower() == "approved":
            return hist_raw, hist_fm
    return None


def _verify_source_revision_and_baseline(
    root: Path,
    spec_path: Path,
    raw: str,
    fm: dict[str, str],
    strict: bool,
    status_label: str,
    require_git_baseline: bool = False,
) -> list[str]:
    warnings: list[str] = []
    rel_path = spec_path.relative_to(root)
    src_rev = fm.get("source_revision", "").strip()
    require(
        bool(src_rev),
        f"{rel_path}: status: {status_label} requires non-empty frontmatter 'source_revision'",
    )
    require(
        src_rev.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
        f"{rel_path}: status: {status_label} forbids placeholder value '{src_rev}' in 'source_revision'",
    )
    require(
        not re.fullmatch(r"0+", src_rev),
        f"{rel_path}: status: {status_label} forbids all-zero source_revision '{src_rev}'",
    )

    if not HEX40_RE.fullmatch(src_rev):
        if strict:
            raise ValueError(
                f"{rel_path}: status: {status_label} requires 40-char lowercase hex Git SHA in source_revision (got '{src_rev}')"
            )
        warnings.append(
            f"{rel_path}: legacy non-40-hex source_revision '{src_rev}' on {status_label} spec (enforced as error with --strict)"
        )
        return warnings

    if not (root / ".git").exists():
        return warnings

    try:
        cat_proc = subprocess.run(
            ["git", "cat-file", "-e", f"{src_rev}^{{commit}}"],
            cwd=root,
            capture_output=True,
            text=True,
        )
    except OSError:
        if strict:
            raise ValueError(f"{rel_path}: git binary unavailable to verify source_revision '{src_rev}'")
        warnings.append(f"{rel_path}: git binary unavailable to verify source_revision '{src_rev}'")
        return warnings

    if cat_proc.returncode != 0:
        shallow_proc = subprocess.run(
            ["git", "rev-parse", "--is-shallow-repository"],
            cwd=root,
            capture_output=True,
            text=True,
        )
        is_shallow = shallow_proc.returncode == 0 and shallow_proc.stdout.strip() == "true"
        if is_shallow and not strict:
            warnings.append(f"{rel_path}: source_revision '{src_rev}' not present in shallow Git clone")
            return warnings
        raise ValueError(
            f"{rel_path}: source_revision '{src_rev}' is not a valid commit object in Git history"
        )

    posix_spec_path = rel_path.as_posix()
    baseline_raw = _find_earliest_approved_baseline(root, posix_spec_path, src_rev)
    if baseline_raw is None:
        require(
            not require_git_baseline,
            f"{rel_path}: status: {status_label} altered historical approved 'source_revision' ('{src_rev}')",
        )
        return warnings

    if spec_path.name in {"1. Product Spec.md", MINI_SPEC_FILE}:
        hist_ac = _normalize_ac_contract(rel_path, baseline_raw)
        curr_ac = _normalize_ac_contract(rel_path, raw)
        require(
            hist_ac == curr_ac,
            f"{rel_path}: post-approval tampering detected in '## Acceptance criteria' without refreshing "
            "source_revision and approved_at",
        )

    if spec_path.name in {"4. Tasks.md", MINI_SPEC_FILE}:
        hist_tasks = _normalize_task_contract(rel_path, baseline_raw)
        curr_tasks = _normalize_task_contract(rel_path, raw)
        require(
            hist_tasks == curr_tasks,
            f"{rel_path}: post-approval tampering detected in '## Execution tasks' (Owned paths / Verification) "
            "without refreshing source_revision and approved_at",
        )

    return warnings


def _check_approved_source_revision(
    root: Path,
    spec_path: Path,
    raw: str,
    fm: dict[str, str],
    strict: bool,
) -> list[str]:
    if spec_path.name not in SPEC_PACK_FILES:
        return []
    if fm.get("status", "").strip().lower() != "approved":
        return []
    return _verify_source_revision_and_baseline(
        root, spec_path, raw, fm, strict=strict, status_label="approved"
    )


def _is_in_docs_current(root: Path, path: Path) -> bool:
    root_resolved = root.resolve()
    current_dir = root_resolved / "docs" / "current"
    if not current_dir.exists() or current_dir.is_symlink() or (root_resolved / "docs").is_symlink():
        return False
    try:
        return path.resolve().is_relative_to(current_dir.resolve())
    except OSError:
        return False


def _validate_no_leaked_secrets(rel_path: Path | str, raw_text: str) -> None:
    for label, pat in SECRET_PATTERNS:
        match = pat.search(raw_text)
        require(
            match is None,
            f"{rel_path}: high-confidence secret detected ({label}); redact credentials before committing",
        )
    for uri_match in CREDENTIALED_URI_RE.finditer(raw_text):
        user_part = uri_match.group(1).strip()
        pass_part = uri_match.group(2).strip()
        pair = f"{user_part}:{pass_part}".lower()
        if pair in ALLOWED_CREDENTIAL_PLACEHOLDERS:
            continue
        if (user_part.startswith("<") and pass_part.endswith(">")) or "${" in pair or "{{" in pair:
            continue
        raise ValueError(
            f"{rel_path}: high-confidence credentialed URI detected; use placeholder 'user:pass@' or redact"
        )


def _normalize_triage_header(header: str) -> str:
    norm = re.sub(r"\s+", " ", header.strip().lower())
    if norm in {"evidence (`file:line`)", "evidence (file:line)"}:
        return "evidence"
    return norm


def _validate_triage_section(rel_path: Path | str, raw_text: str) -> None:
    if not _iter_h2_sections(strip_fenced_code(raw_text), TRIAGE_SECTION_HEADING):
        return
    matched_rows = (
        _extract_section_table_rows(
            rel_path,
            raw_text,
            TRIAGE_SECTION_HEADING,
            TRIAGE_COLUMNS,
            require_table=True,
            header_normalizer=_normalize_triage_header,
        )
        or []
    )

    seen_sec_ids: set[str] = set()
    for row in matched_rows:
        sec_id = strip_outer_backticks(row["id"]).strip()
        require(
            bool(re.fullmatch(r"SEC-\d+", sec_id)),
            f"{rel_path}: invalid triage ID '{sec_id}' in '## {TRIAGE_SECTION_HEADING}' (expected SEC-xx)",
        )
        require(
            sec_id not in seen_sec_ids,
            f"{rel_path}: duplicate triage ID '{sec_id}' in '## {TRIAGE_SECTION_HEADING}'",
        )
        seen_sec_ids.add(sec_id)

        raw_st = row["status"]
        norm_st = re.sub(r"\s+", " ", strip_outer_backticks(raw_st).strip().lower())
        require(
            norm_st in VALID_TRIAGE_STATUSES,
            f"{rel_path}: triage row {sec_id} has invalid Status '{raw_st}' "
            "(expected one of: Open, In Progress, Mitigated, Accepted Risk)",
        )


def _check_non_empty_uri_path_safety(rel_path: Path | str, field_name: str, val: str) -> None:
    require(
        not any(ord(ch) < 32 or ord(ch) == 127 for ch in val),
        f"{rel_path}: frontmatter '{field_name}' contains control characters",
    )
    require(
        "\\" not in val and "%" not in val,
        f"{rel_path}: frontmatter '{field_name}' forbids '\\' and '%' URL-encoding ('{val}')",
    )
    require(
        not val.startswith("![["),
        f"{rel_path}: frontmatter '{field_name}' forbids Obsidian embed syntax ![[...]]",
    )


def _check_no_uri_scheme(rel_path: Path | str, field_name: str, target_str: str) -> None:
    lower = target_str.lower()
    for bad_scheme in FORBIDDEN_URI_SCHEMES + ALLOWED_EXTERNAL_SCHEMES:
        require(
            not lower.startswith(bad_scheme),
            f"{rel_path}: unsupported URI scheme in '{field_name}' ('{target_str}')",
        )
    require(
        not SCHEME_RE.match(target_str),
        f"{rel_path}: unsupported URI scheme in '{field_name}' ('{target_str}')",
    )


def _resolve_docs_current_root(root_resolved: Path, rel_path: Path | str) -> Path:
    return _walk_lexical_no_symlink(
        root_resolved,
        root_resolved,
        "docs/current",
        escape_msg=f"{rel_path}: docs/current escapes project root",
        symlink_msg=f"{rel_path}: symlinked docs/current refused",
        err_prefix=str(rel_path),
    )


def _is_product_feature_member(current_root: Path, resolved_path: Path) -> bool:
    rel_parts = resolved_path.relative_to(current_root).parts
    return len(rel_parts) >= 3 and rel_parts[0] == "05 - Product Features"


def _resolve_superseded_by_single(
    root_resolved: Path,
    source_path: Path,
    raw_superseded_by: str,
) -> tuple[Path, tuple[str, str]]:
    rel_path = source_path.relative_to(root_resolved)
    val = raw_superseded_by.strip()
    require(
        bool(val),
        f"{rel_path}: status: superseded requires non-empty frontmatter 'superseded_by'",
    )
    require(
        val.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
        f"{rel_path}: status: superseded forbids placeholder value '{val}' in 'superseded_by'",
    )
    _check_non_empty_uri_path_safety(rel_path, "superseded_by", val)

    current_root = _resolve_docs_current_root(root_resolved, rel_path)

    def walk_target(rel_candidate: str) -> Path:
        return _walk_lexical_no_symlink(
            root_resolved,
            current_root,
            rel_candidate,
            escape_msg=f"{rel_path}: 'superseded_by' target escapes docs/current ('{val}')",
            symlink_msg=f"{rel_path}: symlinked 'superseded_by' target refused ('{val}')",
            err_prefix=str(rel_path),
        )

    is_wikilink = val.startswith("[[") and val.endswith("]]")
    had_slash = True
    if is_wikilink:
        inner = val[2:-2]
        require(
            "[" not in inner and "]" not in inner,
            f"{rel_path}: malformed wikilink in 'superseded_by' ('{val}')",
        )
        # Exact order: #heading -> |alias -> optional .md
        target_core = inner.split("#", 1)[0].split("|", 1)[0].strip()
        if target_core.lower().endswith(".md"):
            target_core = target_core[:-3].strip()
        require(bool(target_core), f"{rel_path}: empty wikilink target in 'superseded_by'")
        require(
            not any(ch in target_core for ch in ("*", "?", "[", "]")),
            f"{rel_path}: 'superseded_by' forbids glob wildcards ('{val}')",
        )
        _check_no_uri_scheme(rel_path, "superseded_by", target_core)
        require(
            not target_core.startswith("/") and not target_core.startswith("~"),
            f"{rel_path}: 'superseded_by' target escapes docs/current ('{val}')",
        )
        segments = target_core.split("/")
        require(
            not any(seg in {"", ".", ".."} for seg in segments),
            f"{rel_path}: 'superseded_by' forbids '.' or '..' traversal ('{val}')",
        )
        had_slash = "/" in target_core
        rel_inside = (
            target_core[len("docs/current/") :]
            if target_core.startswith("docs/current/")
            else target_core
        )
        require(bool(rel_inside), f"{rel_path}: invalid 'superseded_by' target ('{val}')")
        direct_resolved = walk_target(f"{rel_inside}.md")
        if direct_resolved.is_file():
            resolved = direct_resolved
        elif not had_slash:
            matches = [
                p
                for p in sorted(current_root.rglob("*.md"))
                if not p.is_symlink() and p.stem == rel_inside
            ]
            require(
                len(matches) == 1,
                f"{rel_path}: unresolved or ambiguous wikilink in 'superseded_by' ('{val}')",
            )
            resolved = walk_target(matches[0].relative_to(current_root).as_posix())
        else:
            raise ValueError(f"{rel_path}: missing 'superseded_by' target '{val}'")

        require(
            had_slash or resolved.name not in SPEC_PACK_FILES,
            f"{rel_path}: slash-less stem-only wikilink is forbidden when targeting feature spec '{resolved.name}'",
        )
    else:
        require(
            "#" not in val and "|" not in val,
            f"{rel_path}: plain path in 'superseded_by' cannot contain '#' or '|' ('{val}')",
        )
        require(
            not any(ch in val for ch in ("*", "?", "[", "]")),
            f"{rel_path}: 'superseded_by' forbids glob wildcards or partial brackets ('{val}')",
        )
        _check_no_uri_scheme(rel_path, "superseded_by", val)
        require(
            not val.startswith("/") and not val.startswith("~"),
            f"{rel_path}: 'superseded_by' target must be relative ('{val}')",
        )
        segments = val.split("/")
        require(
            not any(seg in {"", ".", ".."} for seg in segments),
            f"{rel_path}: 'superseded_by' forbids '.' or '..' traversal ('{val}')",
        )
        require(
            val.lower().endswith(".md"),
            f"{rel_path}: plain 'superseded_by' path must end with '.md' ('{val}')",
        )
        rel_md = val[len("docs/current/") :] if val.startswith("docs/current/") else val
        require(bool(rel_md), f"{rel_path}: invalid 'superseded_by' path ('{val}')")
        resolved = walk_target(rel_md)
        require(resolved.is_file(), f"{rel_path}: missing 'superseded_by' target '{val}'")

    require(
        resolved.is_relative_to(current_root),
        f"{rel_path}: 'superseded_by' target must reside inside docs/current ('{val}')",
    )
    src_resolved = source_path.resolve()
    require(resolved != src_resolved, f"{rel_path}: 'superseded_by' cannot reference itself")

    if _is_product_feature_member(current_root, src_resolved):
        require(
            resolved.parent != src_resolved.parent,
            f"{rel_path}: 'superseded_by' cannot target another file in the same feature folder",
        )

    target_rel_parts = resolved.relative_to(current_root).parts
    if target_rel_parts and target_rel_parts[0] == "05 - Product Features":
        require(
            len(target_rel_parts) >= 3 and resolved.name in SPEC_PACK_FILES,
            f"{rel_path}: 'superseded_by' inside '05 - Product Features/' must target a spec file inside a feature folder (got '{resolved.relative_to(current_root).as_posix()}')",
        )
        scope = ("feature", target_rel_parts[1])
    else:
        scope = ("domain", resolved.relative_to(current_root).as_posix())

    return resolved, scope


def _check_archived_spec_history(
    root: Path,
    spec_path: Path,
    fm: dict[str, str],
) -> None:
    if spec_path.name not in SPEC_PACK_FILES:
        return
    rel_path = spec_path.relative_to(root)
    hist = _find_any_approved_history(root, rel_path.as_posix())
    if hist is None:
        return
    for field in ("approved_by", "source_revision"):
        val = fm.get(field, "").strip()
        require(
            bool(val) and val.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
            f"{rel_path}: status: archived on formerly approved spec must preserve non-empty '{field}'",
        )


def _validate_superseded_by(
    root: Path,
    source_path: Path,
    raw: str,
    fm: dict[str, str],
    strict: bool,
) -> tuple[list[str], tuple[str, str]]:
    warnings: list[str] = []
    root_resolved = root.resolve()
    rel_path = source_path.relative_to(root)

    was_formerly_approved = False
    if source_path.name in SPEC_PACK_FILES:
        hist = _find_any_approved_history(root, rel_path.as_posix())
        has_src_rev = bool(fm.get("source_revision", "").strip())
        was_formerly_approved = has_src_rev or (hist is not None)
        if was_formerly_approved:
            for field in APPROVAL_FIELDS:
                val = fm.get(field, "").strip()
                require(
                    bool(val) and val.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
                    f"{rel_path}: status: superseded on formerly approved spec must preserve non-empty '{field}'",
                )
            warnings.extend(
                _verify_source_revision_and_baseline(
                    root,
                    source_path,
                    raw,
                    fm,
                    strict=strict,
                    status_label="superseded",
                    require_git_baseline=(hist is not None),
                )
            )

    first_target, first_scope = _resolve_superseded_by_single(
        root_resolved,
        source_path,
        fm.get("superseded_by", ""),
    )

    src_resolved = source_path.resolve()
    visited_files: set[Path] = {src_resolved}
    current_root = _resolve_docs_current_root(root_resolved, rel_path)
    visited_feature_dirs: set[Path] = set()
    if _is_product_feature_member(current_root, src_resolved):
        visited_feature_dirs.add(src_resolved.parent)

    curr_target = first_target
    terminal_status = ""
    for hop in range(1, MAX_SUPERSEDED_HOPS + 1):
        require(
            curr_target not in visited_files,
            f"{rel_path}: superseded_by cycle detected involving '{curr_target.relative_to(root_resolved).as_posix()}'",
        )
        is_curr_feature_spec = _is_product_feature_member(current_root, curr_target)
        if is_curr_feature_spec:
            require(
                curr_target.parent not in visited_feature_dirs,
                f"{rel_path}: superseded_by cycle detected across feature folder '{curr_target.parent.name}'",
            )

        target_raw = read_markdown(curr_target)
        _validate_governance_frontmatter(curr_target.relative_to(root_resolved), target_raw)
        target_fm = parse_frontmatter(target_raw)
        target_status = target_fm.get("status", "").strip().lower()

        if target_status != "superseded":
            terminal_status = target_status
            break

        require(
            hop < MAX_SUPERSEDED_HOPS,
            f"{rel_path}: superseded_by chain exceeds maximum {MAX_SUPERSEDED_HOPS} hops",
        )
        visited_files.add(curr_target)
        if is_curr_feature_spec:
            visited_feature_dirs.add(curr_target.parent)
        curr_target, _ = _resolve_superseded_by_single(
            root_resolved,
            curr_target,
            target_fm.get("superseded_by", ""),
        )

    require(
        terminal_status not in FORBIDDEN_SUPERSEDED_TERMINAL_STATUSES,
        f"{rel_path}: 'superseded_by' terminal target '{curr_target.relative_to(root_resolved).as_posix()}' "
        f"has inactive or missing status '{terminal_status or 'missing'}'",
    )
    if strict and was_formerly_approved:
        require(
            terminal_status in {"approved", "active"},
            f"{rel_path}: under --strict, formerly approved superseded spec requires terminal successor status "
            f"'approved' or 'active' (got '{terminal_status}' on '{curr_target.relative_to(root_resolved).as_posix()}')",
        )

    return warnings, first_scope


def _validate_supersedes_field(
    root: Path,
    spec_path: Path,
    fm: dict[str, str],
    strict: bool,
) -> Path | None:
    raw_sup = fm.get("supersedes", "").strip()
    if not raw_sup:
        return None
    root_resolved = root.resolve()
    rel_path = spec_path.relative_to(root)
    require(
        spec_path.name in SPEC_PACK_FILES,
        f"{rel_path}: frontmatter 'supersedes' is only allowed on feature spec files",
    )
    require(
        raw_sup.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
        f"{rel_path}: frontmatter 'supersedes' forbids placeholder value '{raw_sup}'",
    )
    _check_non_empty_uri_path_safety(rel_path, "supersedes", raw_sup)
    require(
        not any(ch in raw_sup for ch in ("*", "?", "[", "]", "#", "|")),
        f"{rel_path}: frontmatter 'supersedes' must be a plain POSIX directory path '05 - Product Features/<old-folder>' (got '{raw_sup}')",
    )
    _check_no_uri_scheme(rel_path, "supersedes", raw_sup)
    require(
        not raw_sup.startswith("/") and not raw_sup.startswith("~"),
        f"{rel_path}: frontmatter 'supersedes' must be relative ('{raw_sup}')",
    )
    trimmed = raw_sup.rstrip("/")
    rel_sup = trimmed[len("docs/current/") :] if trimmed.startswith("docs/current/") else trimmed
    parts = rel_sup.split("/")
    require(
        len(parts) == 2
        and parts[0] == "05 - Product Features"
        and parts[1] not in {"", ".", ".."},
        f"{rel_path}: frontmatter 'supersedes' must have form '05 - Product Features/<old-folder>' (got '{raw_sup}')",
    )

    current_root = _resolve_docs_current_root(root_resolved, rel_path)
    old_dir = _walk_lexical_no_symlink(
        root_resolved,
        current_root,
        rel_sup,
        escape_msg=f"{rel_path}: 'supersedes' target escapes docs/current ('{raw_sup}')",
        symlink_msg=f"{rel_path}: symlinked 'supersedes' target refused ('{raw_sup}')",
        err_prefix=str(rel_path),
    )
    require(
        old_dir.is_dir(),
        f"{rel_path}: 'supersedes' target feature directory does not exist ('{raw_sup}')",
    )
    require(
        old_dir != spec_path.resolve().parent,
        f"{rel_path}: 'supersedes' cannot reference its own feature folder",
    )

    old_specs: list[Path] = []
    for name in sorted(SPEC_PACK_FILES):
        cand = old_dir / name
        require(not cand.is_symlink(), f"{rel_path}: symlinked spec inside 'supersedes' target '{raw_sup}'")
        if cand.is_file():
            old_specs.append(cand)
    require(
        bool(old_specs),
        f"{rel_path}: 'supersedes' target '{raw_sup}' contains no feature spec files",
    )

    curr_status = fm.get("status", "").strip().lower()
    if strict and curr_status == "approved":
        for old_spec in old_specs:
            old_raw = read_markdown(old_spec)
            _validate_governance_frontmatter(old_spec.relative_to(root_resolved), old_raw)
            old_fm = parse_frontmatter(old_raw)
            old_st = old_fm.get("status", "").strip().lower()
            require(
                old_st in {"superseded", "archived"},
                f"{rel_path}: approved replacement pack declares supersedes '{raw_sup}', "
                f"but '{old_spec.relative_to(root_resolved).as_posix()}' still has status '{old_st or 'missing'}' "
                "(expected 'superseded' or 'archived')",
            )

    return old_dir


def validate_clarify_gate(root: Path, files: list[Path], strict: bool = False) -> list[str]:
    warnings: list[str] = []
    for path in files:
        raw = read_markdown(path)
        rel_path = path.relative_to(root)
        _validate_governance_frontmatter(rel_path, raw)
        fm = parse_frontmatter(raw)
        status = fm.get("status", "").strip().lower()
        in_current = _is_in_docs_current(root, path)

        if in_current:
            _validate_no_leaked_secrets(rel_path, raw)
            _validate_triage_section(rel_path, raw)

        if path.name in SPEC_PACK_FILES:
            require(
                status in VALID_SPEC_STATUSES,
                f"{rel_path}: invalid or missing frontmatter status '{status or 'missing'}' "
                f"(expected one of: {', '.join(sorted(VALID_SPEC_STATUSES))})",
            )
        elif status:
            valid_note_statuses = VALID_SPEC_STATUSES | {"active", "template", "completed", "skipped"}
            require(
                status in valid_note_statuses,
                f"{rel_path}: invalid frontmatter status '{status}' "
                f"(expected one of: {', '.join(sorted(valid_note_statuses))})",
            )

        if in_current and fm.get("supersedes", "").strip():
            _validate_supersedes_field(root, path, fm, strict=strict)

        if status == "superseded":
            if in_current:
                sup_warnings, _ = _validate_superseded_by(root, path, raw, fm, strict=strict)
                warnings.extend(sup_warnings)
            continue
        if status == "archived":
            if in_current:
                _check_archived_spec_history(root, path, fm)
            continue
        if status not in {"draft", "approved", "example"}:
            continue

        stripped = strip_code(raw)

        if status == "draft":
            markers = re.findall(r"\[NEEDS CLARIFICATION\b[^\]]*\]", stripped, flags=re.I)
            require(
                len(markers) <= 3,
                f"{rel_path}: status: draft allows at most 3 [NEEDS CLARIFICATION] markers (found {len(markers)})",
            )
            continue

        if path.name in SPEC_PACK_FILES:
            for field in APPROVAL_FIELDS:
                val = fm.get(field, "").strip()
                require(
                    bool(val),
                    f"{rel_path}: status: {status} requires non-empty frontmatter '{field}'",
                )
                if status == "approved":
                    require(
                        val.lower() not in FORBIDDEN_APPROVED_PLACEHOLDERS,
                        f"{rel_path}: status: approved forbids placeholder value '{val}' in '{field}'",
                    )
            if status == "approved":
                warnings.extend(_check_approved_source_revision(root, path, raw, fm, strict=strict))

        require(
            not re.search(r"\[NEEDS CLARIFICATION\b", stripped, flags=re.I),
            f"{rel_path}: status: {status} forbids unresolved [NEEDS CLARIFICATION] markers",
        )
        for section_name in READINESS_SECTIONS:
            for section_body in _iter_h2_sections(stripped, section_name):
                require(
                    not re.search(r"(?m)^[ \t]*-\s*\[ \]", section_body),
                    f"{rel_path}: status: {status} forbids unchecked '- [ ]' items in '## {section_name}'",
                )

    return warnings


def validate_feature_folder(
    root: Path,
    feature_dir: Path,
    require_tasks: bool = False,
    strict: bool = False,
) -> list[str]:
    warnings: list[str] = []
    effective_strict = strict or require_tasks
    rel_feature = feature_dir.relative_to(root)

    p_mini = feature_dir / MINI_SPEC_FILE
    p1 = feature_dir / "1. Product Spec.md"
    p2 = feature_dir / "2. Tech Spec.md"
    p3 = feature_dir / "3. QA Spec.md"
    p4 = feature_dir / "4. Tasks.md"

    for candidate in (p_mini, p1, p2, p3, p4):
        require(not candidate.is_symlink(), f"{candidate.relative_to(root)}: spec file must not be a symlink")

    if p_mini.is_file():
        mixed_4 = [p.name for p in (p1, p2, p3, p4) if p.exists()]
        require(
            not mixed_4,
            f"{rel_feature}: cannot mix '{MINI_SPEC_FILE}' with 4-file spec pack ({', '.join(mixed_4)})",
        )
        raw_mini = read_markdown(p_mini)
        _validate_governance_frontmatter(p_mini.relative_to(root), raw_mini)
        fm_mini = parse_frontmatter(raw_mini)
        st_mini = fm_mini.get("status", "").strip().lower()
        require(
            st_mini in VALID_SPEC_STATUSES,
            f"{p_mini.relative_to(root)}: invalid or missing frontmatter status '{st_mini or 'missing'}' "
            f"(expected one of: {', '.join(sorted(VALID_SPEC_STATUSES))})",
        )
        warnings.extend(validate_clarify_gate(root, [p_mini], strict=effective_strict))
        if st_mini in {"superseded", "archived"}:
            return warnings

        is_ready_mini = st_mini in {"approved", "example"}
        require_mini_tables = is_ready_mini or require_tasks

        ac_rows = _extract_section_table_rows(
            p_mini.relative_to(root),
            raw_mini,
            "Acceptance criteria",
            ("id", "scenario", "expected result"),
            require_table=require_mini_tables,
        )
        mini_acs = _extract_acs_from_rows(ac_rows, "id")
        if require_mini_tables:
            require(
                len(mini_acs) >= 1,
                f"{p_mini.relative_to(root)}: '## Acceptance criteria' must declare at least one AC-xx",
            )

        parsed_mini_tasks = parse_execution_tasks(
            p_mini.relative_to(root),
            raw_mini,
            require_table=require_mini_tables,
        )
        task_acs = {
            ac
            for task in (parsed_mini_tasks or [])
            for ac in task["related_ac"]  # type: ignore[attr-defined]
        }
        if ac_rows is not None:
            ghost_mini = sorted(task_acs - mini_acs)
            require(
                not ghost_mini,
                f"{p_mini.relative_to(root)}: undeclared AC reference(s) not in '## Acceptance criteria': "
                f"{', '.join(ghost_mini)}",
            )
        if require_mini_tables:
            missing_mini = sorted(mini_acs - task_acs)
            require(
                not missing_mini,
                f"{p_mini.relative_to(root)}: '## Execution tasks' is missing AC coverage for: "
                f"{', '.join(missing_mini)}",
            )
        return warnings

    present = [p for p in (p1, p2, p3, p4) if p.is_file()]
    if not present:
        return warnings

    in_current_pack = _is_in_docs_current(root, feature_dir)
    raw_texts: dict[Path, str] = {}
    frontmatters: dict[Path, dict[str, str]] = {}
    statuses: dict[Path, str] = {}
    for spec_path in present:
        raw = read_markdown(spec_path)
        _validate_governance_frontmatter(spec_path.relative_to(root), raw)
        fm = parse_frontmatter(raw)
        st = fm.get("status", "").strip().lower()
        require(
            st in VALID_SPEC_STATUSES,
            f"{spec_path.relative_to(root)}: invalid or missing frontmatter status '{st or 'missing'}' "
            f"(expected one of: {', '.join(sorted(VALID_SPEC_STATUSES))})",
        )
        raw_texts[spec_path] = raw
        frontmatters[spec_path] = fm
        statuses[spec_path] = st

    if in_current_pack:
        supersedes_vals = {p: frontmatters[p].get("supersedes", "").strip() for p in present}
        if any(supersedes_vals.values()):
            require(
                all(supersedes_vals.values()),
                f"{rel_feature}: all specs in a 4-file pack must declare matching frontmatter 'supersedes'",
            )
            resolved_sup_dirs = {
                _validate_supersedes_field(root, p, frontmatters[p], strict=effective_strict)
                for p in present
            }
            require(
                len(resolved_sup_dirs) == 1,
                f"{rel_feature}: divergent 'supersedes' target folders across 4-file feature pack",
            )

    inactive_statuses = {st for st in statuses.values() if st in {"superseded", "archived"}}
    if inactive_statuses:
        unique_all = set(statuses.values())
        require(
            len(unique_all) == 1,
            f"{rel_feature}: mixed feature pack status across specs ({', '.join(f'{p.name}={s}' for p, s in statuses.items())})",
        )
        only_status = next(iter(unique_all))
        if in_current_pack and only_status == "superseded":
            scopes: list[tuple[str, str]] = []
            for spec_path in present:
                sup_w, scope = _validate_superseded_by(
                    root,
                    spec_path,
                    raw_texts[spec_path],
                    frontmatters[spec_path],
                    strict=effective_strict,
                )
                warnings.extend(sup_w)
                scopes.append(scope)
            require(
                len(set(scopes)) == 1,
                f"{rel_feature}: all specs in a superseded 4-file pack must target the same replacement feature folder or note",
            )
        elif in_current_pack and only_status == "archived":
            for spec_path in present:
                _check_archived_spec_history(root, spec_path, frontmatters[spec_path])
        return warnings

    ready_statuses = {st for st in statuses.values() if st in {"approved", "example"}}
    is_ready_pack = bool(ready_statuses)
    target_status = ""

    if is_ready_pack:
        target_status = "approved" if "approved" in ready_statuses else "example"
        require(
            p1.is_file() and p2.is_file() and p3.is_file(),
            f"{rel_feature}: {target_status} feature pack requires "
            "1. Product Spec.md, 2. Tech Spec.md, and 3. QA Spec.md",
        )
        for spec_path in present:
            require(
                statuses[spec_path] == target_status,
                f"{rel_feature}: mixed feature pack status "
                f"({spec_path.name} has status '{statuses[spec_path] or 'missing'}', expected '{target_status}')",
            )
            if target_status == "approved":
                warnings.extend(
                    _check_approved_source_revision(
                        root,
                        spec_path,
                        raw_texts[spec_path],
                        frontmatters[spec_path],
                        strict=effective_strict,
                    )
                )
        if not p4.is_file():
            if require_tasks:
                raise ValueError(
                    f"{rel_feature}: {target_status} feature pack is missing 4. Tasks.md (--require-tasks)"
                )
            if target_status == "approved":
                warnings.append(
                    f"{rel_feature}: approved 3-file feature pack omits 4. Tasks.md (legacy mode)"
                )

    product_acs: set[str] = set()
    if p1.is_file():
        p1_rows = _extract_section_table_rows(
            p1.relative_to(root),
            raw_texts[p1],
            "Acceptance criteria",
            ("id",),
            require_table=is_ready_pack or require_tasks,
        )
        product_acs = _extract_acs_from_rows(p1_rows, "id")

    tech_acs: set[str] = set()
    if p2.is_file():
        p2_rows = _extract_section_table_rows(
            p2.relative_to(root),
            raw_texts[p2],
            "Acceptance-criteria mapping",
            ("product ac",),
            require_table=is_ready_pack,
        )
        tech_acs = _extract_acs_from_rows(p2_rows, "product ac")
        ghost_tech = sorted(tech_acs - product_acs)
        require(
            not ghost_tech,
            f"{p2.relative_to(root)}: undeclared Product AC reference(s) not in 1. Product Spec.md: "
            f"{', '.join(ghost_tech)}",
        )

    qa_coverage_acs: set[str] = set()
    qa_trace_acs: set[str] = set()
    if p3.is_file():
        p3_cov_rows = _extract_section_table_rows(
            p3.relative_to(root),
            raw_texts[p3],
            "Coverage",
            ("acceptance criterion",),
            require_table=is_ready_pack,
        )
        p3_trace_rows = _extract_section_table_rows(
            p3.relative_to(root),
            raw_texts[p3],
            "Traceability and test ownership",
            ("product ac",),
            require_table=is_ready_pack,
        )
        qa_coverage_acs = _extract_acs_from_rows(p3_cov_rows, "acceptance criterion")
        qa_trace_acs = _extract_acs_from_rows(p3_trace_rows, "product ac")
        ghost_qa = sorted((qa_coverage_acs | qa_trace_acs) - product_acs)
        require(
            not ghost_qa,
            f"{p3.relative_to(root)}: undeclared Product AC reference(s) not in 1. Product Spec.md: "
            f"{', '.join(ghost_qa)}",
        )

    task_acs: set[str] = set()
    if p4.is_file():
        require_task_table = is_ready_pack or require_tasks
        parsed_tasks = parse_execution_tasks(
            p4.relative_to(root),
            raw_texts[p4],
            require_table=require_task_table,
        )
        task_acs = {
            ac
            for task in (parsed_tasks or [])
            for ac in task["related_ac"]  # type: ignore[attr-defined]
        }
        ghost_tasks = sorted(task_acs - product_acs)
        require(
            not ghost_tasks,
            f"{p4.relative_to(root)}: undeclared Product AC reference(s) not in 1. Product Spec.md: "
            f"{', '.join(ghost_tasks)}",
        )
        if require_task_table and p1.is_file():
            require(
                len(product_acs) >= 1,
                f"{p1.relative_to(root)}: Product Spec must declare at least one AC-xx in '## Acceptance criteria'",
            )
            missing_tasks = sorted(product_acs - task_acs)
            require(
                not missing_tasks,
                f"{p4.relative_to(root)}: Tasks Spec '## Execution tasks' is missing Product AC(s): "
                f"{', '.join(missing_tasks)}",
            )

    if is_ready_pack:
        require(
            len(product_acs) >= 1,
            f"{p1.relative_to(root)}: {target_status} Product Spec must declare at least one AC-xx in '## Acceptance criteria'",
        )
        missing_tech = sorted(product_acs - tech_acs)
        require(
            not missing_tech,
            f"{p2.relative_to(root)}: {target_status} Tech Spec '## Acceptance-criteria mapping' is missing Product AC(s): "
            f"{', '.join(missing_tech)}",
        )
        missing_qa_cov = sorted(product_acs - qa_coverage_acs)
        require(
            not missing_qa_cov,
            f"{p3.relative_to(root)}: {target_status} QA Spec '## Coverage' is missing Product AC(s): "
            f"{', '.join(missing_qa_cov)}",
        )
        missing_qa_trace = sorted(product_acs - qa_trace_acs)
        require(
            not missing_qa_trace,
            f"{p3.relative_to(root)}: {target_status} QA Spec '## Traceability and test ownership' is missing Product AC(s): "
            f"{', '.join(missing_qa_trace)}",
        )

    return warnings


def validate_feature_specs(
    root: Path,
    features_root: Path,
    require_tasks: bool = False,
    strict: bool = False,
) -> list[str]:
    if not features_root.is_dir():
        return []
    warnings: list[str] = []
    seen_prefixes: dict[str, str] = {}
    for child in sorted(features_root.iterdir(), key=lambda p: p.name):
        if child.name.startswith("."):
            continue
        require(
            not child.is_symlink(),
            f"{child.relative_to(root)}: feature directory must not be a symlink",
        )
        if child.is_dir():
            prefix_match = SEQ_PREFIX_RE.match(child.name)
            if prefix_match:
                prefix = prefix_match.group(1)
                if prefix in seen_prefixes:
                    raise ValueError(
                        f"{features_root.relative_to(root)}: duplicate numeric feature prefix '{prefix}-' "
                        f"shared by '{seen_prefixes[prefix]}' and '{child.name}'"
                    )
                seen_prefixes[prefix] = child.name
            warnings.extend(
                validate_feature_folder(
                    root,
                    child,
                    require_tasks=require_tasks,
                    strict=strict,
                )
            )
    return warnings
