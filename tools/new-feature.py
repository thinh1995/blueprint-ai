#!/usr/bin/env python3
"""Scaffold a 4-file feature pack or 1-file Mini-Spec under docs/current/05 - Product Features/."""

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
    r"^(approved_by|approved_at|approval_evidence|source_revision|superseded_by|supersedes):[ \t]*.*$",
    re.M,
)

MINI_SPEC_NAME = "1. Mini Spec.md"
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
    "security-hardening",
)

AI_ADDENDUM_ROWS = (
    "AI addendum: model / policy / prompt version",
    "AI addendum: Tool permissions, timeout, retry, fallback",
    "AI addendum: knowledge provenance, citation, retention",
    "AI addendum: human escalation and evaluation threshold",
)

BLAST_ANCHOR_RE = r"^(- Affected modules, routes, jobs, schemas, or integrations:)[ \t]*$"

IGNORED_PRESET_ENTRIES = {".DS_Store", ".gitkeep"}


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


def is_source_template_repository(root: Path) -> bool:
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
            manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
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
        if entry.name in IGNORED_PRESET_ENTRIES:
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
            if entry.name in IGNORED_PRESET_ENTRIES:
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


def sub_once_required(pattern: str, repl: str, text: str, label: str) -> str:
    updated, count = re.subn(pattern, repl, text, count=1, flags=re.M)
    if count != 1:
        raise ValueError(f"expected preset anchor {label!r} not found")
    return updated


def replace_once_required(text: str, target: str, replacement: str, label: str) -> str:
    if target not in text:
        raise ValueError(f"expected preset anchor {label!r} not found")
    return text.replace(target, replacement, 1)


def replace_table_row_by_first_cell(text: str, first_cell: str, col2: str, col3: str) -> str:
    pattern = re.compile(r"^\|\s*" + re.escape(first_cell) + r"\s*\|.*\|[ \t]*$", re.M)
    replacement = f"| {first_cell} | {col2} | {col3} |"
    updated, count = pattern.subn(lambda _m: replacement, text, count=1)
    if count == 0:
        raise ValueError(f"expected template table row '{first_cell}' not found in 2. Tech Spec.md")
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
        raise ValueError("expected QA-01/AC-01 coverage row not found in 3. QA Spec.md")

    trace_pattern = re.compile(r"^\|\s*AC-01\s*\|\s*QA-01\s*\|.*\|[ \t]*$", re.M)
    trace_row = f"| AC-01 | QA-01 | {test_cmd} | qa |"
    text, count = trace_pattern.subn(lambda _m: trace_row, text, count=1)
    if count == 0:
        raise ValueError("expected AC-01/QA-01 traceability row not found in 3. QA Spec.md")

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


