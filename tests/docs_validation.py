"""Shared, portable Markdown validation for repository and installed docs."""

import posixpath
import re
from pathlib import Path, PurePosixPath

NUMBERED_SPEC_FILES = {
    "1. Product Spec.md",
    "2. Tech Spec.md",
    "3. QA Spec.md",
    "4. Tasks.md",
}
APPROVAL_FIELDS = (
    "approved_by",
    "approved_at",
    "approval_evidence",
    "source_revision",
)
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


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def strip_fenced_code(markdown_text: str) -> str:
    """Remove CommonMark fenced code blocks while preserving line structure."""
    text = markdown_text.replace("\r\n", "\n")
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


def parse_frontmatter(markdown_text: str) -> dict[str, str]:
    """Parse optional leading YAML scalar frontmatter."""
    text = markdown_text.replace("\r\n", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", text, flags=re.DOTALL)
    if not match:
        return {}
    result: dict[str, str] = {}
    body = match.group(1) or ""
    for line in body.split("\n"):
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or ":" not in line:
            continue
        key, raw_val = line.split(":", 1)
        key = key.strip()
        val = raw_val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in {'"', "'"}:
            val = val[1:-1].strip()
        if key:
            result[key] = val
    return result


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
    return bool(cells) and all(bool(re.fullmatch(r":?-{3,}:?", cell)) for cell in cells)


def _extract_section_table_rows(
    rel_path: Path,
    raw_text: str,
    section_heading: str,
    required_columns: tuple[str, ...],
    require_table: bool,
) -> list[dict[str, str]] | None:
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
                    headers = [re.sub(r"\s+", " ", h.strip().lower()) for h in header_cells]
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


def validate_links(root: Path, docs_root: Path, files: list[Path]) -> None:
    relative_paths = {path.relative_to(docs_root).with_suffix("").as_posix() for path in files}
    stems: dict[str, list[Path]] = {}
    for path in files:
        stems.setdefault(path.stem, []).append(path)

    wiki = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
    markdown = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    for path in files:
        content = strip_code(read(path))
        for match in wiki.finditer(content):
            target = match.group(1).strip().replace("\\", "/")
            relative = posixpath.normpath((path.parent.relative_to(docs_root) / target).as_posix())
            current = f"current/{target}"
            if target in relative_paths or relative in relative_paths or current in relative_paths:
                continue
            require(len(stems.get(target, [])) == 1, f"{path.relative_to(root)}: unresolved or ambiguous link [[{target}]]")
        for match in markdown.finditer(content):
            target = match.group(1).split("#", 1)[0]
            require(not target.lower().startswith("file:"), f"{path.relative_to(root)}: unsupported Markdown URI scheme file:")
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            candidate = (path.parent / target).resolve()
            require(candidate.is_relative_to(root), f"{path.relative_to(root)}: Markdown link target escapes project root {target}")
            require(candidate.is_file(), f"{path.relative_to(root)}: missing Markdown link target {target}")


def validate_mermaid(root: Path, files: list[Path]) -> None:
    block = re.compile(r"(?ms)^```mermaid[ \t]*\n(.*?)^```[ \t]*$")
    for path in files:
        content = read(path)
        diagrams = block.findall(content)
        require(content.count("```mermaid") == len(diagrams), f"{path.relative_to(root)}: malformed or unclosed Mermaid fence")
        for diagram in diagrams:
            require(bool(diagram.strip()), f"{path.relative_to(root)}: empty Mermaid diagram")
            require(bool(re.match(r"[A-Za-z][A-Za-z0-9_-]*", diagram.lstrip())), f"{path.relative_to(root)}: Mermaid diagram has no type")


def validate_clarify_gate(root: Path, files: list[Path]) -> None:
    for path in files:
        raw = read(path)
        fm = parse_frontmatter(raw)
        status = fm.get("status", "").strip().lower()
        if status not in {"draft", "approved", "example"}:
            continue
        rel_path = path.relative_to(root)
        stripped = strip_code(raw)

        if status == "draft":
            markers = re.findall(r"\[NEEDS CLARIFICATION\b[^\]]*\]", stripped, flags=re.I)
            require(
                len(markers) <= 3,
                f"{rel_path}: status: draft allows at most 3 [NEEDS CLARIFICATION] markers (found {len(markers)})",
            )
            continue

        if path.name in NUMBERED_SPEC_FILES:
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


def _parse_owned_paths(rel_path: Path, task_id: str, cell: str) -> list[PurePosixPath]:
    paths: list[PurePosixPath] = []
    outer_match = re.fullmatch(r"(`+)([^`]*)\1", cell.strip())
    unwrapped = outer_match.group(2) if outer_match else cell
    for raw_item in unwrapped.split(","):
        cleaned = raw_item.strip()
        if not cleaned:
            continue
        code_match = re.fullmatch(r"(`+)([^`]*)\1", cleaned)
        if code_match:
            cleaned = code_match.group(2).strip()
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
            not cleaned.startswith("/"),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' must be relative to project root",
        )
        trimmed = cleaned.rstrip("/")
        raw_segments = trimmed.split("/") if trimmed else [""]
        require(
            not any(seg in {"", ".", ".."} for seg in raw_segments),
            f"{rel_path}: task {task_id} Owned path '{cleaned}' contains invalid '.' or '..' segments",
        )
        paths.append(PurePosixPath(trimmed))

    require(bool(paths), f"{rel_path}: task {task_id} must declare at least one Owned path")
    return paths


