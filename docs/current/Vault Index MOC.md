---
tags: [moc, documentation, docs-as-code]
status: active
owner: engineering
---
# 🗺️ Vault Index MOC (Map of Content)

Chào mừng bạn đến với **Knowledge Base** của dự án. Tài liệu ở đây được tổ chức theo nguyên tắc "Feature-First" và "Docs as Code". Dưới đây là bản đồ chỉ mục giúp cả con người và AI dễ dàng điều hướng qua các thư mục trong Vault.

## 📁 Kiến trúc Thư mục

- 🚀 **[[00 - Onboarding/1. Setup Guide|00 - Onboarding]]**
  - Chứa hướng dẫn cài đặt môi trường, [[00 - Onboarding/2. Task Evidence|Task Evidence]] và **[[00 - Onboarding/3. AI Agent Workflow|AI Agent Workflow]]** bắt buộc trước task kỹ thuật.

- 📖 **[[01 - Overview/Overview|01 - Overview]]**
  - Cung cấp cái nhìn tổng quan về hệ thống, sơ đồ Use Case và các liên kết quan trọng.

- 🏗️ **[[02 - Architecture/Architecture|02 - Architecture]]**
  - Chứa các tài liệu quyết định kiến trúc hệ thống, mô hình dữ liệu (Data Models).

- 🔌 **03 - API & Integrations** và **04 - Backend & Core**
  - Starter notes nâng cao; cài bằng `--with-advanced-docs` khi project cần API/backend docs riêng, rồi mở `Advanced Docs MOC`.

- 🧩 **`05 - Product Features`** *(Trung tâm dự án)*
  - Thư mục quan trọng nhất, chia nhỏ hệ thống thành các module tính năng độc lập. Mỗi tính năng bao gồm 3 lớp tài liệu chuẩn:
    - **Product Spec**: Yêu cầu nghiệp vụ, User Flow, Mockup.
    - **Tech Spec**: Thiết kế kỹ thuật, Logic code, Database updates.
    - **QA Spec**: Kịch bản kiểm thử (Test cases).
  - Bắt đầu bằng cách copy [[05 - Product Features/_Feature Template/README|Feature Spec Template]] thành folder của feature mới, rồi đổi tên và điền đủ ba lớp tài liệu.

- ☁️ **Infrastructure & Deployment** và 📚 **User Manual & Help Center**
  - Starter notes nâng cao; cài bằng `--with-advanced-docs` khi cần vận hành hoặc hướng dẫn người dùng.

---
*💡 Mẹo dùng Obsidian: Nhấn `Cmd/Ctrl + O` (Mac/Win) và gõ tên file để tìm kiếm & mở file nhanh chóng.*

*Changelog: 2026-07-17 — thêm Feature Spec Template cho Product/Tech/QA specs.*
