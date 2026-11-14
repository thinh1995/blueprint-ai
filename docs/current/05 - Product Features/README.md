---
status: active
owner: product
---
# Product Features

Tạo một thư mục đánh số riêng cho mỗi tính năng thực tế của dự án tại đây. Tuyệt đối không đặt các bản mẫu dùng chung hoặc ví dụ minh hoạ vào thư mục này.

## Choosing the right SDD tier

- **Tier M — Mini-Spec (1 file gọn nhẹ):** Dành cho tính năng nhỏ hoặc vừa có **1–2 `AC-xx`**, không bổ sung mô hình dữ liệu bền vững mới hay tích hợp ngoài phức tạp. Khởi tạo từ mẫu `docs/templates/mini-spec-template/` (tuỳ chọn kèm `--preset <general|web-api|cli-tool|ai-agent|security-hardening|<custom>>`) bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug> --mini [--preset <general|web-api|cli-tool|ai-agent|security-hardening|<custom>>]
  ```
- **Tier L — Full Spec Pack (bộ 4 file chuẩn):** Dành cho tính năng có **>= 3 `AC-xx`**, thay đổi schema/API, tích hợp bên thứ ba, phân quyền đa tenant phức tạp, gia cố bảo mật diện rộng hoặc luồng **AI Agent**. Khởi tạo từ mẫu `docs/templates/feature-spec-template/` (tuỳ chọn kèm `--preset <general|web-api|cli-tool|ai-agent|security-hardening|<custom>>`) bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug> [--preset <general|web-api|cli-tool|ai-agent|security-hardening|<custom>>]
  ```
- **Tier S — Bugfix / Hotfix (`/sdd-fix`):** Sửa lỗi hồi quy không phát sinh `AC-xx` mới không cần tạo thư mục tại đây; thực hiện theo quy trình TDD và ghi nhận trực tiếp vào `task-evidence/`.

## Anti-fragmentation and supersession lifecycle

- **Kiểm tra chống phân mảnh trước khi khởi tạo (`Spec Amendment` tại chỗ):** Trước khi chạy `tools/new-feature.py`, bắt buộc kiểm tra các thư mục hiện có trong `05 - Product Features/`. Nếu thay đổi chỉ mở rộng hoặc điều chỉnh hợp đồng của một tính năng sẵn có, hãy thực hiện **Spec Amendment** trực tiếp trên thư mục hiện hữu (phê duyệt lại và làm mới `approved_at` cùng `source_revision` 40 ký tự hex nếu đã `approved`) thay vì tạo thêm thư mục mới gây phân mảnh.
- **Nâng cấp Tier M lên Tier L hoặc thay thế gói cũ (`--supersede`):** Khi một `1. Mini Spec.md` vượt ngưỡng Tier M hoặc cần thiết kế lại toàn diện một gói đặc tả cũ, khởi tạo gói kế nhiệm bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug> --supersede <old-folder>
  ```
  Lệnh này cấp số thứ tự `<NNN-slug>` mới và tự động ghi `supersedes: "05 - Product Features/<old-folder>"` vào YAML frontmatter của gói mới, đồng thời giữ nguyên trạng thái hoạt động của `<old-folder>` trong suốt thời gian gói mới còn ở `status: draft`.
- **Đóng dấu `superseded` nguyên tử tại `/sdd-analyze`:** Ngay khi gói đặc tả mới được người dùng phê duyệt sang `status: approved` trong `/sdd-analyze`, cập nhật nguyên tử toàn bộ file đặc tả trong `<old-folder>` sang `status: superseded` kèm trường `superseded_by` đặt trong dấu ngoặc kép trỏ tới đặc tả kế nhiệm (ví dụ `superseded_by: "[[05 - Product Features/<new-folder>/1. Product Spec]]"` hoặc `"05 - Product Features/<new-folder>/1. Product Spec.md"`, giữ nguyên metadata phê duyệt lịch sử của gói cũ) và kiểm định bằng `python3 tools/validate-docs.py --require-tasks --strict`.

## Scaffolding and approval rules

- Thay thế toàn bộ nội dung giữ chỗ bằng bằng chứng thực tế của dự án theo đúng **Contract Language Rule** (tiêu đề, frontmatter và cột bảng bằng tiếng Anh; nội dung mô tả bằng tiếng Việt tự nhiên).
- Trước khi viết mã nguồn tính năng, toàn bộ file đặc tả trong thư mục tính năng (`1. Mini Spec.md` hoặc cả 4 file `1..4`) phải đồng loạt đạt `status: approved`, không còn thẻ `[NEEDS CLARIFICATION: ...]` hay ô `- [ ]` bỏ trống, điền đủ `approved_by`, `approved_at`, `approval_evidence` kèm mã commit `source_revision` 40 ký tự hex (`git rev-parse HEAD`), và vượt qua `python3 tools/validate-docs.py --require-tasks`.