def _validate_tasks_rows(rel_path: Path, rows: list[dict[str, str]]) -> None:
    task_order: list[str] = []
    seen_ids: set[str] = set()
    raw_deps: dict[str, list[str]] = {}
    parallel_flags: dict[str, str] = {}
    owned_paths: dict[str, list[PurePosixPath]] = {}

    for row in rows:
        tid = row["task id"].strip()
        require(
            bool(re.fullmatch(r"T-\d+", tid)),
            f"{rel_path}: invalid Task ID '{tid}' (expected T-xx)",
        )
        require(tid not in seen_ids, f"{rel_path}: duplicate Task ID '{tid}'")
        seen_ids.add(tid)
        task_order.append(tid)

        status_val = row["status"].strip().lower()
        require(
            status_val in VALID_TASK_STATUSES,
            f"{rel_path}: task {tid} has invalid Status '{row['status']}' "
            f"(expected one of: {', '.join(sorted(VALID_TASK_STATUSES))})",
        )

        p_val = row["[p]"].strip().lower()
        require(
            p_val in {"yes", "no"},
            f"{rel_path}: task {tid} has invalid [P] value '{row['[p]']}' (expected yes or no)",
        )
        parallel_flags[tid] = p_val

        dep_cell = row["depends on"].strip()
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
        owned_paths[tid] = _parse_owned_paths(rel_path, tid, row["owned paths"])

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
            for pa in owned_paths[tid_a]:
                for pb in owned_paths[tid_b]:
                    if pa == pb or pa.is_relative_to(pb) or pb.is_relative_to(pa):
                        raise ValueError(
                            f"{rel_path}: parallel [P] tasks {tid_a} ('{pa.as_posix()}') and "
                            f"{tid_b} ('{pb.as_posix()}') have overlapping Owned paths"
                        )


def validate_feature_folder(
    root: Path,
    feature_dir: Path,
    require_tasks: bool = False,
) -> list[str]:
    warnings: list[str] = []
    p1 = feature_dir / "1. Product Spec.md"
    p2 = feature_dir / "2. Tech Spec.md"
    p3 = feature_dir / "3. QA Spec.md"
    p4 = feature_dir / "4. Tasks.md"
    present = [p for p in (p1, p2, p3, p4) if p.is_file()]
    if not present:
        return warnings

    raw_texts: dict[Path, str] = {}
    statuses: dict[Path, str] = {}
    for spec_path in present:
        raw = read(spec_path)
        raw_texts[spec_path] = raw
        statuses[spec_path] = parse_frontmatter(raw).get("status", "").strip().lower()

    ready_statuses = {st for st in statuses.values() if st in {"approved", "example"}}
    is_ready_pack = bool(ready_statuses)
    target_status = ""
    rel_feature = feature_dir.relative_to(root)

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
            require_table=is_ready_pack,
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
    task_rows: list[dict[str, str]] | None = None
    if p4.is_file():
        require_task_table = is_ready_pack or require_tasks
        task_rows = _extract_section_table_rows(
            p4.relative_to(root),
            raw_texts[p4],
            "Execution tasks",
            TASK_COLUMNS,
            require_table=require_task_table,
        )
        if require_task_table:
            require(
                bool(task_rows),
                f"{p4.relative_to(root)}: '## Execution tasks' must define at least one task row",
            )
        task_acs = _extract_acs_from_rows(task_rows, "related ac")
        ghost_tasks = sorted(task_acs - product_acs)
        require(
            not ghost_tasks,
            f"{p4.relative_to(root)}: undeclared Product AC reference(s) not in 1. Product Spec.md: "
            f"{', '.join(ghost_tasks)}",
        )
        if task_rows:
            _validate_tasks_rows(p4.relative_to(root), task_rows)

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
        if p4.is_file():
            missing_tasks = sorted(product_acs - task_acs)
            require(
                not missing_tasks,
                f"{p4.relative_to(root)}: {target_status} Tasks Spec '## Execution tasks' is missing Product AC(s): "
                f"{', '.join(missing_tasks)}",
            )

    return warnings


def validate_feature_specs(
    root: Path,
    features_root: Path,
    require_tasks: bool = False,
) -> list[str]:
    if not features_root.is_dir():
        return []
    warnings: list[str] = []
    for child in sorted(features_root.iterdir()):
        if child.is_dir() and not child.name.startswith("."):
            warnings.extend(validate_feature_folder(root, child, require_tasks=require_tasks))
    return warnings