def replace_execution_task_rows(text: str, rows: list[str], spec_label: str = "4. Tasks.md") -> str:
    section_match = re.search(r"^##[ \t]+Execution tasks[ \t]*$", text, re.M)
    if not section_match:
        raise ValueError(f"expected '## Execution tasks' section not found in {spec_label}")

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
        raise ValueError(f"expected Markdown table under '## Execution tasks' in {spec_label}")

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
        tech = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 HTTP routes, hợp đồng request/response, middleware phân quyền/tenant và migration dữ liệu.",
            tech,
            "2. Tech Spec.md blast-radius bullet",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Xác định HTTP method/route, schema request/response, mã trạng thái, idempotency key và phân trang.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Xác định bước migration tương thích xuôi/ngược, độ an toàn backfill và kịch bản rollback.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Xác định structured log cho request, metric độ trễ/5xx và ngưỡng cảnh báo.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Xác định trình tự triển khai không gián đoạn, feature flag bảo vệ và điều kiện rollback.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Xác định timeout dịch vụ phụ thuộc, giới hạn retry và phản hồi suy giảm an toàn.",
            "engineering",
        )
        for ai_row in AI_ADDENDUM_ROWS:
            tech = replace_table_row_by_first_cell(
                tech, ai_row, "Không áp dụng (preset web-api).", "n/a"
            )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Hiện thực hóa HTTP route có phiên bản, kiểm tra ranh giới auth/tenant và tầng lưu trữ.",
            "`pytest tests/api/`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Caller đã xác thực và dữ liệu mẫu cô lập theo tenant.",
            steps="Gửi request hợp lệ, payload lỗi 4xx, truy cập trái phép/chéo tenant, kiểm tra rate-limit và rollback migration.",
            expected="Trả về 2xx cho luồng hợp lệ; lỗi 400/401/403/429 tất định; không rò rỉ dữ liệu chéo tenant; rollback sạch.",
            automated="yes",
            test_cmd="`pytest tests/api/`",
            extra_edge_bullets=[
                "Preset web-api: kiểm thử phân quyền 401/403 & cô lập chéo tenant, kiểm tra schema 4xx, giới hạn tần suất (429) và rollback migration.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/api/contracts/` | Định nghĩa hợp đồng HTTP route, mã trạng thái, phân trang và kế hoạch migration. | `pytest tests/api/test_contracts.py` |",
                "| T-02 | todo | no | T-01 | AC-01 | `src/api/handlers/` | Hiện thực hóa handler kèm kiểm tra auth/tenant, xác thực 4xx và rate-limit. | `pytest tests/api/test_handlers.py` |",
            ],
        )

    elif preset_name == "cli-tool":
        tech = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Điểm vào CLI, bộ phân tích tham số, chốt chặn filesystem/symlink và hợp đồng mã thoát (không áp dụng web/multi-tenancy).",
            tech,
            "2. Tech Spec.md blast-radius bullet",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Xác định cờ/tham số CLI, mã thoát (0 thành công, 1 lỗi thực thi, 2 sai cú pháp) và luồng stdin/stdout/stderr.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Không áp dụng (preset cli-tool; nêu tính tương thích định dạng file cấu hình/xuất nếu có lưu đĩa).",
            "n/a",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Xác định kết xuất stdout tất định và thông báo chẩn đoán lỗi rõ ràng trên stderr.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Xác định chế độ xem trước --dry-run, ghi file nguyên tử (O_EXCL), từ chối symlink và dọn dẹp khi lỗi.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Ưu tiên chạy độc lập bằng thư viện chuẩn; dừng sớm kèm thông báo rõ khi thiếu công cụ ngoài.",
            "engineering",
        )
        for ai_row in AI_ADDENDUM_ROWS:
            tech = replace_table_row_by_first_cell(
                tech, ai_row, "Không áp dụng (preset cli-tool).", "n/a"
            )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Hiện thực hóa bộ phân tích cờ CLI, hợp đồng luồng xuất/lỗi, ghi file nguyên tử và chặn symlink/path traversal.",
            "`pytest tests/test_cli.py`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Thư mục tạm cô lập chứa dữ liệu kiểm thử.",
            steps="Chạy lệnh hợp lệ, cờ sai cú pháp, chế độ --dry-run, chạy lặp idempotent và đường dẫn ../ hoặc symlink.",
            expected="Thoát mã 0 khi hợp lệ/--dry-run (không ghi đĩa ở --dry-run); thoát mã khác 0 tất định khi cờ sai hoặc đường dẫn không an toàn.",
            automated="yes",
            test_cmd="`pytest tests/test_cli.py`",
            extra_edge_bullets=[
                "Preset cli-tool: kiểm thử cờ không hợp lệ, mã thoát khác 0 (1/2), cam kết không ghi đĩa với --dry-run, tính idempotent và từ chối symlink/path traversal.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/cli/parser.py` | Hiện thực hóa bộ phân tích tham số CLI, mã thoát, --dry-run và chốt chặn ghi file nguyên tử/symlink. | `pytest tests/test_cli.py -k parser` |",
                "| T-02 | todo | no | T-01 | AC-01 | `tests/test_cli.py` | Bổ sung kiểm thử tích hợp cho hợp đồng stdout/stderr, tính idempotent và chặn path traversal. | `pytest tests/test_cli.py` |",
            ],
        )

    elif preset_name == "ai-agent":
        tech = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Bộ điều phối agent, cấu hình prompt/policy, luồng truy xuất có dẫn nguồn, danh sách cho phép tool và bộ đánh giá.",
            tech,
            "2. Tech Spec.md blast-radius bullet",
        )
        tech = replace_once_required(
            tech,
            "For every diagram, record:",
            "Lưu ý preset ai-agent: bổ sung sơ đồ Mermaid cho luồng tương tác (sequence), trạng thái/lỗi (state) và ranh giới dữ liệu với nhãn đặt trong dấu ngoặc kép.\n\nFor every diagram, record:",
            "2. Tech Spec.md diagram anchor",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Xác định cấu trúc request/response của agent, schema trích dẫn nguồn và trạng thái chuyển giao con người.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Xác định cách đánh phiên bản prompt/policy và tính tương thích bộ dữ liệu đánh giá (eval).",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Xác định trace ID, nhãn phiên bản model/prompt, bộ đếm lỗi/timeout của tool và cảnh báo tỷ lệ leo thang.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Xác định quy trình rollback phiên bản model/prompt đã ghim và công tắc ngắt an toàn sang con người.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Xác định timeout cho model/truy xuất, trần retry và phản hồi dự phòng tất định khi nhà cung cấp lỗi.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: model / policy / prompt version",
            "Ghim định danh model, bản sửa đổi system policy và mã phiên bản mẫu prompt.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: Tool permissions, timeout, retry, fallback",
            "Định nghĩa danh sách tool đọc/ghi được phép, timeout từng tool, trần retry và nhánh dự phòng an toàn.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: knowledge provenance, citation, retention",
            "Giới hạn truy xuất theo nguồn đã duyệt của từng tenant, bắt buộc trích dẫn nguồn và thời hạn lưu trace.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AI addendum: human escalation and evaluation threshold",
            "Định nghĩa ngưỡng độ tin cậy/an toàn để chuyển con người, dữ liệu bàn giao và ngưỡng vượt bài eval.",
            "qa",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Hiện thực hóa truy xuất có trích dẫn nguồn, chính sách allowlist/timeout cho tool và cổng chuyển giao con người.",
            "`pytest tests/agent_eval/`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Cấu hình model/prompt đã ghim và bộ dữ liệu đánh giá chuẩn.",
            steps="Chạy câu hỏi có nguồn, câu hỏi thiếu nguồn, payload prompt injection, lệnh gọi tool trái phép và ca leo thang.",
            expected="Câu trả lời trích dẫn đúng nguồn được duyệt; ca thiếu nguồn, injection hoặc gọi tool trái phép bị từ chối an toàn hoặc chuyển con người.",
            automated="yes",
            test_cmd="`pytest tests/agent_eval/`",
            extra_edge_bullets=[
                "Preset ai-agent: kiểm thử từ chối khi thiếu nguồn (chống bịa đặt), kháng prompt injection từ dữ liệu không tin cậy, chặn tool trái phép và bàn giao con người.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/agent/policy/` | Định nghĩa cấu hình ghim phiên bản model/prompt, allowlist tool, timeout/fallback và quy tắc leo thang. | `pytest tests/agent_eval/test_policy.py` |",
                "| T-02 | todo | yes | T-01 | AC-01 | `src/agent/retrieval/` | Hiện thực hóa luồng truy xuất cô lập theo tenant và bộ định dạng trích dẫn nguồn bắt buộc. | `pytest tests/agent_eval/test_retrieval.py` |",
                "| T-03 | todo | no | T-02 | AC-01 | `tests/agent_eval/` | Bổ sung bộ kiểm thử đánh giá từ chối khi thiếu nguồn, chống prompt injection, chặn tool trái phép và bàn giao con người. | `pytest tests/agent_eval/` |",
            ],
        )

    elif preset_name == "security-hardening":
        tech = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Ranh giới tin cậy (trust boundaries), xác thực/phân quyền, cô lập tenant, quản lý khoá bí mật, lọc dữ liệu nhạy cảm trên log và phụ thuộc bên ngoài.",
            tech,
            "2. Tech Spec.md blast-radius bullet",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "API / event contract and versioning",
            "Xác định ranh giới xác thực/phân quyền (authn/authz), kiểm tra đầu vào nghiêm ngặt, rate-limit và mã lỗi không làm lộ thông tin nội bộ.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Schema or data migration",
            "Xác định mã hoá dữ liệu nhạy cảm, xoay vòng khoá/token tương thích ngược và kịch bản backfill/rollback an toàn.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Observability (logs, metrics, alerts)",
            "Đảm bảo che giấu (redact) secret/token/PII trên toàn bộ log/trace, bổ sung audit log và cảnh báo hành vi bất thường.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Deployment and rollback plan",
            "Xác định trình tự triển khai bản vá bảo mật, xoay vòng/thu hồi thông tin xác thực an toàn và phương án rollback tức thời.",
            "engineering",
        )
        tech = replace_table_row_by_first_cell(
            tech,
            "Dependencies / third-party failure mode",
            "Ghim phiên bản phụ thuộc an toàn, cổng quét SCA/SAST/secret trên CI và chế độ đóng an toàn (fail-closed) khi dịch vụ xác thực lỗi.",
            "engineering",
        )
        for ai_row in AI_ADDENDUM_ROWS:
            tech = replace_table_row_by_first_cell(
                tech, ai_row, "Không áp dụng (preset security-hardening; điền chi tiết nếu phạm vi có thành phần AI Agent).", "n/a"
            )
        tech = replace_table_row_by_first_cell(
            tech,
            "AC-01",
            "Gia cố kiểm soát truy cập/cô lập tenant, xác thực đầu vào chống injection, che giấu secret/PII và đóng mã SEC-xx liên quan.",
            "`pytest tests/security/`",
        )

        qa = replace_qa_rows(
            qa,
            preconditions="Môi trường local/dev cô lập với tài khoản đa vai trò/đa tenant và dữ liệu kiểm thử giả lập (không dùng secret thật).",
            steps="Thực thi kiểm thử leo thang đặc quyền (IDOR/chéo tenant), payload biên/injection, xác minh che giấu secret/PII trong log và kịch bản fail-closed.",
            expected="Mọi truy cập trái phép hoặc payload độc hại bị chặn tất định (401/403/400); không rò rỉ dữ liệu chéo tenant hay secret trong phản hồi/log.",
            automated="yes",
            test_cmd="`pytest tests/security/`",
            extra_edge_bullets=[
                "Preset security-hardening: kiểm thử chống leo thang đặc quyền & IDOR chéo tenant, chặn injection/traversal, xác minh che giấu secret/PII trên log và hành vi fail-closed.",
            ],
        )

        tasks = replace_execution_task_rows(
            tasks,
            [
                "| T-01 | todo | no | - | AC-01 | `src/security/` | Gia cố ranh giới xác thực/phân quyền, kiểm tra đầu vào an toàn và bộ lọc che giấu secret/PII trên log. | `pytest tests/security/test_controls.py` |",
                "| T-02 | todo | no | T-01 | AC-01 | `tests/security/` | Bổ sung kiểm thử hồi quy bảo mật cho các ca lạm dụng, cô lập tenant và đối chiếu đóng mã SEC-xx. | `pytest tests/security/` |",
            ],
        )

    docs["2. Tech Spec.md"] = tech
    docs["3. QA Spec.md"] = qa
    docs["4. Tasks.md"] = tasks
    return docs


