# AI Agent & Obsidian Project Template

Current release: `0.6.0`. See [V6 Acceptance Matrix](docs/internal/acceptance-matrices/V6_ACCEPTANCE_MATRIX.md) and [Changelog](CHANGELOG.md).

> **Dành cho người mới — Bộ khung này là gì?**
> Đây **không phải** là thư viện mã nguồn (như gói `npm` hay `pip`), mà là **bộ quy tắc điều phối chuẩn cho AI Agent kết hợp kho tài liệu dự án Docs-as-Code (GitHub + Obsidian)**. Khi cài đặt vào dự án của bạn, bộ khung giải quyết triệt để 3 bài toán lớn khi lập trình cùng AI:
> 1. **Chống AI tự suy diễn & làm hỏng hệ thống hiện hữu (`AGENTS.md` + 8 runtime adapters):** Buộc AI đọc mã nguồn và tài liệu thực tế trước khi sửa, phân tách minh bạch `Fact / Assumption / Unknown`, chỉ sửa tối giản đúng phạm vi (`Owned paths`) và đồng bộ lại tài liệu khi hành vi thay đổi.
> 2. **Kho tài liệu song ngữ chuẩn hoá máy đọc – người đọc (`docs/current/` & `docs/templates/`):** Giữ 100% tiếng Anh cho cấu trúc máy kiểm định (YAML frontmatter, tiêu đề H1/H2/H3, cột bảng) kết hợp 100% tiếng Việt tự nhiên cho nội dung giải thích, cùng liên kết tương đối mã hoá `%20` hoạt động mượt trên cả GitHub lẫn Obsidian.
> 3. **Quy trình Spec-Driven Development 3 cấp độ linh hoạt (`/sdd-*` & `tools/`):** Trang bị sẵn **8 lệnh tắt `/sdd-*`** (tự động khử trùng lặp qua `.agents/skills/`) và bộ công cụ Python 3 thuần thư viện chuẩn cho cả sửa lỗi nhanh (**Tier S** `/sdd-fix`), tính năng nhỏ 1 file (**Tier M** `--mini`) lẫn gói 4 file đầy đủ (**Tier L**).

---

## 1. Prerequisites

