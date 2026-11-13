---
status: active
owner: product
---
# Product Features

Tạo một thư mục đánh số riêng cho mỗi tính năng thực tế của dự án tại đây. Tuyệt đối không đặt các bản mẫu dùng chung hoặc ví dụ minh hoạ vào thư mục này.

## Choosing the right SDD tier

- **Tier M — Mini-Spec (1 file gọn nhẹ):** Dành cho tính năng nhỏ hoặc vừa có **1–2 `AC-xx`**, không bổ sung mô hình dữ liệu bền vững mới hay tích hợp ngoài phức tạp. Khởi tạo từ mẫu `docs/templates/mini-spec-template/` bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug> --mini
  ```
- **Tier L — Full Spec Pack (bộ 4 file chuẩn):** Dành cho tính năng có **>= 3 `AC-xx`**, thay đổi schema/API, tích hợp bên thứ ba, phân quyền đa tenant phức tạp hoặc luồng **AI Agent**. Khởi tạo từ mẫu `docs/templates/feature-spec-template/` (tuỳ chọn kèm `--preset <general|web-api|cli-tool|ai-agent|<custom>>`) bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug>
  ```
- **Tier S — Bugfix / Hotfix (`/sdd-fix`):** Sửa lỗi hồi quy không phát sinh `AC-xx` mới không cần tạo thư mục tại đây; thực hiện theo quy trình TDD và ghi nhận trực tiếp vào `task-evidence/`.

## Scaffolding and approval rules

- Thay thế toàn bộ nội dung giữ chỗ bằng bằng chứng thực tế của dự án theo đúng **Contract Language Rule** (tiêu đề, frontmatter và cột bảng bằng tiếng Anh; nội dung mô tả bằng tiếng Việt tự nhiên).
- Trước khi viết mã nguồn tính năng, toàn bộ file đặc tả trong thư mục tính năng (`1. Mini Spec.md` hoặc cả 4 file `1..4`) phải đồng loạt đạt `status: approved`, không còn thẻ `[NEEDS CLARIFICATION: ...]` hay ô `- [ ]` bỏ trống, điền đủ `approved_by`, `approved_at`, `approval_evidence` kèm mã commit `source_revision` 40 ký tự hex (`git rev-parse HEAD`), và vượt qua `python3 tools/validate-docs.py --require-tasks`.
