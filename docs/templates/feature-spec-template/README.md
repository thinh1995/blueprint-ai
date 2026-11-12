---
status: draft
owner: product
---
# Feature Spec Template

Khởi tạo feature mới bằng `python3 tools/new-feature.py <slug>` (mặc định scaffold 4 file spec đánh số vào `docs/current/05 - Product Features/<NNN-slug>/`) hoặc copy từ folder này vào `docs/current/05 - Product Features/<feature-name>/`, rồi điền bốn note theo thứ tự:

1. [[1. Product Spec]] — mục tiêu, user story/use case, business rules, user flow và acceptance criteria.
2. [[2. Tech Spec]] — thiết kế, brownfield blast radius, agent/data flow khi phù hợp, và AC mapping.
3. [[3. QA Spec]] — test cases, AI-agent safety coverage khi phù hợp, evidence và validation tương ứng.
4. [[4. Tasks]] — checklist sẵn sàng trước khi code (`Pre-implementation readiness checklist`), vertical MVP slices và ranh giới `Owned paths` cho thực thi song song.

Tham chiếu `docs/current/08 - Diagram Standards/Diagram Standards.md`. Điền owner, status và các liên kết giữa bốn note. Khi phê duyệt cả pack (`status: approved`), tất cả các file spec đánh số hiện có (`1..4`) phải đồng loạt đạt `approved`, không còn `[NEEDS CLARIFICATION: ...]` hay mục `- [ ]` mở, và chỉ đóng dấu `source_revision` (`git rev-parse HEAD`) tại thời điểm phê duyệt. Không coi nội dung placeholder là source of truth.