- **Bash** và **Python 3**: Có sẵn trên macOS và hầu hết bản phân phối Linux (hoạt động độc lập 100% bằng thư viện chuẩn, không cần cài gói phụ thuộc ngoài).
- **Git**: Dự án đích cần được khởi tạo Git (`git init`) và có tối thiểu **1 commit nền (`HEAD`)** để đóng dấu mã commit phê duyệt `source_revision` 40 ký tự hex cũng như truy vết bằng chứng kiểm thử.
- **Công cụ AI Agent (hỗ trợ 8 runtimes)**: Claude Code (`claude`), Antigravity CLI (`antigravity`), Qwen Code (`qwen`), OpenCode (`opencode`), OpenAI Codex (`codex`), Cursor (`cursor`), GitHub Copilot (`copilot`) hoặc Gemma/custom API harness (`gemma`). *(Riêng với `gemma` hoặc custom harness, phía host cần tiêm thêm [1. Agent System Prompt Template](docs/templates/1.%20Agent%20System%20Prompt%20Template.md) vì một file nằm trong repo không tự trở thành system prompt).*
- **Ứng dụng [Obsidian](https://obsidian.md)** *(khuyên dùng)*: Chọn `Open folder as vault` ngay tại **thư mục gốc dự án (`.`)** để xem sơ đồ luồng Mermaid và bản đồ liên kết giữa `AGENTS.md`, `task-evidence/` và `docs/`.

---

## 2. Five-minute quickstart

> **Nguyên tắc "Cài 1 lần ở Terminal, vận hành trọn vẹn trong khung AI Chat":** Bạn chỉ cần chạy lệnh cài đặt **1 lần duy nhất** ở Bước 1. Từ Bước 2 trở đi, chỉ cần gõ các lệnh `/sdd-*` ngay trong khung chat AI — chính AI Agent sẽ tự động gọi ngầm bộ công cụ trong `tools/` ở hậu trường.

### Step 1: Clone template and install into your project

Tải bộ khung về một thư mục riêng trên máy (giữ lại thư mục này để dùng cho `--doctor` hoặc nâng cấp `--update` về sau), sau đó `cd` vào **thư mục gốc dự án của bạn** *(không chạy cài đặt ngay bên trong thư mục `ai-project-template`)*:

```bash
# 1. Tải bộ template về máy (chỉ cần làm 1 lần)
git clone https://github.com/thinh1995/blueprint-ai.git ~/ai-project-template

# 2. Di chuyển vào thư mục gốc dự án của bạn (chạy `git init` nếu dự án mới chưa có Git)
cd /duong/dan/du-an-cua-ban

# 3. Cài đặt nhanh (tự động bật menu chọn 1..8 AI runtime; nhấn Enter để cài đủ 7 runtime phổ biến)
bash ~/ai-project-template/setup.sh

# Hoặc cài đặt tuỳ chỉnh sẵn cờ (xem trước với --dry-run, chọn preset & danh sách runtime cố định):
# bash ~/ai-project-template/setup.sh --dry-run --preset web-api --models claude,antigravity,codex,cursor,copilot --with-advanced-docs
# bash ~/ai-project-template/setup.sh --preset web-api --models claude,antigravity,codex,cursor,copilot --with-advanced-docs

# 4. Kiểm tra sức khoẻ cấu hình và tạo commit Git nền đầu tiên (để dự án có mã HEAD SHA)
bash ~/ai-project-template/setup.sh --doctor
git add . && git commit -m "chore: install ai-project-template"
```

> **An toàn tuyệt đối cho dự án đang chạy:** Mặc định `setup.sh` **không bao giờ ghi đè** bất kỳ file nào đã có sẵn trong dự án của bạn. Bạn có thể chọn `--preset` là `general` (mặc định), `web-api`, `cli-tool` hoặc `ai-agent`.

### Step 2: Bootstrap project documentation

Mở công cụ AI Agent (khởi động lại cửa sổ IDE/CLI nếu vừa cài xong để nhận diện các lệnh `/sdd-*`) ngay tại thư mục gốc dự án:
- **Dự án ĐÃ CÓ MÃ NGUỒN:** Gõ `/sdd-docs` (hoặc `/sdd-docs refresh` sau các đợt thay đổi lớn). AI sẽ khảo sát cấu trúc mã nguồn thực tế (tự động điều phối các sub-agent chuyên biệt nếu host hỗ trợ) để điền lệnh chạy vào [1. Setup Guide](docs/current/00%20-%20Onboarding/1.%20Setup%20Guide.md) và hoàn thiện kho `docs/current/` theo [4. Whole-Project Documentation Update Prompt](docs/current/00%20-%20Onboarding/4.%20Whole-Project%20Documentation%20Update%20Prompt.md).
- **Dự án MỚI TINH (chưa có code):** Mở [1. Setup Guide](docs/current/00%20-%20Onboarding/1.%20Setup%20Guide.md) điền trước các lệnh `Run tests` / `Lint` / `Build` dự kiến *(theo quy tắc an toàn, AI sẽ không tự đoán lệnh chạy nếu file này bỏ trống)*, sau đó mở `docs/current/01 - Overview/Overview.md` và `BA Foundation.md` để phác thảo bài toán sản phẩm cùng AI.

### Step 3: Deliver changes with three-tier SDD

Chọn đúng luồng tương ứng với quy mô công việc ngay trong khung chat AI (xem chi tiết tại [6. Spec-Driven Feature Prompts](docs/current/00%20-%20Onboarding/6.%20Spec-Driven%20Feature%20Prompts.md)):

| Tier | Scope and criteria | Slash-command workflow |
|---|---|---|
| **Tier S** | Sửa lỗi hồi quy / hotfix / chỉnh sửa nhỏ (**0 `AC-xx` mới**, không đổi schema hay API công khai). | `/sdd-fix <mô-tả-lỗi>` *(tạo test tái hiện lỗi trước -> sửa tối giản -> ghi `task-evidence/`).* |
| **Tier M** | Tính năng nhỏ/vừa (**1–2 `AC-xx`**, không thêm mô hình dữ liệu bền vững mới hay tích hợp ngoài phức tạp). | `/sdd-specify <slug> --mini` -> `/sdd-clarify` -> `/sdd-analyze` -> *(duyệt)* -> `/sdd-implement` *(1 file `1. Mini Spec.md`).* |
| **Tier L** | Tính năng lớn (**>= 3 `AC-xx`**, đổi schema/API, tích hợp bên thứ ba, đa tenant hoặc **AI Agent**). | `/sdd-specify <slug>` -> `/sdd-clarify` -> `/sdd-plan` -> `/sdd-tasks` -> `/sdd-analyze` -> *(duyệt)* -> `/sdd-implement` *(trọn bộ 4 file `1..4`).* |

### End-to-end chat walkthrough (Tier M example)

Dưới đây là trọn vẹn 4 câu chat thực tế từ lúc nêu ý tưởng đến lúc hoàn thành code & kiểm thử cho một tính năng vừa/nhỏ:

1. **Khởi tạo bản nháp đặc tả:**
   > `/sdd-specify order-status-filter --mini Lọc danh sách đơn hàng theo trạng thái paid/pending trên API GET /orders`
   *(AI tự chạy `tools/new-feature.py order-status-filter --mini` và soạn `docs/current/05 - Product Features/001-order-status-filter/1. Mini Spec.md` ở trạng thái `status: draft`).*
2. **Làm rõ các điểm mơ hồ (nếu có):**
   > `/sdd-clarify`
   *(AI hỏi tối đa 3 câu ngắn gọn cho các góc khuất nghiệp vụ, cập nhật câu trả lời của bạn vào spec và xoá sạch thẻ `[NEEDS CLARIFICATION: ...]`).*
3. **Kiểm định đặc tả trước khi code:**
   > `/sdd-analyze`
   *(AI kiểm tra chéo `AC-xx`, `Owned paths`, chạy `tools/validate-docs.py` và dừng lại báo cáo sẵn sàng chờ bạn phê duyệt).*
4. **Phê duyệt ngay trong chat & triển khai code:**
   > `Tôi phê duyệt spec này (approved_by: thinh). Hãy đóng dấu status: approved kèm HEAD SHA hiện tại (commit bản nháp trước nếu cần), sau đó chạy /sdd-implement.`
   *(AI tự lấy mã commit 40 ký tự hex từ `git rev-parse HEAD` điền vào `source_revision`, kiểm tra `tools/validate-docs.py --strict`, viết code + test đúng trong phạm vi `Owned paths`, cập nhật `Status: done` và tạo báo cáo bằng chứng trong `task-evidence/`).*

> **Mẹo khi khung chat không hiện gợi ý `/sdd-*`:** Hãy reload cửa sổ IDE/CLI để nạp thư mục `.agents/skills/` (hoặc `.claude/skills/`, `.qwen/skills/`). Ngay cả khi bạn tắt skill bằng `--without-skills` hoặc dùng công cụ không hỗ trợ slash command, bạn chỉ cần nhắn bằng tiếng Việt tự nhiên: *"Thực hiện bước 1. Specify (chế độ Mini Spec) theo `docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md` cho tính năng..."*.

---

## 3. Directory layout and setup options

Sau khi chạy `setup.sh`, dự án của bạn được bổ sung các thành phần sau *(các thư mục `docs/internal/`, `lib/` và `tests/` chỉ nằm ở repo phát triển template gốc, không được cài sang dự án của bạn)*:

```text
AGENTS.md                          # Hiến pháp gốc điều hướng mọi AI Agent
CLAUDE.md / GEMINI.md / QWEN.md    # Các file cầu nối mỏng (tuỳ theo --models / --set-models)
.cursor/rules/agents.mdc           # Quy tắc alwaysApply cho Cursor (khi chọn cursor)
.github/copilot-instructions.md    # Hướng dẫn tuỳ chỉnh cho GitHub Copilot (khi chọn copilot)
.claude/skills/sdd-*/SKILL.md      # 8 lệnh tắt /sdd-* cho Claude Code (khi chọn claude)
.agents/skills/sdd-*/SKILL.md      # 8 lệnh tắt /sdd-* dùng chung cho antigravity, opencode, codex, cursor, copilot
.qwen/skills/sdd-*/SKILL.md        # 8 lệnh tắt /sdd-* cho Qwen Code (khi chọn qwen)
template-manifest.json             # Lưu phiên bản, default_preset, requested_models, skills_enabled
task-evidence/                     # Hồ sơ bằng chứng kiểm thử gắn với commit SHA 40 ký tự hex
tools/
  ├── new-feature.py               # Tạo thư mục tính năng 4 file (Tier L) hoặc 1 file --mini (Tier M)
  ├── validate-docs.py             # Kiểm định link, Mermaid, Clarify Gate, --strict SHA & chống sửa trộm sau duyệt
  ├── docs_validation.py           # Thư viện kiểm định Markdown/spec dùng chung
  ├── export-tasks.py              # Xuất công việc từ 4. Tasks.md hoặc 1. Mini Spec.md ra JSON/MD/GitHub Issues
  └── validate-task-evidence.py    # Kiểm định bằng chứng theo git show hoặc --allow-working-tree (cho bản nháp)
docs/
  ├── current/                     # Kho tài liệu thực tế của dự án (Onboarding 1..6, Overview, Architecture, Features...)
  └── templates/                   # Kho mẫu tái sử dụng (feature-spec-template/, mini-spec-template/, examples/)
```

| Option | Purpose |
|---|---|
| `--dry-run` | Xem trước danh sách file sẽ tạo/cập nhật/gỡ bỏ mà không ghi xuống ổ đĩa. |
| `--interactive` | Luôn hiển thị menu chọn `1..8` runtime kể cả khi chạy qua script không tương tác. |
| `--preset <name>` | Đặt `default_preset` mặc định (`general`, `web-api`, `cli-tool`, `ai-agent` hoặc thư mục tuỳ biến trong `docs/templates/presets/<name>/`). |
| `--models <list>` | Chọn cài đặt và cộng dồn công cụ AI runtime (`claude`, `antigravity`, `qwen`, `opencode`, `codex`, `cursor`, `copilot`, `gemma` hoặc `all`). Xem chi tiết tại [5. Model Runtime Instructions](docs/current/00%20-%20Onboarding/5.%20Model%20Runtime%20Instructions.md). |
| `--set-models <list>` | Thay thế chính xác tập runtime đang quản lý (sao lưu & gỡ sạch các adapter/skill cũ do template quản lý không còn nằm trong danh sách mới, vẫn giữ nguyên file người dùng tự sửa). |
| `--without-skills` | Bỏ qua việc cài đặt 8 kỹ năng `/sdd-*` và lưu `"skills_enabled": false` vào `template-manifest.json`. |
| `--with-advanced-docs` | Cài thêm khung tài liệu mở rộng cho API, Service Layer, Infrastructure và User Manual. |
| `--with-legacy-agents` | Tạo thêm bản sao `.agents/AGENTS.md` cho các công cụ đời cũ yêu cầu đường dẫn lồng. |
| `--force` | Chủ động ghi đè các file thuộc quyền quản lý của template (vẫn từ chối đi xuyên qua symlink). |
| `--doctor [--strict]` | Kiểm tra toàn diện môi trường ở chế độ chỉ đọc (`read-only`) kèm hướng dẫn khắc phục; thêm `--strict` để báo lỗi nghiêm ngặt nếu thiếu CLI cục bộ hoặc `source_revision` chưa đủ 40 ký tự hex. |

---

## 4. Three-tier Spec-Driven workflow and CLI tools

Khi bạn làm việc trong khung chat AI, Agent sẽ tự chạy các công cụ bên dưới; bạn cũng có thể gọi trực tiếp trên Terminal hoặc gắn vào pipeline CI/CD của dự án:

```bash
# Chạy tại thư mục gốc dự án ĐÃ CÀI ĐẶT template (không chạy trong kho nguồn ai-project-template)

# Liệt kê các preset có sẵn
python3 tools/new-feature.py --list-presets

# Khởi tạo tính năng Tier M (1 file 1. Mini Spec.md) hoặc Tier L (4 file 1..4)
python3 tools/new-feature.py quick-filter --mini --preset web-api
python3 tools/new-feature.py user-auth --preset web-api

# Kiểm tra liên kết, sơ đồ Mermaid, cổng Clarify, mã SHA 40 ký tự hex (--strict) và độ phủ AC-xx
python3 tools/validate-docs.py --require-tasks
python3 tools/validate-docs.py --require-tasks --strict

# Xuất các task chưa hoàn thành từ gói 4 file hoặc Mini-Spec sau khi đã duyệt (status: approved)
python3 tools/export-tasks.py "docs/current/05 - Product Features/002-user-auth" --format json
python3 tools/export-tasks.py "docs/current/05 - Product Features/002-user-auth" --apply-gh --repo OWNER/REPO

# Kiểm tra hồ sơ bằng chứng ở chế độ nháp trước khi commit hoặc chế độ bắt buộc trên CI
python3 tools/validate-task-evidence.py --allow-working-tree
python3 tools/validate-task-evidence.py --require-completed
```

- **Cổng phê duyệt & Chống sửa ngầm sau phê duyệt (Spec Amendment):** Trước khi chuyển sang `status: approved`, toàn bộ file đặc tả của tính năng phải sạch thẻ `[NEEDS CLARIFICATION: ...]`, sạch ô `- [ ]` mở và đóng dấu `source_revision` bằng mã commit Git 40 ký tự hex thường (`git rev-parse HEAD`). Sau khi đã duyệt, bảng `## Acceptance criteria` cùng các trường `Task ID`, `Owned paths`, `Verification` được khoá bất biến theo commit duyệt đầu tiên; muốn thay đổi hợp đồng phải thực hiện **Spec Amendment** kèm xác nhận duyệt lại và làm mới cả `approved_at` lẫn `source_revision`.

---

## 5. Template upgrade and health check

### Template upgrade

Đứng tại thư mục gốc dự án của bạn và chạy xem trước kế hoạch nâng cấp trước khi áp dụng chính thức:

```bash
bash ~/ai-project-template/setup.sh --dry-run --update
bash ~/ai-project-template/setup.sh --dry-run --update --migration-plan ai-template-migration-plan.md
bash ~/ai-project-template/setup.sh --update
bash ~/ai-project-template/setup.sh --update --set-models claude,antigravity,codex,cursor
```

- **Sao lưu tự động & Bảo toàn tuỳ biến:** Yêu cầu `template-manifest.json` hợp lệ, tự động sao lưu các file cũ vào `.ai-template-backup.*` kèm hướng dẫn khôi phục trong `RECOVERY.md`, và giữ nguyên mọi file adapter/skill/script hoặc custom preset (`docs/templates/presets/`) đã được đội ngũ tuỳ biến riêng.

### Readiness health check

```bash
bash ~/ai-project-template/setup.sh --doctor
bash ~/ai-project-template/setup.sh --doctor --strict
```

Lệnh `--doctor` rà soát phiên bản Bash/Python, `AGENTS.md`, cấu hình của 8 runtime, `template-manifest.json`, bộ công cụ `tools/`, 8 kỹ năng `/sdd-*`, toàn bộ liên kết Markdown nội bộ và tính hợp lệ của các thư mục đặc tả. Mặc định, các CLI runtime chưa cài trên máy cá nhân chỉ hiện cảnh báo `WARN` (`READY`); khi thêm `--strict`, trình kiểm tra sẽ nâng lên mức `FAIL` (`NOT READY`) đối với CLI thiếu, adapter tuỳ biến thiếu tham chiếu `AGENTS.md` hoặc `source_revision` viết tắt (riêng `gemma`/custom harness luôn báo `NOT READY` cho đến khi phía host xác nhận cơ chế tiêm system prompt).

---

## 6. Template development and CI validation

*(Phần này chỉ dành cho người đóng góp phát triển chính kho nguồn `ai-project-template`. Đối với CI dự án của bạn, chỉ cần đưa `python3 tools/validate-docs.py --require-tasks --strict` và `python3 tools/validate-task-evidence.py --require-completed` vào bước kiểm tra Pull Request).*

```bash
bash -n setup.sh tests/setup.sh tests/validate-docs.sh tests/render-mermaid.sh template-paths.sh
bash tests/setup.sh < /dev/null
bash tests/validate-docs.sh
bash setup.sh --doctor
python3 -B tests/validate-antigravity-conformance-fixture.py
python3 -B tools/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed
bash tests/render-mermaid.sh --extract-only
```

GitHub Actions tại `.github/workflows/ai-template-validation.yml` tự động chạy toàn bộ bài kiểm tra hồi quy trên kèm bước biên dịch thực tế toàn bộ sơ đồ Mermaid (`@mermaid-js/mermaid-cli`) trên cả Linux và macOS.
