# AI Agent & Obsidian Project Template

Current release: `0.5.1`. See [V5.1 Acceptance Matrix](docs/internal/acceptance-matrices/V5_1_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

> **Dành cho người mới — Bộ khung này là gì?**
> Đây **không phải** là thư viện code (như gói `npm` hay `pip`), mà là **bộ quy tắc làm việc chuẩn cho AI Agent kết hợp kho tài liệu dự án (Obsidian)**. Khi cài vào dự án của bạn, bộ khung giúp giải quyết 3 vấn đề thường gặp khi lập trình cùng AI:
> 1. **Chống AI tự đoán mò & làm hỏng code cũ (`AGENTS.md` + file adapter):** Buộc AI đọc tài liệu thực tế trước khi sửa, tách bạch rõ điều đã xác minh và điều giả định (`Fact / Assumption / Unknown`), chỉ sửa đúng chỗ cần thiết và tự cập nhật lại tài liệu khi hành vi hệ thống thay đổi.
> 2. **Tài liệu dự án rõ ràng, trực quan (`docs/current/` & `docs/templates/`):** Tách riêng sự thật hiện tại của dự án (`docs/current/`) khỏi các mẫu tái sử dụng (`docs/templates/`), dùng sơ đồ Mermaid chuẩn để dễ đọc trên cả GitHub lẫn ứng dụng Obsidian.
> 3. **Quy trình làm tính năng từng bước bằng lệnh tắt `/sdd-*` & `tools/`:** Cài sẵn **7 lệnh slash `/sdd-*`** (cho Claude Code, Antigravity CLI, Qwen Code) kết hợp các script nhỏ gọn bằng Bash + Python 3 chuẩn (`tools/`) giúp tạo khung đặc tả tính năng, kiểm tra thiếu sót trước khi viết code và xuất danh sách việc sang GitHub Issues.

---

## 1. Cần chuẩn bị gì trước khi bắt đầu? (1 phút)

- **Bash** và **Python 3**: Đã có sẵn trên macOS và hầu hết bản phân phối Linux (không cần cài thêm thư viện ngoài).
- **Git**: Thư mục dự án của bạn nên được khởi tạo sẵn Git (`git init`) để lưu lịch sử và xác nhận phiên bản duyệt tài liệu.
- **Công cụ AI Agent**: Claude Code, Antigravity CLI (Gemini), Cursor, Qwen Code... mở tại thư mục gốc dự án. *(Với Gemma hoặc custom API harness riêng, phía host cần nạp thêm [system prompt template](docs/templates/1.%20Agent%20System%20Prompt%20Template.md) vì file trong repo không tự trở thành system prompt).*
- **Ứng dụng [Obsidian](https://obsidian.md)** *(tuỳ chọn nhưng khuyên dùng)*: Dùng tính năng `Open folder as vault` mở thư mục dự án để xem sơ đồ luồng và liên kết tài liệu trực quan.

---

## 2. Bắt đầu nhanh trong 5 phút (Ví dụ với Dự án Web)

> **Nguyên tắc "Cài 1 lần, dùng 100% trên AI Chat":** Bạn chỉ cần mở Terminal **đúng 1 lần duy nhất** ở Bước 1 để cài bộ khung vào dự án. Từ Bước 2 trở đi, bạn chỉ việc trò chuyện trong khung **AI Chat** — chính AI Agent sẽ tự gọi ngầm các công cụ trong `tools/` ở hậu trường mà bạn không cần chuyển cửa sổ qua lại.

Giả sử bạn đang có một **dự án Web** (hoặc vừa tạo thư mục dự án mới) tại `/duong/dan/du-an-web`:

### Bước 1 (Terminal – 1 phút, làm 1 lần duy nhất): Cài bộ khung vào dự án

Mở Terminal, di chuyển (`cd`) vào **thư mục gốc của dự án Web** *(lưu ý: không chạy lệnh cài đặt ngay bên trong thư mục `ai-project-template` này)*:

```bash
cd /duong/dan/du-an-web

# 1. Xem thử các file sẽ được thêm vào (chưa ghi xuống ổ cứng)
bash /path/to/ai-project-template/setup.sh --dry-run --preset web-api --with-advanced-docs

# 2. Cài đặt chính thức (chọn sẵn mẫu web-api và khung tài liệu API/Backend/Infra)
bash /path/to/ai-project-template/setup.sh --preset web-api --with-advanced-docs

# 3. Kiểm tra môi trường đã sẵn sàng chưa
bash /path/to/ai-project-template/setup.sh --doctor
```

> **An toàn cho dự án hiện có:** Mặc định `setup.sh` **không bao giờ ghi đè** code hay bất kỳ file nào đã tồn tại trong dự án của bạn. Nếu dự án không phải web, bạn có thể đổi `--preset` thành `general`, `cli-tool` hoặc `ai-agent`.

### Bước 2 (AI Chat – 2 phút): Để AI làm quen với dự án (gõ `/sdd-docs`)

Mở công cụ chat AI ngay tại thư mục `/duong/dan/du-an-web`, sau đó chọn đúng trường hợp của bạn:

- **Trường hợp A — Dự án Web ĐÃ CÓ SẴN CODE:** Gõ lệnh tắt trực tiếp trong khung chat (Claude Code, Antigravity CLI, Qwen Code):
  ```text
  /sdd-docs
  ```
  *(Khi cần đồng bộ lại tài liệu sau các đợt thay đổi lớn, gõ `/sdd-docs refresh`. Nếu dùng Gemma, Cursor hoặc trình chat web không tự nạp skill từ repo, chỉ cần nhắn 1 câu: *"Đọc `docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md` và chạy mục First documentation pass cho dự án này."* AI sẽ tự đọc [4. Whole-Project Documentation Update Prompt](docs/current/00%20-%20Onboarding/4.%20Whole-Project%20Documentation%20Update%20Prompt.md), khảo sát cấu trúc code `src/`, `app/`, routes, database... để điền vào `docs/current/` và hỏi lại bạn những chỗ còn chưa rõ).*
- **Trường hợp B — Dự án MỚI TINH (chưa có code):** Mở `docs/current/01 - Overview/Overview.md` (bằng trình soạn thảo hoặc Obsidian) để ghi vài gạch đầu dòng về mục tiêu dự án, hoặc nhờ AI trò chuyện cùng bạn để điền dần bối cảnh ban đầu.

### Bước 3 (AI Chat – 2 phút): Thử làm tính năng đầu tiên bằng bộ lệnh `/sdd-*`

Khi muốn thêm một tính năng mới có thay đổi hành vi hệ thống (ví dụ chức năng đăng nhập `user-auth`), bạn chỉ cần gõ lần lượt các lệnh `/sdd-*` ngay trong **AI Chat** (không cần mở file copy-paste hay tự gõ lại đường dẫn thư mục tính năng ở các bước sau):

1. **Khởi tạo đặc tả yêu cầu (`Specify`):**
   ```text
   /sdd-specify user-auth
   ```
   - *Ở hậu trường:* AI tự chạy `python3 tools/new-feature.py user-auth` (tự động lấy `default_preset` `web-api` đã lưu trong `template-manifest.json`), sinh bộ 4 file nháp (`1. Product Spec.md`, `2. Tech Spec.md`, `3. QA Spec.md`, `4. Tasks.md`) trong `docs/current/05 - Product Features/001-user-auth/`, điền đặc tả và nêu tối đa 3 câu hỏi cần bạn chốt.
2. **Làm rõ, thiết kế, kiểm toán & viết code:** Đi tiếp từng bước bằng lệnh tắt (AI tự nhận diện thư mục tính năng đang làm):
   ` /sdd-clarify ` → ` /sdd-plan ` → ` /sdd-tasks ` → ` /sdd-analyze ` *(xác nhận duyệt bộ spec)* → ` /sdd-implement `
   *(Fallback cho host không hỗ trợ skill: nhắn câu tự nhiên *"Đọc `docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md` và chạy Giai đoạn 1 (Specify) cho `user-auth`"* rồi bảo AI chuyển tiếp sang từng giai đoạn tại [6. Spec-Driven Feature Prompts](docs/current/00%20-%20Onboarding/6.%20Spec-Driven%20Feature%20Prompts.md)).*
3. **AI tự kiểm định trước khi bàn giao:** Ở bước `/sdd-analyze` và `/sdd-implement`, chính AI sẽ đóng dấu mã commit Git khi bạn duyệt, chạy `validate-docs.py --require-tasks` kiểm tra tài liệu và ghi nhận bằng chứng kiểm thử vào `task-evidence/`.

*(Đối với các chỉnh sửa nhỏ chỉ đổi giao diện/định dạng mà không làm thay đổi hành vi nghiệp vụ hay API, bạn có thể nhắn AI sửa trực tiếp theo nguyên tắc tối giản trong [3. AI Agent Workflow](docs/current/00%20-%20Onboarding/3.%20AI%20Agent%20Workflow.md) mà không cần tạo bộ 4 file).*

---

## 3. Cấu trúc thư mục & Các tuỳ chọn cài đặt

Sau khi chạy `setup.sh`, thư mục dự án của bạn sẽ có thêm các thành phần sau *(thư mục `docs/internal/` chỉ nằm ở repo nguồn của template, không được chép sang dự án của bạn)*:

```text
AGENTS.md                   # Bộ quy tắc gốc điều hướng mọi AI Agent
CLAUDE.md / GEMINI.md / ... # Các file cầu nối mỏng trỏ về AGENTS.md (tuỳ theo --models)
.claude/skills/sdd-*/       # 7 lệnh tắt /sdd-* cho Claude Code (khi chọn runtime claude)
.agents/skills/sdd-*/       # 7 lệnh tắt /sdd-* cho Antigravity CLI (khi chọn antigravity)
.qwen/skills/sdd-*/         # 7 lệnh tắt /sdd-* cho Qwen Code (khi chọn qwen)
template-manifest.json      # Ghi nhận phiên bản, preset, skills_enabled và file do template quản lý
task-evidence/              # Nơi lưu bằng chứng kiểm thử cho các thay đổi hành vi
tools/
  ├── new-feature.py        # Tạo nhanh thư mục tính năng 4 file đánh số tự động
  ├── validate-docs.py      # Kiểm tra link, sơ đồ Mermaid và tính khớp nối giữa các file spec
  ├── docs_validation.py    # Thư viện kiểm tra dùng chung cho validate-docs.py
  ├── export-tasks.py       # Xuất danh sách công việc ra JSON/Markdown hoặc GitHub Issues
  └── validate-task-evidence.py
docs/
  ├── current/              # Kho tài liệu thực tế của dự án (Onboarding, Overview, Architecture, Product Features...)
  └── templates/            # Kho mẫu tái sử dụng & ví dụ mẫu (examples/ai-support-agent/)
```

**Bảng tra cứu nhanh các tuỳ chọn của `setup.sh`:**

| Tuỳ chọn | Công dụng |
|---|---|
| `--dry-run` | Xem trước danh sách file sẽ cài hoặc bỏ qua, không ghi xuống đĩa. |
| `--preset <name>` | Đặt mẫu tính năng mặc định (`general`, `web-api`, `cli-tool`, `ai-agent`, hoặc tên thư mục tự tạo trong `docs/templates/presets/<name>/`). |
| `--with-advanced-docs` | Cài thêm khung tài liệu chi tiết cho API, Backend, Infrastructure và User Manual. |
| `--models <list>` | Chọn cài file cầu nối và bộ skill `/sdd-*` cho công cụ AI cụ thể (`claude`, `antigravity`, `qwen`, `gemma`, hoặc `all`). Dùng thêm `--interactive` nếu cần mở menu chọn trong pipe/PTY. Xem chi tiết tại [5. Model Runtime Instructions](docs/current/00%20-%20Onboarding/5.%20Model%20Runtime%20Instructions.md). |
| `--without-skills` | Bỏ qua việc cài đặt 7 bộ skill `/sdd-*` (ghi `"skills_enabled": false` vào `template-manifest.json`; khi dùng kèm `--update` sẽ ngưng quản lý skill mà không xoá file sẵn có trên đĩa). |
| `--with-legacy-agents` | Cài thêm bản sao `.agents/AGENTS.md` cho các công cụ cũ yêu cầu đường dẫn lồng. |
| `--force` | Chủ động ghi đè các file thuộc template (vẫn luôn bảo vệ symlink không bị ghi đè). Nếu cài đặt bị ngắt giữa chừng, chỉ cần chạy lại lệnh để hoàn tất. |
| `--doctor` | Chế độ chỉ đọc (read-only) giúp kiểm tra nhanh sức khoẻ toàn bộ cấu hình, bộ skill `/sdd-*` và tài liệu. |

---

## 4. Quy trình 6 bước làm tính năng (Spec-Driven Development)

Với các tính năng quan trọng trong `docs/current/05 - Product Features/`, bộ khung áp dụng chu trình 6 bước chuẩn (đã có sẵn prompt mẫu tại [6. Spec-Driven Feature Prompts](docs/current/00%20-%20Onboarding/6.%20Spec-Driven%20Feature%20Prompts.md)):

`1. Specify (Chốt yêu cầu)` → `2. Clarify (Làm rõ điểm mơ hồ)` → `3. Plan (Thiết kế Tech & QA)` → `4. Tasks (Chia nhỏ việc)` → `5. Analyze (Kiểm tra & Duyệt)` → `6. Implement, Converge & Evidence (Viết code & Lưu bằng chứng)`

> **Ai là người chạy các lệnh `tools/` dưới đây?** Khi bạn dùng AI Agent trực tiếp tại thư mục dự án (Antigravity, Claude Code, Cursor...), **AI sẽ tự động gọi các lệnh này ở hậu trường**. Bạn chỉ cần tự chạy tay khi muốn kiểm tra độc lập, gắn vào CI/CD (GitHub Actions), hoặc khi dùng trình chat AI trên trình duyệt web không có quyền truy cập thư mục máy tính:

```bash
# Xem các mẫu preset có sẵn
python3 tools/new-feature.py --list-presets

# Khởi tạo bộ 4 file đặc tả tự động đánh số (ví dụ: 001-user-auth)
python3 tools/new-feature.py user-auth --preset web-api

# Kiểm tra link, sơ đồ Mermaid, câu hỏi bỏ ngỏ, độ phủ AC-xx và xung đột chạy song song [P]
python3 tools/validate-docs.py --require-tasks

# Xuất các task chưa làm sau khi bộ spec đã được duyệt (status: approved)
python3 tools/export-tasks.py "docs/current/05 - Product Features/001-user-auth" --format json
python3 tools/export-tasks.py "docs/current/05 - Product Features/001-user-auth" --apply-gh --repo OWNER/REPO

# Kiểm tra bản ghi bằng chứng hoàn thành trong task-evidence/
python3 tools/validate-task-evidence.py --require-completed
```

- **Cổng kiểm duyệt trước khi code (Clarify & Pack-level Approval Gate):** Khi đang nháp (`status: draft`), mỗi file được giữ tối đa `3` câu hỏi `[NEEDS CLARIFICATION: ...]`. Trước khi chuyển sang `status: approved` để bắt đầu code, cả 4 file trong thư mục tính năng phải cùng đạt `approved`, không còn câu hỏi `[NEEDS CLARIFICATION: ...]`, không còn ô `- [ ]` bỏ trống, và điền đủ `approved_by`, `approved_at`, `approval_evidence` cùng mã commit `source_revision` (`git rev-parse HEAD` tại thời điểm duyệt).
- **Tạo mẫu riêng cho nhóm (Custom Presets):** Đặt các file `.md` tuỳ biến của đội ngũ vào `docs/templates/presets/<slug>/`; thư mục này luôn được giữ nguyên khi nâng cấp template.

---

## 5. Nâng cấp phiên bản mới (`--update`) & Kiểm tra sức khoẻ (`--doctor`)

### Nâng cấp Template (`--update` / Template upgrade)

Khi bộ template có phiên bản mới, đứng tại thư mục gốc dự án của bạn và xem trước kế hoạch nâng cấp trước khi áp dụng:

```bash
bash /path/to/ai-project-template/setup.sh --dry-run --update
bash /path/to/ai-project-template/setup.sh --dry-run --update --migration-plan ai-template-migration-plan.md
bash /path/to/ai-project-template/setup.sh --update
```

- **An toàn & Sao lưu tự động:** Yêu cầu dự án có `template-manifest.json` hợp lệ. Trước khi cập nhật, script tự động sao lưu các file cũ vào thư mục `.ai-template-backup.*` kèm hướng dẫn khôi phục trong `RECOVERY.md`.
- **Giữ nguyên tuỳ biến riêng:** Bảo toàn các file adapter, `SKILL.md` tự tạo hoặc script trong `tools/` do bạn tự viết, giữ nguyên `default_preset`, trạng thái `skills_enabled` và các custom preset trong `docs/templates/presets/` (có thể đổi bằng `--update --preset <name>` hoặc tắt quản lý skill bằng `--update --without-skills`). Với các bản cũ `v0.4.0–v0.4.2`, hãy truyền rõ `--with-advanced-docs` hoặc `--with-legacy-agents` nếu muốn nâng cấp kèm các gói đó.
- **Xuất báo cáo di trú (`--migration-plan`):** Ghi chi tiết danh sách file sẽ cập nhật, giữ nguyên hoặc cần xử lý thủ công ra file `.md` hoặc `.json` (không ghi đè nếu file báo cáo đã tồn tại).

### Kiểm tra mức độ sẵn sàng (`--doctor`)

Bất cứ lúc nào muốn kiểm tra xem dự án đã cấu hình đúng chưa, hãy chạy:

```bash
bash /path/to/ai-project-template/setup.sh --doctor
```

Lệnh `--doctor` kiểm tra phiên bản Bash/Python, file `AGENTS.md`, các công cụ AI và file adapter đã chọn, `template-manifest.json`, bộ công cụ `tools/`, các file skill `/sdd-*` do template quản lý, toàn bộ đường dẫn Markdown nội bộ và trạng thái sẵn sàng của các bản spec (chỉ cảnh báo `WARN` với feature 3 file đời cũ chưa có `4. Tasks.md`; riêng Gemma/custom harness sẽ báo `NOT READY` nhắc bạn tự xác nhận cấu hình system prompt ở phía host).

---

## 6. Dành cho người phát triển bộ Template này (Testing & CI)

*(Nếu bạn chỉ cài bộ khung này vào dự án Web của mình, bạn **không cần** chạy phần dưới đây. Gợi ý cho CI dự án của bạn: chỉ cần đưa `python3 tools/validate-docs.py --require-tasks` và `python3 tools/validate-task-evidence.py --require-completed` vào bước kiểm tra Pull Request).*

Để kiểm định chính bộ mã nguồn `ai-project-template` này, chạy trọn bộ bài kiểm tra hồi quy từ thư mục gốc của repo template:

```bash
bash -n setup.sh tests/setup.sh tests/validate-docs.sh tests/render-mermaid.sh template-paths.sh
bash tests/setup.sh < /dev/null
bash tests/validate-docs.sh
python3 -B tests/validate-antigravity-conformance-fixture.py
python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed
```

GitHub Actions tại `.github/workflows/ai-template-validation.yml` tự động chạy toàn bộ các bước kiểm tra trên kèm kiểm định render sơ đồ Mermaid (`@mermaid-js/mermaid-cli`) trên cả Linux và macOS.
