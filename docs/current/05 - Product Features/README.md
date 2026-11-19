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

- **Kiểm tra chống phân mảnh trước khi khởi tạo (`Spec Amendment` tại chỗ):** Trước khi chạy `tools/new-feature.py`, bắt buộc kiểm tra các thư mục hiện có trong `05 - Product Features/`. Nếu thay đổi chỉ mở rộng hoặc điều chỉnh hợp đồng của một tính năng sẵn có, hãy cập nhật trực tiếp trên thư mục hiện hữu thay vì tạo thêm thư mục mới gây phân mảnh; nếu gói đã `status: approved`, trình người dùng phê duyệt lại rồi chạy `python3 tools/stamp-spec.py <feature-folder> --by "<approver>" --evidence "<ref>" --amend` để làm mới `approved_at` cùng `contract_sha256` trên gói `source_revision: self` (hoặc bảo toàn chế độ `source_revision` 40 ký tự hex trên gói cũ trừ khi truyền rõ `--mode self`).
- **Nâng cấp Tier M lên Tier L hoặc thay thế gói cũ (`--supersede`):** Khi một `1. Mini Spec.md` vượt ngưỡng Tier M hoặc cần thiết kế lại toàn diện một gói đặc tả cũ, khởi tạo gói kế nhiệm bằng lệnh:
  ```bash
  python3 tools/new-feature.py <slug> --supersede <old-folder>
  ```
  Lệnh này cấp số thứ tự `<NNN-slug>` mới và tự động ghi `supersedes: "05 - Product Features/<old-folder>"` vào YAML frontmatter của gói mới, đồng thời giữ nguyên trạng thái hoạt động của `<old-folder>` trong suốt thời gian gói mới còn ở `status: draft`.
- **Đóng dấu `superseded` nguyên tử tại `/sdd-analyze`:** Ngay khi gói đặc tả mới được người dùng xác nhận phê duyệt trong `/sdd-analyze`, chạy công cụ đóng dấu nguyên tử:
  ```bash
  python3 tools/stamp-spec.py <new-folder> --by "<approver>" --evidence "<ref>"
  ```
  Công cụ đồng loạt chuyển toàn bộ file của `<new-folder>` sang `status: approved` kèm `source_revision: self` + `contract_sha256` theo mặc định (không cần commit nháp và an toàn qua GitHub Squash & Merge; hoặc ghi mã 40-hex `git rev-parse HEAD` khi truyền `--mode head-sha`), đồng thời tự động chuyển toàn bộ file của `<old-folder>` (khai báo qua `supersedes`) sang `status: superseded` kèm trường `superseded_by` đặt trong dấu ngoặc kép (giữ nguyên metadata phê duyệt lịch sử của gói cũ, tự hoàn tác nếu kiểm định nghiêm ngặt thất bại), sau đó kiểm định lại bằng `python3 tools/validate-docs.py --require-tasks --strict`.

## Scaffolding and approval rules

- Thay thế toàn bộ nội dung giữ chỗ bằng bằng chứng thực tế của dự án theo đúng **Contract Language Rule** (tiêu đề, frontmatter và cột bảng bằng tiếng Anh; nội dung mô tả bằng tiếng Việt tự nhiên).
- Trước khi viết mã nguồn tính năng, toàn bộ file đặc tả trong thư mục tính năng (`1. Mini Spec.md` hoặc cả 4 file `1..4`) phải còn 0 thẻ `[NEEDS CLARIFICATION: ...]` hay ô `- [ ]` bỏ trống, và sau khi người dùng xác nhận duyệt, đóng dấu bằng `python3 tools/stamp-spec.py <feature-folder> --by "<approver>" --evidence "<ref>"` (hỗ trợ `--dry-run` để kiểm thử trước khi ghi) để thiết lập đồng bộ `status: approved`, `approved_by`, `approved_at`, `approval_evidence` kèm `source_revision: self` + `contract_sha256` (hoặc mã commit `source_revision` 40 ký tự hex qua `--mode head-sha`), rồi xác nhận đạt `python3 tools/validate-docs.py --require-tasks --strict`.
- Trong và sau khi triển khai, kiểm soát phạm vi thay đổi bằng máy đối chiếu với cột `Owned paths` đã duyệt qua lệnh `python3 tools/validate-docs.py --require-tasks --strict --check-owned-paths --feature <feature-folder>` (hỗ trợ `--task T-xx` cho lát cắt working-tree/index và `--base <git-rev>` cho phạm vi PR/nhánh).
