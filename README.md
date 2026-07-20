# AI Agent & Obsidian Project Template

Current release: `0.3.1`. See [V3.1 Acceptance Matrix](V3_1_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

Đây là thư mục template dùng để khởi tạo nhanh một project mới với cấu trúc chuẩn:
1. **Rule cho AI Agent (`AGENTS.md` + runtime adapters)**: Định hướng AI Agent tự động tìm kiếm context từ thư mục docs, làm việc dựa trên "evidence-first" và tự động sync docs sau khi code xong. `CLAUDE.md`, `GEMINI.md`, và `QWEN.md` là các entrypoint ngắn, cùng trỏ về `AGENTS.md` là nguồn rule canon. Với Gemma/raw API, cấu hình host phải inject [system prompt template](docs/templates/agent-system-prompt-template.md); repository file không tự trở thành system prompt.
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
   Khi chạy trong Terminal, script cho phép chọn nhiều runtime: Claude Code, Gemini CLI, Qwen Code và Gemma/custom API harness. Nhấn Enter để cài tất cả; dùng `--interactive` khi cần menu trong pipe/PTY. Với automation dùng `--models gemini,qwen` (hoặc `claude`, `gemma`, `all`) một lần. Core luôn cài `AGENTS.md`; lựa chọn chỉ quyết định các adapter `CLAUDE.md`, `GEMINI.md`, `QWEN.md` và được merge vào `template-manifest.json` khi chạy incremental setup. Gemma/custom API không có filename adapter: chọn nó sẽ in hướng dẫn để cấu hình host inject system/developer prompt template. Core chỉ cài rule chính và onboarding/overview/architecture (gồm Generated Inventory)/feature specs. Thêm `--with-advanced-docs` cho API, backend, infrastructure và user manual; thêm `--with-legacy-agents` nếu tool của bạn chỉ đọc `.agents/AGENTS.md`.
   Mặc định script giữ nguyên file đã tồn tại, kể cả symlink ở chính file đích. `template-manifest.json` không thuộc template hoặc là symlink cũng được preserve; khi đó installer không cập nhật inventory runtime. Chỉ dùng `--force` khi bạn chủ động muốn thay thế các file template tương ứng; script sẽ dừng trước khi ghi nếu đường dẫn template có symlink không an toàn hoặc một file nằm tại vị trí cần là thư mục. Kiểm tra này giả định không có process khác thay đổi filesystem đích trong lúc setup chạy. Installer dọn temporary file khi bị ngắt, nhưng không cung cấp transaction toàn-vault; nếu bị ngắt sau khi vài file đã được atomically cài, hãy chạy lại setup để hoàn tất.
   Bạn có thể đặt folder template trong project đích rồi chạy script từ root của project. Tuy nhiên, không chạy script trong chính folder template hoặc thư mục con của template.
3. Sau khi chạy, project mới của bạn sẽ có cấu trúc:
   ```
   AGENTS.md
   CLAUDE.md            # Default/all selection only
   GEMINI.md            # Default/all selection only
   QWEN.md              # Default/all selection only
   docs/
     ├── current/
         ├── 00 - Onboarding/
         ├── 01 - Overview/
         ├── 02 - Architecture/
         ├── 05 - Product Features/
         ├── 08 - Diagram Standards/
         └── Vault Index MOC.md
     └── templates/
         ├── feature-spec-template/
         ├── task-evidence-template.md
         └── examples/ai-support-agent/
   ```
4. Mở thư mục project bằng ứng dụng Obsidian (Open as Vault) để bắt đầu. Các starter note trong `docs/current/` được đánh dấu `status: draft`; hãy điền chúng bằng thông tin dự án trước khi coi chúng là source of truth. Copy material từ `docs/templates/` khi tạo feature/evidence; không dùng template hoặc sample làm source of truth. Dùng `00 - Onboarding/4. Whole-Project Documentation Update Prompt` để yêu cầu agent tạo/refresh toàn bộ docs từ source hiện hữu. Đọc `00 - Onboarding/5. Model Runtime Instructions` để xác minh runtime thực sự nạp rule. `docs/internal/` là source-only và không được cài vào project downstream.

## Kiểm tra template

Cần Bash và Python 3 (để tạo/kiểm tra JSON manifest). Chạy regression test cho installer từ thư mục template:

```bash
bash tests/setup.sh
```

Test bao phủ dry-run, giữ file có sẵn/symlink theo mặc định, `--force`, chặn symlink, bảo vệ hard link và bảo đảm lỗi preflight không để lại cài đặt dở dang.

Template cài `template-manifest.json` để truy vết phiên bản và các đường dẫn được quản lý. Repository template có workflow GitHub tại `.github/workflows/ai-template-validation.yml`, tự chạy syntax check và regression test; nếu mirror template sang CI khác, gọi cùng lệnh `bash tests/setup.sh`.

Project đích nhận `tools/validate-docs.py` và `tools/validate-task-evidence.py`. Thêm `python3 tools/validate-docs.py` vào CI để kiểm tra link và Mermaid structure; dùng `python3 tools/validate-task-evidence.py --require-completed` cho PR behavior-changing để bắt buộc có completed evidence record.
