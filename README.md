# AI Agent & Obsidian Project Template

Current release: `0.5.0`. See [V5 Acceptance Matrix](V5_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

Đây là thư mục template dùng để khởi tạo nhanh một project mới với cấu trúc chuẩn:
1. **Rule cho AI Agent (`AGENTS.md` + runtime adapters)**: Định hướng AI Agent tự động tìm kiếm context từ thư mục docs, làm việc dựa trên "evidence-first" và tự động sync docs sau khi code xong. Agent chỉ chọn năng lực có sẵn trên host; delegation được dùng khi phù hợp với công việc độc lập hoặc rủi ro cao, với ownership, evidence và handoff rõ ràng. Khi khởi tạo/refresh docs, host có delegation phải tạo sub-agent chuyên biệt trước khi ghi; host không có capability phải ghi fallback tuần tự. `CLAUDE.md`, `GEMINI.md` (adapter tương thích của Antigravity CLI), và `QWEN.md` là các entrypoint ngắn, cùng trỏ về `AGENTS.md` là nguồn rule canon. Với Gemma/raw API, cấu hình host phải inject [system prompt template](docs/templates/1. Agent System Prompt Template.md); repository file không tự trở thành system prompt.
2. **Cấu trúc Obsidian**: `docs/current/` chỉ chứa tài liệu thực của dự án; `docs/templates/` chứa reusable templates và sample AI Agent để copy khi cần. Mermaid là định dạng sơ đồ chính thức.

## Cách sử dụng cho Project mới

1. Mở Terminal và di chuyển (`cd`) vào thư mục gốc của **project mới** của bạn.
2. Chạy script bằng **đường dẫn thực tế đến folder template** trên máy bạn:
   ```bash
   bash /path/to/ai-project-template/setup.sh
   ```
   Chạy thử trước mà không ghi file:
   ```bash
   bash /path/to/ai-project-template/setup.sh --dry-run
   ```
   Khi chạy trong Terminal, script cho phép chọn nhiều runtime: Claude Code, Antigravity CLI, Qwen Code và Gemma/custom API harness. Nhấn Enter để cài tất cả; dùng `--interactive` khi cần menu trong pipe/PTY. Với automation dùng `--models antigravity,qwen` (hoặc `claude`, `gemma`, `all`) một lần. Core luôn cài `AGENTS.md`; lựa chọn chỉ quyết định các adapter `CLAUDE.md`, `GEMINI.md` (tương thích Antigravity), `QWEN.md` và được merge vào `template-manifest.json` khi chạy incremental setup. Gemma/custom API không có filename adapter: chọn nó sẽ in hướng dẫn để cấu hình host inject system/developer prompt template. Core chỉ cài rule chính và onboarding/overview/architecture (gồm Generated Inventory)/feature specs. Thêm `--with-advanced-docs` cho API, backend, infrastructure và user manual; thêm `--with-legacy-agents` nếu tool của bạn chỉ đọc `.agents/AGENTS.md`.
   Mặc định script giữ nguyên file đã tồn tại, kể cả symlink ở chính file đích. `template-manifest.json` không thuộc template hoặc là symlink cũng được preserve; khi đó installer không cập nhật inventory runtime. Chỉ dùng `--force` khi bạn chủ động muốn thay thế các file template tương ứng; script sẽ dừng trước khi ghi nếu đường dẫn template có symlink không an toàn hoặc một file nằm tại vị trí cần là thư mục. Kiểm tra này giả định không có process khác thay đổi filesystem đích trong lúc setup chạy. Installer dọn temporary file khi bị ngắt, nhưng không cung cấp transaction toàn-vault; nếu bị ngắt sau khi vài file đã được atomically cài, hãy chạy lại setup để hoàn tất.
   Bạn có thể đặt folder template trong project đích rồi chạy script từ root của project. Tuy nhiên, không chạy script trong chính folder template hoặc thư mục con của template.
3. Sau khi chạy, project mới của bạn sẽ có cấu trúc:
   ```
   AGENTS.md
   CLAUDE.md            # Default/all selection only
   GEMINI.md            # Default/all selection only
   QWEN.md              # Default/all selection only
   task-evidence/        # Installed alongside docs/
   tools/
     ├── validate-docs.py
     ├── docs_validation.py
     ├── validate-task-evidence.py
     ├── new-feature.py
     └── export-tasks.py
   docs/
     ├── current/
         ├── 00 - Onboarding/
         ├── 01 - Overview/
         ├── 02 - Architecture/
         ├── 05 - Product Features/
         ├── 08 - Diagram Standards/
         └── Vault Index MOC.md
     └── templates/
         ├── feature-spec-template/   # 1..4 spec pack (Product, Tech, QA, Tasks)
         ├── 1. Agent System Prompt Template.md
         ├── 2. Documentation Subagent Contract.md
         ├── 3. Task Evidence Template.md
         ├── 4. Runtime Delegation Evidence Template.md
         └── examples/ai-support-agent/
   ```
4. Mở thư mục project bằng ứng dụng Obsidian (Open as Vault) để bắt đầu. Các starter note trong `docs/current/` được đánh dấu `status: draft`; hãy điền chúng bằng thông tin dự án trước khi coi chúng là source of truth. Copy material từ `docs/templates/` hoặc chạy `python3 tools/new-feature.py <slug>` (tùy chọn `--preset general|web-api|cli-tool|ai-agent|<custom>`) để tạo pack 4 file tính năng mới (`1. Product Spec.md` .. `4. Tasks.md`); có thể đặt preset mặc định khi cài hoặc nâng cấp bằng `--preset <name>`. Dùng `00 - Onboarding/4. Whole-Project Documentation Update Prompt` để yêu cầu agent tạo/refresh toàn bộ docs từ source hiện hữu, và `00 - Onboarding/6. Spec-Driven Feature Prompts` cho quy trình 6 bước Spec-Driven Development (`Specify -> Clarify -> Plan -> Tasks -> Analyze -> Implement, Converge & Evidence`). Sau khi spec đạt `status: approved`, dùng `python3 tools/export-tasks.py <feature-dir>` để xuất task offline (`json`, `markdown`, `gh-commands`) hoặc `--apply-gh --repo OWNER/REPO` để tạo GitHub Issue idempotent. Đọc `00 - Onboarding/5. Model Runtime Instructions` để xác minh runtime thực sự nạp rule. `docs/internal/` là source-only và không được cài vào project downstream.

## Template upgrade

From the project root, inspect the update before writing:

```bash
bash /path/to/ai-project-template/setup.sh --dry-run --update
bash /path/to/ai-project-template/setup.sh --dry-run --update --migration-plan ai-template-migration-plan.md
bash /path/to/ai-project-template/setup.sh --update
```

- The destination needs a regular, template-owned `template-manifest.json`; symlinked, malformed, or unmanaged manifests are refused.
- The installer derives installed profiles and template-managed adapters, preserves user-owned adapters, and creates `.ai-template-backup.*` with `RECOVERY.md` before replacing each managed file.
- When updating from v0.4.0–v0.4.2, unchanged root template files with the former unnumbered names are backed up and removed after their numbered replacements are installed. User-modified files and symlinks are preserved with an explicit warning.
- A legacy manifest without `managed_profiles` needs explicit `--with-advanced-docs` and/or `--with-legacy-agents` when those profiles should be upgraded. Updates are per-file, not transactional; use `RECOVERY.md` if interrupted.
- Add `--migration-plan report.md` (or `.json`) to the dry run for a shareable list of files to replace, preserve, or resolve manually, plus backup and rollback guidance. It refuses to overwrite an existing report.

## Environment readiness

After setup, run this read-only check from the downstream project root:

```bash
bash /path/to/ai-project-template/setup.sh --doctor
```

It checks Bash/Python, canonical `AGENTS.md`, the selected runtime agents and their adapters (or static adapter delegation and `tests/` tools when run in source-template mode directly inside the template repository), the managed manifest, managed `tools/` scripts, local Markdown documentation links, and Spec/Clarify readiness (`WARN` on legacy 3-file approved packs without `4. Tasks.md`). Each failed check includes a remediation; Gemma/custom harnesses remain `NOT READY` in downstream projects until their host-level system-prompt injection is verified outside the repository.

## Kiểm tra template

Cần Bash và Python 3 (để tạo/kiểm tra JSON manifest). Chạy regression test cho installer từ thư mục template:

```bash
bash tests/setup.sh
```

Test bao phủ dry-run, giữ file có sẵn/symlink theo mặc định, `--force`, chặn symlink, bảo vệ hard link và bảo đảm lỗi preflight không để lại cài đặt dở dang.

Template cài `template-manifest.json` để truy vết phiên bản và các đường dẫn được quản lý. Repository template có workflow GitHub tại `.github/workflows/ai-template-validation.yml`, tự chạy syntax check và regression test; nếu mirror template sang CI khác, gọi cùng lệnh `bash tests/setup.sh`.

Project đích nhận `tools/validate-docs.py`, `tools/validate-task-evidence.py`, `tools/new-feature.py` và `tools/export-tasks.py`. Thêm `python3 tools/validate-docs.py` (`--require-tasks` khi bắt buộc mọi approved feature có `4. Tasks.md`) vào CI để kiểm tra link, Mermaid structure, Clarify Gate và liên thông AC giữa các spec; dùng `python3 tools/validate-task-evidence.py --require-completed` cho PR behavior-changing để bắt buộc có completed evidence record.
