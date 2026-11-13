---
status: draft
owner: product
---
# Feature Spec Template

Khởi tạo tính năng mới phức tạp (**Tier L — 4-file Spec Pack**) bằng lệnh `python3 tools/new-feature.py <slug>` (tự động tạo thư mục đánh số trong `docs/current/05 - Product Features/<NNN-slug>/`), hoặc sao chép bốn file mẫu trong thư mục này sang `docs/current/05 - Product Features/<feature-name>/` rồi điền lần lượt theo thứ tự:

1. [1. Product Spec](./1.%20Product%20Spec.md) — bài toán, mục tiêu, user story/use case, quy tắc nghiệp vụ, sơ đồ luồng người dùng và tiêu chí nghiệm thu (`AC-xx`).
2. [2. Tech Spec](./2.%20Tech%20Spec.md) — thiết kế kỹ thuật, phạm vi ảnh hưởng trên hệ thống hiện hữu (brownfield blast radius), sơ đồ tương tác/trạng thái/ranh giới dữ liệu cho AI Agent (khi áp dụng) và ánh xạ `AC-xx`.
3. [3. QA Spec](./3.%20QA%20Spec.md) — kịch bản kiểm thử (`QA-xx`), kiểm thử an toàn AI/prompt injection (khi áp dụng), bằng chứng xác thực và quyền sở hữu bài test.
4. [4. Tasks](./4.%20Tasks.md) — danh mục kiểm tra sẵn sàng trước khi viết code (`Pre-implementation readiness checklist`), phân rã lát cắt dọc MVP và ranh giới `Owned paths` cho thực thi song song.

> **Gợi ý chọn cấp độ (Tier M):** Với tính năng nhỏ/vừa chỉ có 1–2 `AC-xx` và không phát sinh mô hình dữ liệu bền vững mới, bạn có thể chạy `python3 tools/new-feature.py <slug> --mini` để dùng mẫu gọn [1. Mini Spec](../mini-spec-template/1.%20Mini%20Spec.md).

Tuân thủ quy chuẩn vẽ sơ đồ tại [[08 - Diagram Standards/Diagram Standards|Diagram Standards]]. Khi phê duyệt toàn bộ gói đặc tả (`status: approved`), cả bốn file đánh số (`1..4`) phải đồng loạt đạt `approved`, không còn thẻ `[NEEDS CLARIFICATION: ...]` hay ô `- [ ]` bỏ trống, và chỉ đóng dấu `source_revision` bằng mã commit Git (`git rev-parse HEAD`) ngay tại thời điểm duyệt. Không bao giờ coi nội dung giữ chỗ (placeholder) trong mẫu là sự thật của dự án.
