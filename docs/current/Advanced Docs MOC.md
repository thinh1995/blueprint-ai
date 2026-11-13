---
status: active
owner: engineering
---
# Advanced Docs MOC

Ghi chú chỉ mục này được cài đặt kèm tuỳ chọn `--with-advanced-docs` khi dự án cần quản lý chi tiết hợp đồng API, tầng dịch vụ lõi, hạ tầng vận hành và tài liệu hướng dẫn người dùng cuối.

## Domain notes

- [[03 - API & Integrations/API Reference|03 - API & Integrations]] — Danh mục API nội bộ/công khai, cơ chế xác thực, định dạng lỗi chuẩn và chính sách tương thích ngược.
- [[04 - Backend & Core/Service Layer|04 - Backend & Core]] — Ranh giới module dịch vụ, quy tắc phân quyền/giao dịch, tác vụ nền (background jobs) và xử lý lỗi.
- [[06 - Infrastructure & Deployment/Infrastructure Spec|06 - Infrastructure & Deployment]] — Danh mục môi trường, quy trình CI/CD, giám sát cảnh báo, sao lưu và kịch bản hoàn tác (rollback).
- [[07 - User Manual & Help Center/User Manual|07 - User Manual & Help Center]] — Hướng dẫn thao tác các luồng chính theo vai trò người dùng, giới hạn đã biết và kênh hỗ trợ.

## Obsidian and contract language rule

- Mở kho tài liệu từ **thư mục gốc dự án (`.`)** trong Obsidian để duy trì liên kết thống nhất với [[Vault Index MOC]], `AGENTS.md` và `task-evidence/`.
- Tuân thủ **Contract Language Rule**: giữ nguyên 100% tiếng Anh cho YAML frontmatter, tiêu đề `#` / `##` / `###` và tiêu đề cột/khoá chuẩn của bảng Markdown; trình bày toàn bộ phần mô tả, quy định và hướng dẫn bằng tiếng Việt tự nhiên.