def apply_builtin_mini_overlay(preset_name: str, mini_text: str) -> str:
    if preset_name == "general":
        return mini_text

    if preset_name == "web-api":
        mini_text = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 HTTP route, hợp đồng request/response, kiểm tra quyền/tenant và tầng lưu trữ.",
            mini_text,
            "1. Mini Spec.md blast-radius bullet",
        )
        mini_text = replace_execution_task_rows(
            mini_text,
            [
                "| T-01 | todo | no | - | AC-01 | `src/api/handlers/` | Hiện thực hóa endpoint kèm xác thực schema 4xx, ranh giới auth/tenant và kiểm thử tự động. | `pytest tests/api/` |",
            ],
            spec_label=MINI_SPEC_NAME,
        )
    elif preset_name == "cli-tool":
        mini_text = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Bộ phân tích cờ CLI, hợp đồng mã thoát/stdout/stderr và chốt chặn filesystem/symlink.",
            mini_text,
            "1. Mini Spec.md blast-radius bullet",
        )
        mini_text = replace_execution_task_rows(
            mini_text,
            [
                "| T-01 | todo | no | - | AC-01 | `src/cli/` | Hiện thực hóa tham số CLI, mã thoát tất định, --dry-run và kiểm thử chặn symlink/traversal. | `pytest tests/test_cli.py` |",
            ],
            spec_label=MINI_SPEC_NAME,
        )
    elif preset_name == "ai-agent":
        mini_text = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Cấu hình prompt/policy đã ghim, allowlist/timeout cho tool, trích dẫn nguồn và cổng leo thang con người.",
            mini_text,
            "1. Mini Spec.md blast-radius bullet",
        )
        mini_text = replace_execution_task_rows(
            mini_text,
            [
                "| T-01 | todo | no | - | AC-01 | `src/agent/` | Hiện thực hóa chính sách tool/prompt đã ghim, trích dẫn nguồn và bộ kiểm thử chống prompt injection. | `pytest tests/agent_eval/` |",
            ],
            spec_label=MINI_SPEC_NAME,
        )
    elif preset_name == "security-hardening":
        mini_text = sub_once_required(
            BLAST_ANCHOR_RE,
            r"\1 Ranh giới xác thực/phân quyền, kiểm tra đầu vào chống injection, cô lập tenant và che giấu secret/PII trên log.",
            mini_text,
            "1. Mini Spec.md blast-radius bullet",
        )
        mini_text = replace_execution_task_rows(
            mini_text,
            [
                "| T-01 | todo | no | - | AC-01 | `src/security/` | Gia cố kiểm soát bảo mật, che giấu secret/PII trên log, kiểm thử hồi quy chống lạm dụng và đóng mã SEC-xx liên quan. | `pytest tests/security/` |",
            ],
            spec_label=MINI_SPEC_NAME,
        )

    return mini_text


