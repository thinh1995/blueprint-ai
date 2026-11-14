---
tags: [moc, documentation, docs-as-code]
status: active
owner: engineering
---
# Vault Index MOC

Chào mừng bạn đến với kho tri thức (**Knowledge Base**) của dự án. Toàn bộ ghi chú tại đây được tổ chức theo nguyên tắc **Docs as Code** và **Evidence-First** để cả con người lẫn AI Agent đều có thể tra cứu, đối chiếu và cập nhật nhất quán trên cả GitHub và Obsidian.

## Obsidian workspace and contract language rule

- **Mở kho tài liệu ở thư mục gốc dự án (`.`):** Trong ứng dụng Obsidian, hãy chọn `Open folder as vault` ngay tại **thư mục gốc của repository (`.`)** thay vì chỉ mở thư mục con `docs/`. Cách mở này giúp liên kết hai chiều giữa `AGENTS.md`, `task-evidence/`, `docs/current/` và `docs/templates/` hiển thị đầy đủ trên sơ đồ liên kết mà không lệch đường dẫn tương đối với GitHub.
- **Quy tắc ngôn ngữ hợp đồng (Contract Language Rule):**
  - **100% tiếng Anh cho cấu trúc máy đọc:** toàn bộ khoá và giá trị trạng thái YAML frontmatter (`status: draft | approved | example | superseded | archived | active | template`, `owner`, `supersedes`, `superseded_by`, `approved_by`, `approved_at`, `approval_evidence`, `source_revision`...), mọi tiêu đề `#` / `##` / `###`, tiêu đề cột bảng Markdown và các khoá dòng chuẩn (`Task ID`, `Status`, `[P]`, `Owned paths`, `Verification`, `AC-xx`, `QA-xx`, `T-xx`, `SEC-xx`...). Mọi ghi chú hoặc đặc tả trong `docs/current/**` mang `status: superseded` bắt buộc phải khai báo trường `superseded_by` đặt trong dấu ngoặc kép trỏ tới ghi chú/đặc tả kế nhiệm đang hoạt động (ví dụ `superseded_by: "[[05 - Product Features/<new-folder>/1. Product Spec]]"` hoặc đường dẫn `.md` tương đối).
  - **100% tiếng Việt tự nhiên cho nội dung con người đọc:** toàn bộ phần giải thích, hướng dẫn, danh mục kiểm tra, nội dung ô mô tả trong bảng, ví dụ minh hoạ và các khối prompt nghiệp vụ.

## Directory architecture

- **[[00 - Onboarding/1. Setup Guide|00 - Onboarding]]** — Cổng khởi động bắt buộc cho thành viên mới và AI Agent:
  - [1. Setup Guide](./00%20-%20Onboarding/1.%20Setup%20Guide.md): cấu trúc mã nguồn, lệnh build/lint/test/quét bảo mật đã xác minh, nâng cấp template và kiểm tra `--doctor`.
  - [2. Task Evidence](./00%20-%20Onboarding/2.%20Task%20Evidence.md): quy tắc lưu trữ và kiểm định bằng chứng kiểm thử theo mã commit Git.
  - [3. AI Agent Workflow](./00%20-%20Onboarding/3.%20AI%20Agent%20Workflow.md): quy trình làm việc dựa trên bằng chứng, phân luồng 3 cấp độ SDD (`Tier S / M / L`), sửa đổi/thay thế đặc tả (`Spec Amendment` / `--supersede`) và phân luồng bảo mật brownfield (`SEC-xx`).
  - [4. Whole-Project Documentation Update Prompt](./00%20-%20Onboarding/4.%20Whole-Project%20Documentation%20Update%20Prompt.md): prompt chuẩn khởi tạo hoặc làm mới toàn bộ `docs/current/` (`/sdd-docs`).
  - [5. Model Runtime Instructions](./00%20-%20Onboarding/5.%20Model%20Runtime%20Instructions.md): cấu hình adapter, bộ kỹ năng `.agents/skills/` và kiểm tra sub-agent cho 8 công cụ AI runtime.
  - [6. Spec-Driven Feature Prompts](./00%20-%20Onboarding/6.%20Spec-Driven%20Feature%20Prompts.md): bộ prompt 7 giai đoạn (`/sdd-specify` .. `/sdd-implement` và `/sdd-fix`).
- **[[01 - Overview/Overview|01 - Overview]]** — Tầm nhìn sản phẩm, phạm vi hệ thống và nền tảng phân tích nghiệp vụ tại [[01 - Overview/BA Foundation|BA Foundation]].
- **[[02 - Architecture/Architecture|02 - Architecture]]** — Ranh giới hệ thống, mô hình dữ liệu, quyết định kiến trúc, sổ đăng ký triage bảo mật/nợ kỹ thuật brownfield (`SEC-xx`) và danh mục tự động tại [[02 - Architecture/Generated Reference Inventory|Generated Reference Inventory]].
- **[[05 - Product Features/README|05 - Product Features]]** — Thư mục trung tâm chứa đặc tả của từng tính năng thực tế trong dự án:
  - **Tier M (`1. Mini Spec.md`):** tạo bằng `python3 tools/new-feature.py <slug> --mini` cho tính năng gọn (1–2 `AC-xx`).
  - **Tier L (`1. Product Spec.md` .. `4. Tasks.md`):** tạo bằng `python3 tools/new-feature.py <slug>` cho tính năng lớn, tích hợp ngoài, thay đổi schema/API, gia cố bảo mật (`--preset security-hardening`) hoặc AI Agent; dùng `--supersede <old-folder>` khi nâng cấp từ Tier M hoặc thay thế gói đặc tả cũ.
- **[[08 - Diagram Standards/Diagram Standards|08 - Diagram Standards]]** — Quy chuẩn vẽ sơ đồ Mermaid cho luồng nghiệp vụ, chuỗi tương tác, máy trạng thái và mô hình dữ liệu.
- **Advanced Docs (`--with-advanced-docs`)** — Khung tài liệu mở rộng cho API, tầng dịch vụ, hạ tầng triển khai và cẩm nang người dùng; khi dự án cài gói này, mở ghi chú `Advanced Docs MOC` để điều hướng.

## Templates and evidence

- **`docs/templates/`** — Kho mẫu tái sử dụng và bộ ví dụ minh hoạ (`feature-spec-template/`, `mini-spec-template/`, `examples/ai-support-agent/`, `3. Task Evidence Template.md`, `4. Runtime Delegation Evidence Template.md`); tuyệt đối không coi nội dung trong `docs/templates/` là sự thật hiện hành của dự án.
- **`task-evidence/`** (ở thư mục gốc dự án) — Nơi lưu hồ sơ bằng chứng thực thi và kiểm thử cho từng nhiệm vụ có làm thay đổi hành vi hệ thống.

---
*Mẹo dùng Obsidian: Nhấn `Cmd/Ctrl + O` để tìm và mở nhanh bất kỳ ghi chú nào trong kho tài liệu.*
