# AI Agent & Obsidian Project Template

Current release: `0.1`. See [V1 Acceptance Matrix](V1_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

Đây là thư mục template dùng để khởi tạo nhanh một project mới với cấu trúc chuẩn:
1. **Rule cho AI Agent (`AGENTS.md` và `CLAUDE.md`)**: Định hướng AI Agent tự động tìm kiếm context từ thư mục docs, làm việc dựa trên "evidence-first" và tự động sync docs sau khi code xong. `CLAUDE.md` là entrypoint cho Claude Code; dùng `--with-legacy-agents` nếu tool cần `.agents/AGENTS.md`.
2. **Cấu trúc Obsidian (`docs/current/`)**: Chuẩn "Docs as Code" giúp AI và con người có cùng một Knowledge Base.

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
   Core chỉ cài rule chính và onboarding/overview/architecture (gồm Generated Inventory)/feature specs. Thêm `--with-advanced-docs` cho API, backend, infrastructure và user manual; thêm `--with-legacy-agents` nếu tool của bạn chỉ đọc `.agents/AGENTS.md`.
   Mặc định script giữ nguyên file đã tồn tại, kể cả symlink ở chính file đích. Chỉ dùng `--force` khi bạn chủ động muốn thay thế các file template tương ứng; script sẽ dừng trước khi ghi nếu đường dẫn template có symlink không an toàn hoặc một file nằm tại vị trí cần là thư mục.
   Bạn có thể đặt folder template trong project đích rồi chạy script từ root của project. Tuy nhiên, không chạy script trong chính folder template hoặc thư mục con của template.
3. Sau khi chạy, project mới của bạn sẽ có cấu trúc:
   ```
   AGENTS.md
   CLAUDE.md
   docs/
     └── current/
         ├── 00 - Onboarding/
         ├── 01 - Overview/
         ├── 02 - Architecture/
         ├── 05 - Product Features/
         └── Vault Index MOC.md
   ```
4. Mở thư mục project bằng ứng dụng Obsidian (Open as Vault) để bắt đầu. Các starter note của project được đánh dấu `status: draft`; hãy điền chúng bằng thông tin dự án trước khi coi chúng là source of truth. `AI Agent Workflow` và `Vault Index MOC` là governing notes của template nên có `status: active`. Claude Code sẽ đọc `CLAUDE.md`; các tool khác nên đọc `AGENTS.md` theo convention của chúng.

## Kiểm tra template

Cần Bash và Python 3 (để kiểm tra JSON manifest). Chạy regression test cho installer từ thư mục template:

```bash
bash tests/setup.sh
```

Test bao phủ dry-run, giữ file có sẵn/symlink theo mặc định, `--force`, chặn symlink, bảo vệ hard link và bảo đảm lỗi preflight không để lại cài đặt dở dang.

Template cài `template-manifest.json` để truy vết phiên bản và các đường dẫn được quản lý. Repository template có workflow GitHub tại `.github/workflows/ai-template-validation.yml`, tự chạy syntax check và regression test; nếu mirror template sang CI khác, gọi cùng lệnh `bash tests/setup.sh`.

Project đích nhận `tools/validate-task-evidence.py`; thêm `python3 tools/validate-task-evidence.py` vào CI của project để validate completed task evidence và verified inventory. Với PR behavior-changing đã được phân loại, chạy `python3 tools/validate-task-evidence.py --require-completed` để bắt buộc có completed evidence record.
