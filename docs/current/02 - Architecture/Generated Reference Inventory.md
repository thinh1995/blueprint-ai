---
status: draft
owner: engineering
generated: false
verified: false
verified_at:
verified_by:
verification_method:
verification_evidence:
artifact_checksum:
valid_until:
generated_at:
source_revision:
generation_command:
artifact_path:
scope:
---
# Generated Reference Inventory

Khi dự án có công cụ quét mã nguồn hoặc trích xuất danh mục tự động, hãy lưu hoặc liên kết danh sách route, lệnh CLI, quyền hạn và hàng đợi/lịch chạy ngầm tại đây. Tuyệt đối không dùng ghi chú này làm nguồn sự thật cho đến khi `generated: true`, `verified: true` và đầy đủ các trường `verified_at`, `verified_by`, `verification_method`, `verification_evidence`, `artifact_checksum`, `valid_until`, `generated_at`, `source_revision`, `generation_command`, `artifact_path`, `scope` đã được điền hợp lệ và chưa hết hạn.

## Verification record

| Field | Required evidence |
|---|---|
| Generated at | Dấu thời gian kèm múi giờ rõ ràng (ISO 8601). |
| Source revision | Mã commit Git đầy đủ hoặc thẻ phát hành bất biến dùng để trích xuất danh mục. |
| Generation command | Câu lệnh tái lập chính xác cùng thư mục làm việc tương ứng. |
| Artifact path | Đường dẫn tương đối trong repo tới tập tin đầu ra được sinh tự động. |
| Scope | Các nhóm route, command, quyền hạn, hàng đợi được quét và những ngoại lệ đã biết. |
| Owner | Cá nhân hoặc nhóm kỹ thuật chịu trách nhiệm làm mới danh mục khi mã nguồn thay đổi. |

## Inventory

Đặt kết quả trích xuất tự động hoặc đường dẫn tới tập tin kết quả tại đây. Không chỉnh sửa tay danh sách bên dưới nếu không đánh dấu lại `generated: false`.
