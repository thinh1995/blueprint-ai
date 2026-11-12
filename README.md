# AI Agent & Obsidian Project Template

Current release: `0.5.0`. See [V5 Acceptance Matrix](docs/internal/acceptance-matrices/V5_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

Bộ template khởi tạo nhanh cấu trúc làm việc chuẩn cho dự án phần mềm kết hợp **AI Agent** và **Obsidian**, xoay quanh 3 trụ cột:

1. **Rule chuẩn hoá cho AI Agent (`AGENTS.md` + runtime adapters)**: Định hướng agent đọc bối cảnh từ `docs/current/`, làm việc theo nguyên tắc **evidence-first** (tách bạch `Fact / Assumption / Unknown`), thay đổi tối giản/surgical và tự động đồng bộ tài liệu khi hành vi hệ thống đổi. `CLAUDE.md`, `GEMINI.md` (adapter tương thích Antigravity CLI) và `QWEN.md` là các entrypoint mỏng trỏ về nguồn rule duy nhất tại `AGENTS.md`. Với Gemma/raw API harness, cấu hình phía host phải nạp [system prompt template](docs/templates/1.%20Agent%20System%20Prompt%20Template.md) vì file trong repo không tự trở thành system prompt.
2. **Kho tri thức Obsidian tách bạch**: `docs/current/` chỉ chứa sự thật hiện hành của dự án; `docs/templates/` chứa các mẫu tái sử dụng và ví dụ AI Agent (`examples/ai-support-agent/`). Mermaid là chuẩn sơ đồ chính thức.
3. **Spec-Driven Development (SDD) không phụ thuộc thư viện ngoài**: Cung cấp sẵn bộ công cụ CLI viết bằng Bash + Python 3 stdlib (`tools/`) để tạo feature pack 4 file, áp đặt cổng kiểm duyệt Clarify/Traceability, kiểm tra an toàn song song `[P]` và xuất task sang GitHub Issues.

---

## Cách sử dụng cho Project mới

1. Mở Terminal và di chuyển (`cd`) vào thư mục gốc của **project đích**.
2. Chạy script cài đặt từ đường dẫn thực tế tới thư mục template:
   ```bash
   # Xem trước các file sẽ được cài mà không ghi xuống đĩa
   bash /path/to/ai-project-template/setup.sh --dry-run

   # Cài đặt mặc định (hiển thị menu chọn runtime nếu chạy trên Terminal)
   bash /path/to/ai-project-template/setup.sh

   # Hoặc cài đặt tự động kèm lựa chọn runtime, preset mặc định và bộ docs nâng cao
   bash /path/to/ai-project-template/setup.sh --models antigravity,claude --preset web-api --with-advanced-docs
   ```
   **Các tuỳ chọn cài đặt chính:**
   - `--models <list>`: Chọn adapter runtime (`claude`, `antigravity` / `gemini`, `qwen`, `gemma`, hoặc `all`). Core luôn cài `AGENTS.md`; tuỳ chọn này chỉ quyết định các file adapter và được ghi nhận vào `template-manifest.json`. Dùng `--interactive` nếu cần ép mở menu trong pipe/PTY.
   - `--preset <name>`: Đặt preset mặc định (`general`, `web-api`, `cli-tool`, `ai-agent` hoặc tên custom preset đã có trong `docs/templates/presets/<name>/`) vào `template-manifest.json`.
   - `--with-advanced-docs`: Cài thêm khung tài liệu API, Backend, Infrastructure và User Manual.
   - `--with-legacy-agents`: Cài thêm bản sao `.agents/AGENTS.md` cho công cụ chỉ đọc đường dẫn lồng.
   - **An toàn mặc định:** Script luôn giữ nguyên các file đã tồn tại (kể cả symlink tại đích hoặc `template-manifest.json` do người dùng tự quản lý). Chỉ truyền `--force` khi bạn chủ động muốn ghi đè. Script kiểm tra preflight toàn bộ đường dẫn trước khi ghi và dọn file tạm nếu bị ngắt (cài đặt theo từng file atomic, nếu gián đoạn chỉ cần chạy lại để hoàn tất).
   - **Lưu ý vị trí chạy:** Có thể đặt thư mục template bên trong project đích rồi chạy từ root của project đích, nhưng **không** chạy lệnh cài đặt/nâng cấp ngay bên trong thư mục template (ngoại trừ chế độ kiểm tra chỉ đọc `setup.sh --doctor`).

3. Cấu trúc thư mục của project sau khi cài đặt:
   ```text
   AGENTS.md
   CLAUDE.md                 # Cài theo lựa chọn --models (mặc định: all)
   GEMINI.md                 # Cài theo lựa chọn --models (mặc định: all)
   QWEN.md                   # Cài theo lựa chọn --models (mặc định: all)
   template-manifest.json    # Theo dõi phiên bản, profile, preset và các đường dẫn được quản lý
   task-evidence/            # Nơi lưu bằng chứng thực thi cho các thay đổi hành vi
   tools/
     ├── validate-docs.py
     ├── docs_validation.py
     ├── validate-task-evidence.py
     ├── new-feature.py
     └── export-tasks.py
   docs/
     ├── current/
     │   ├── 00 - Onboarding/
     │   ├── 01 - Overview/
     │   ├── 02 - Architecture/
     │   ├── 05 - Product Features/
     │   ├── 08 - Diagram Standards/
     │   └── Vault Index MOC.md
     └── templates/
         ├── feature-spec-template/   # Bộ mẫu 4 file (Product, Tech, QA, Tasks)
         ├── 1. Agent System Prompt Template.md
         ├── 2. Documentation Subagent Contract.md
         ├── 3. Task Evidence Template.md
         ├── 4. Runtime Delegation Evidence Template.md
         └── examples/ai-support-agent/
   ```
   *(Thư mục `docs/internal/` chỉ dành riêng cho repo nguồn của template và không được copy sang project đích.)*

4. Mở thư mục project bằng **Obsidian** (`Open folder as vault`):
   - Các note khởi tạo trong `docs/current/` đang ở trạng thái `status: draft`; hãy cập nhật thông tin thực tế của dự án (hoặc dùng [4. Whole-Project Documentation Update Prompt](docs/current/00%20-%20Onboarding/4.%20Whole-Project%20Documentation%20Update%20Prompt.md) để yêu cầu agent khảo sát source code và điền tự động).
   - Đọc [5. Model Runtime Instructions](docs/current/00%20-%20Onboarding/5.%20Model%20Runtime%20Instructions.md) để xác nhận host runtime đã nạp đúng `AGENTS.md` và cơ chế sub-agent delegation.

---

## Quy trình Spec-Driven Development

Từ phiên bản `0.5.0`, mỗi tính năng trong `docs/current/05 - Product Features/` sử dụng bộ spec **4 file** (`1. Product Spec.md`, `2. Tech Spec.md`, `3. QA Spec.md`, `4. Tasks.md`) đi theo 6 bước chuẩn tại [6. Spec-Driven Feature Prompts](docs/current/00%20-%20Onboarding/6.%20Spec-Driven%20Feature%20Prompts.md):

`1. Specify` → `2. Clarify` → `3. Plan` → `4. Tasks` → `5. Analyze` → `6. Implement, Converge & Evidence`

```bash
# 1. Xem danh sách preset có sẵn (general, web-api, cli-tool, ai-agent + custom presets)
python3 tools/new-feature.py --list-presets

# 2. Khởi tạo pack 4 file tự động đánh số (ví dụ: docs/current/05 - Product Features/001-user-auth/)
python3 tools/new-feature.py user-auth --preset web-api

# 3. Kiểm tra link, Mermaid, Clarify Gate, liên thông AC (Product -> Tech -> QA -> Tasks) & xung đột [P]
python3 tools/validate-docs.py --require-tasks

# 4. Sau khi cả pack được duyệt sang status: approved, xuất các task chưa hoàn thành:
python3 tools/export-tasks.py "docs/current/05 - Product Features/001-user-auth" --format json
python3 tools/export-tasks.py "docs/current/05 - Product Features/001-user-auth" --apply-gh --repo OWNER/REPO

# 5. Sau khi code xong và ghi nhận bằng chứng vào task-evidence/, kiểm tra tính toàn vẹn:
python3 tools/validate-task-evidence.py --require-completed
```

- **Clarify & Pack-level Approval Gate:** Khi `status: draft`, mỗi file được phép giữ tối đa `3` đánh dấu `[NEEDS CLARIFICATION: ...]`. Khi chuyển sang `status: approved`, toàn bộ các file số thứ tự trong thư mục tính năng phải cùng đạt `approved`, sạch `0` đánh dấu nghi vấn, `0` checkbox `- [ ]` bỏ ngỏ và điền đủ `approved_by`, `approved_at`, `approval_evidence` cùng `source_revision` tại thời điểm duyệt (`git rev-parse HEAD`).
- **Custom Presets cho đội ngũ:** Tạo thư mục `docs/templates/presets/<slug>/` chứa các file `.md` muốn ghi đè lên mẫu chuẩn; thư mục này được bảo toàn nguyên vẹn qua các lần chạy `setup.sh --update`.

---

## Nâng cấp Template (`--update`)

Từ thư mục gốc của project đang dùng bản cũ, kiểm tra kế hoạch nâng cấp trước khi ghi:

```bash
bash /path/to/ai-project-template/setup.sh --dry-run --update
bash /path/to/ai-project-template/setup.sh --dry-run --update --migration-plan ai-template-migration-plan.md
bash /path/to/ai-project-template/setup.sh --update
```

- **Điều kiện tiên quyết:** Project đích phải có `template-manifest.json` hợp lệ thuộc quyền quản lý của template (manifest bị symlink, sai cấu trúc hoặc user-owned sẽ bị từ chối để tránh ghi đè nhầm).
- **Sao lưu & Khôi phục:** Trước khi thay thế từng file do template quản lý, script tự tạo thư mục `.ai-template-backup.*` kèm hướng dẫn khôi phục tại `RECOVERY.md`.
- **Bảo toàn tuỳ biến của người dùng:** Tự động giữ nguyên các adapter do người dùng tự tạo, bảo toàn độc lập `tools/new-feature.py` hoặc `tools/export-tasks.py` nếu dự án đã có sẵn file tự viết cùng tên, đồng thời giữ nguyên `default_preset` và các custom preset trong `docs/templates/presets/` (có thể đổi preset mặc định bằng `--update --preset <name>`).
- **Tương thích các bản cũ (`v0.4.0–v0.4.2`):** Các file mẫu gốc chưa sửa đổi mang tên cũ (chưa đánh số) sẽ được sao lưu và dọn dẹp sau khi cài bản đánh số mới; nếu người dùng đã chỉnh sửa thì file cũ được giữ lại kèm cảnh báo. Với manifest cũ chưa có trường `managed_profiles`, hãy truyền rõ `--with-advanced-docs` và/hoặc `--with-legacy-agents` nếu muốn nâng cấp các profile đó.
- **Báo cáo di trú (`--migration-plan`):** Xuất danh sách chi tiết các file sẽ thay thế, giữ nguyên hoặc cần xử lý thủ công ra `.md` hoặc `.json` (không ghi đè nếu file báo cáo đã tồn tại).

---

## Kiểm tra mức độ sẵn sàng (`--doctor`)

Chạy kiểm tra chỉ đọc (read-only) tại thư mục gốc của project đích — hoặc chạy trực tiếp ngay trong thư mục repo template:

```bash
bash /path/to/ai-project-template/setup.sh --doctor
```

Lệnh `--doctor` xác minh phiên bản Bash/Python, file chuẩn `AGENTS.md`, các runtime CLI và adapter đã chọn (hoặc kiểm tra static adapter và bộ script trong `tests/` khi chạy trực tiếp trên repo template), tính hợp lệ của `template-manifest.json`, các công cụ trong `tools/`, toàn bộ đường dẫn Markdown cục bộ và cổng **Spec/Clarify readiness** (chỉ phát cảnh báo `WARN` thay vì `FAIL` đối với các feature 3 file đời cũ chưa có `4. Tasks.md`). Các project chọn Gemma/custom harness sẽ giữ trạng thái `NOT READY` cho tới khi xác minh việc nạp system prompt ở tầng host bên ngoài repo.

---

## Kiểm tra & CI cho Template

Để phát triển hoặc kiểm định chính bộ template này (yêu cầu Bash và Python 3), chạy đầy đủ các bài kiểm tra hồi quy từ thư mục gốc của template:

```bash
bash -n setup.sh tests/setup.sh tests/validate-docs.sh tests/render-mermaid.sh template-paths.sh
bash tests/setup.sh < /dev/null
bash tests/validate-docs.sh
python3 -B tests/validate-antigravity-conformance-fixture.py
python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed
```

- Bộ test trong `tests/setup.sh` kiểm tra toàn diện `--dry-run`, bảo toàn file/symlink mặc định, `--force`, chặn symlink/hard-link traversal, rollback preflight, nâng cấp `--update`, presets, scaffolder, exporter (với mock `gh` offline) và `--doctor`.
- Workflow GitHub Actions tại `.github/workflows/ai-template-validation.yml` tự động chạy toàn bộ các bước trên kèm kiểm tra render sơ đồ Mermaid (`@mermaid-js/mermaid-cli`) trên cả Linux và macOS.
- **Gợi ý cho CI của project đích:** Đưa `python3 tools/validate-docs.py` (thêm `--require-tasks` nếu bắt buộc mọi feature đã duyệt phải có `4. Tasks.md`) và `python3 tools/validate-task-evidence.py --require-completed` vào pipeline kiểm tra Pull Request.