def hydrate_spec_content(content: str, title: str, supersede_folder: str | None = None) -> str:
    hydrated = content.replace("[Feature name]", title)
    match = FRONTMATTER_RE.match(hydrated)
    if match:
        fm_open, fm_body, fm_close = match.groups()
        status_match = re.search(r"^status:[ \t]*(.*?)[ \t]*$", fm_body, re.M)
        status_val = status_match.group(1).strip().strip("'\"").lower() if status_match else ""
        if status_val == "draft":
            fm_body = APPROVAL_FIELD_RE.sub(r"\1:", fm_body)
        if supersede_folder:
            sup_line = f'supersedes: "05 - Product Features/{supersede_folder}"'
            if re.search(r"^supersedes:[ \t]*.*$", fm_body, re.M):
                fm_body = re.sub(r"^supersedes:[ \t]*.*$", lambda _m: sup_line, fm_body, count=1, flags=re.M)
            elif re.search(r"^status:[ \t]*.*$", fm_body, re.M):
                fm_body = re.sub(
                    r"^(status:[ \t]*.*)$",
                    lambda m: f"{m.group(1)}\n{sup_line}",
                    fm_body,
                    count=1,
                    flags=re.M,
                )
            else:
                fm_body = f"{sup_line}\n{fm_body}"
        hydrated = fm_open + fm_body + fm_close + hydrated[match.end() :]
    return hydrated


