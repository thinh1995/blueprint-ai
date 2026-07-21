---
tags: [moc, documentation, docs-as-code]
status: active
owner: engineering
---
# 🗺️ Vault Index MOC (Map of Content)

Chào mừng bạn đến với **Knowledge Base** của dự án. Tài liệu ở đây được tổ chức theo nguyên tắc "Feature-First" và "Docs as Code". Dưới đây là bản đồ chỉ mục giúp cả con người và AI dễ dàng điều hướng qua các thư mục trong Vault.

## 📁 Kiến trúc Thư mục

- 🚀 **[[00 - Onboarding/1. Setup Guide|00 - Onboarding]]**
  - Chứa hướng dẫn cài đặt môi trường, [[00 - Onboarding/2. Task Evidence|Task Evidence]], [[00 - Onboarding/4. Whole-Project Documentation Update Prompt|Whole-Project Documentation Update Prompt]], [[00 - Onboarding/5. Model Runtime Instructions|Model Runtime Instructions]] và **[[00 - Onboarding/3. AI Agent Workflow|AI Agent Workflow]]** bắt buộc trước task kỹ thuật.

- 📖 **[[01 - Overview/Overview|01 - Overview]]**
  - Cung cấp cái nhìn tổng quan về hệ thống, BA Foundation và các liên kết quan trọng. Thêm Use Case diagram khi scope thực tế cần làm rõ luồng nghiệp vụ.

- 🏗️ **[[02 - Architecture/Architecture|02 - Architecture]]**
  - Chứa các tài liệu quyết định kiến trúc hệ thống, mô hình dữ liệu (Data Models).

- 📐 **[[08 - Diagram Standards/Diagram Standards|08 - Diagram Standards]]**
  - Mermaid là định dạng sơ đồ chính thức; quy định flow, sequence, state, data boundary và architecture diagrams.

- 🧰 **Advanced Docs MOC**
  - Starter notes API, backend, infrastructure và user manual; cài cùng `--with-advanced-docs` khi project cần các domain này, rồi mở note `Advanced Docs MOC`.

- 🧩 **`05 - Product Features`** *(Trung tâm dự án)*
  - Thư mục quan trọng nhất, chia nhỏ hệ thống thành các module tính năng độc lập. Mỗi tính năng bao gồm 3 lớp tài liệu chuẩn:
    - **Product Spec**: Yêu cầu nghiệp vụ, User Story/Use Case, Business Rule, User Flow, Mockup.
    - **Tech Spec**: Thiết kế kỹ thuật, Logic code, Database updates.
    - **QA Spec**: Kịch bản kiểm thử (Test cases).
  - Tạo folder cho feature thực trong đây. Copy reusable pack từ `docs/templates/feature-spec-template/` rồi đổi tên và điền đủ ba lớp tài liệu.

- 🧰 **`docs/templates/`**
  - Chứa reusable templates và sample; không phải tài liệu thực của dự án. Bắt đầu từ `feature-spec-template/`, `task-evidence-template.md`, `runtime-delegation-evidence-template.md` hoặc `examples/ai-support-agent/`.

---
*💡 Mẹo dùng Obsidian: Nhấn `Cmd/Ctrl + O` (Mac/Win) và gõ tên file để tìm kiếm & mở file nhanh chóng.*