def _extract_top_level_status(markdown_text: str) -> str:
    normalized = markdown_text.lstrip("\ufeff").replace("\r\n", "\n").replace("\r", "\n")
    match = re.match(r"^---[ \t]*\n(?:(.*?)\n)?---[ \t]*(?:\n|$)", normalized, re.S)
    if not match:
        return ""
    for line in (match.group(1) or "").split("\n"):
        if line.startswith((" ", "\t")):
            continue
        stripped = line.strip()
        if stripped.startswith("status:"):
            val = line.split(":", 1)[1].strip()
            val = re.split(r"[ \t]+#", val, maxsplit=1)[0].strip().strip("'\"")
            return val.lower()
    return ""


def _is_inactive_feature_dir(entry: Path) -> bool:
    spec_paths: list[Path] = []
    for name in (MINI_SPEC_NAME, *CANONICAL_SPECS):
        cand = entry / name
        if cand.is_symlink():
            return False
        if cand.is_file():
            spec_paths.append(cand)
    if not spec_paths:
        return False
    return all(
        _extract_top_level_status(p.read_text(encoding="utf-8-sig")) in {"superseded", "archived"}
        for p in spec_paths
    )


def _print_supersede_reminder(supersede_folder: str | None) -> None:
    if supersede_folder:
        print(
            f"REMINDER: '05 - Product Features/{supersede_folder}' remains active until '/sdd-analyze' "
            "atomically stamps status: superseded and superseded_by after explicit user approval."
        )


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


def _require_builtin_preset(preset_name: str) -> None:
    if preset_name not in BUILTIN_PRESETS:
        fail(
            f"unknown preset '{preset_name}' "
            f"(not in built-in presets {', '.join(BUILTIN_PRESETS)} and "
            f"custom directory docs/templates/presets/{preset_name} does not exist)"
        )


def _readme_references_four_file_pack(readme_text: str) -> bool:
    return any(
        token in readme_text
        for token in ("1. Product Spec", "2. Tech Spec", "3. QA Spec", "4. Tasks", "1.%20Product%20Spec")
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scaffold a 4-file Spec-Driven Development pack or a 1-file Mini-Spec (--mini)."
    )
    parser.add_argument(
        "slug",
        nargs="?",
        help="Lowercase kebab-case feature slug (e.g. user-auth).",
    )
    parser.add_argument(
        "--mini",
        action="store_true",
        help="Scaffold a 1-file Tier M Mini-Spec ('1. Mini Spec.md') instead of the 4-file pack.",
    )
    parser.add_argument(
        "--title",
        help="Human-readable feature title (defaults to title-cased slug).",
    )
    parser.add_argument(
        "--preset",
        help="Built-in preset (general, web-api, cli-tool, ai-agent, security-hardening) or custom preset under docs/templates/presets/<name>.",
    )
    parser.add_argument(
        "--supersede",
        metavar="EXISTING_FOLDER",
        help="Promote or replace an existing feature folder under docs/current/05 - Product Features/<folder> (records frontmatter supersedes and allocates next NNN- prefix).",
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

    slug_seq_match = SEQ_PREFIX_RE.match(slug)
    if slug_seq_match and not args.plain:
        stripped_slug = SEQ_PREFIX_RE.sub("", slug)
        fail(
            f"do not include a leading numeric prefix in '{slug}': "
            f"pass '{stripped_slug}' without numeric prefix, or add --plain"
        )

    if args.title is not None:
        raw_title = args.title.strip()
        if not raw_title or "\n" in raw_title or "\r" in raw_title:
            fail("--title must be a non-empty single-line string")
        title = raw_title.replace("|", r"\|")
    else:
        clean_for_title = SEQ_PREFIX_RE.sub("", slug) if slug_seq_match else slug
        title = " ".join(part.capitalize() for part in clean_for_title.split("-"))

    preset_name = resolve_preset_name(args.preset)

    features_root = ensure_no_symlinks(
        ROOT, ("docs", "current", "05 - Product Features"), must_exist=True
    )
    if not features_root.is_dir():
        fail("docs/current/05 - Product Features is not a directory")

    supersede_folder: str | None = None
    if args.supersede is not None:
        raw_sup = args.supersede.strip()
        if (
            not raw_sup
            or raw_sup in {".", ".."}
            or "/" in raw_sup
            or "\\" in raw_sup
            or any(ord(ch) < 32 or ord(ch) == 127 for ch in raw_sup)
        ):
            fail(
                f"invalid --supersede '{args.supersede}' "
                "(expected existing folder name inside docs/current/05 - Product Features/)"
            )
        sup_dir = ensure_no_symlinks(
            ROOT, ("docs", "current", "05 - Product Features", raw_sup), must_exist=True
        )
        if not sup_dir.is_dir():
            fail(f"--supersede target is not a directory: docs/current/05 - Product Features/{raw_sup}")
        has_spec = False
        for spec_cand_name in (MINI_SPEC_NAME, *CANONICAL_SPECS):
            spec_cand = sup_dir / spec_cand_name
            if spec_cand.is_symlink():
                fail(f"symlink refused inside --supersede target '{raw_sup}': {spec_cand_name}")
            if spec_cand.is_file():
                has_spec = True
        if not has_spec:
            fail(f"--supersede target contains no canonical or Mini-Spec files: {raw_sup}")
        if _is_inactive_feature_dir(sup_dir):
            fail(
                f"--supersede target '{raw_sup}' is already superseded or archived; "
                "supersede the active successor pack instead"
            )
        if args.plain and slug == raw_sup:
            fail(f"--plain cannot reuse exact folder name '{slug}' when superseding '{raw_sup}'")
        supersede_folder = raw_sup

    presets_root = ensure_no_symlinks(ROOT, ("docs", "templates", "presets"), must_exist=False)
    if presets_root.exists() and not presets_root.is_dir():
        fail("docs/templates/presets exists and is not a directory")
    custom_dir = presets_root / preset_name

    ordered_files: list[tuple[str, str]] = []
    try:
        if args.mini:
            mini_template_path = ensure_no_symlinks(
                ROOT, ("docs", "templates", "mini-spec-template", MINI_SPEC_NAME), must_exist=True
            )
            if not mini_template_path.is_file():
                fail(f"canonical Mini-Spec template is not a regular file: {mini_template_path.relative_to(ROOT)}")
            base_mini = mini_template_path.read_text(encoding="utf-8-sig")

            if custom_dir.exists() or custom_dir.is_symlink():
                custom_files = validate_custom_preset_dir(custom_dir, preset_name)
                custom_map = {path.name: path.read_text(encoding="utf-8-sig") for path in custom_files}
                if MINI_SPEC_NAME in custom_map:
                    mini_body = custom_map[MINI_SPEC_NAME]
                elif preset_name in BUILTIN_PRESETS:
                    mini_body = apply_builtin_mini_overlay(preset_name, base_mini)
                else:
                    mini_body = base_mini

                if "README.md" in custom_map and (
                    MINI_SPEC_NAME in custom_map
                    or not _readme_references_four_file_pack(custom_map["README.md"])
                ):
                    ordered_files.append(("README.md", hydrate_spec_content(custom_map["README.md"], title)))
            else:
                _require_builtin_preset(preset_name)
                mini_body = apply_builtin_mini_overlay(preset_name, base_mini)
            ordered_files.append(
                (MINI_SPEC_NAME, hydrate_spec_content(mini_body, title, supersede_folder=supersede_folder))
            )
        else:
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
                base_docs[spec_name] = spec_path.read_text(encoding="utf-8-sig")

            if custom_dir.exists() or custom_dir.is_symlink():
                custom_files = validate_custom_preset_dir(custom_dir, preset_name)
                custom_map = {path.name: path.read_text(encoding="utf-8-sig") for path in custom_files}
                merged = dict(base_docs)
                for spec_name in CANONICAL_SPECS:
                    if spec_name in custom_map:
                        merged[spec_name] = custom_map[spec_name]
                if "README.md" in custom_map:
                    ordered_files.append(("README.md", hydrate_spec_content(custom_map["README.md"], title)))
                for spec_name in CANONICAL_SPECS:
                    ordered_files.append(
                        (spec_name, hydrate_spec_content(merged[spec_name], title, supersede_folder=supersede_folder))
                    )
                for extra_name in sorted(custom_map):
                    if extra_name not in CANONICAL_SPECS and extra_name not in {"README.md", MINI_SPEC_NAME}:
                        ordered_files.append((extra_name, hydrate_spec_content(custom_map[extra_name], title)))
            else:
                _require_builtin_preset(preset_name)
                overlaid = apply_builtin_overlay(preset_name, dict(base_docs))
                for spec_name in CANONICAL_SPECS:
                    ordered_files.append(
                        (spec_name, hydrate_spec_content(overlaid[spec_name], title, supersede_folder=supersede_folder))
                    )
    except ValueError as exc:
        fail(str(exc))

    requested_seq_prefix = slug_seq_match.group(1) if slug_seq_match else None
    requested_base_slug = SEQ_PREFIX_RE.sub("", slug) if slug_seq_match else slug

    max_seq = 0
    for entry in sorted(features_root.iterdir(), key=lambda p: p.name):
        if entry.is_symlink():
            fail(f"symlink refused inside 05 - Product Features: {entry.name}")
        if not entry.is_dir():
            continue
        base_slug = SEQ_PREFIX_RE.sub("", entry.name)
        is_allowed_supersede = (
            (supersede_folder is not None and entry.name == supersede_folder)
            or _is_inactive_feature_dir(entry)
        ) and not (args.plain and entry.name == slug)
        if not is_allowed_supersede and (
            entry.name == slug or base_slug == slug or base_slug == requested_base_slug
        ):
            fail(f"duplicate feature slug '{slug}' (conflicts with existing '{entry.name}')")
        seq_match = SEQ_PREFIX_RE.match(entry.name)
        if seq_match:
            existing_prefix = seq_match.group(1)
            if requested_seq_prefix is not None and existing_prefix == requested_seq_prefix:
                fail(
                    f"numeric prefix '{requested_seq_prefix}-' in '{slug}' collides with existing '{entry.name}'"
                )
            max_seq = max(max_seq, int(existing_prefix))

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
        _print_supersede_reminder(supersede_folder)
        return 0

    if is_source_template_repository(ROOT):
        fail(
            "refusing to scaffold feature specs inside the source ai-project-template repository "
            "(install into a target project first, or pass --dry-run to preview)"
        )

    target_dir.mkdir(parents=False, exist_ok=False)
    try:
        for filename, content in ordered_files:
            write_new_file_exclusive(target_dir / filename, content)
    except Exception:
        for child in list(target_dir.iterdir()):
            try:
                child.unlink()
            except OSError:
                pass
        try:
            target_dir.rmdir()
        except OSError:
            pass
        raise

    print(f"OK: scaffolded {rel_target_dir} (preset: {preset_name}, files: {len(ordered_files)})")
    _print_supersede_reminder(supersede_folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
