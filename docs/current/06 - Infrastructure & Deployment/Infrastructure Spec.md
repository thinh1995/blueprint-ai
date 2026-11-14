---
status: draft
owner: engineering
---
# Infrastructure Spec

Ghi lại danh mục môi trường vận hành, quy trình CI/CD, giám sát cảnh báo, triển khai và khôi phục sự cố. Tuyệt đối không ghi thông tin xác thực hoặc khoá bí mật (secrets) vào ghi chú này.

## Environment and ownership

| Environment | Purpose | Access owner | Deployment approval | Data classification |
|---|---|---|---|---|
| Local | Môi trường phát triển và kiểm thử cục bộ mặc định cho lập trình viên và AI Agent. |  | N/A | Dữ liệu giả lập / kiểm thử an toàn |

## Delivery and recovery

| Area | Process / evidence | Owner |
|---|---|---|
| CI checks |  |  |
| Secrets management and security scanning | Quản lý khoá bí mật ngoài Git (secret manager/vault), xoay vòng khoá và cổng quét lộ secret / lỗ hổng phụ thuộc (SCA/SAST) trên CI/CD (không ghi giá trị secret thật). |  |
| Deployment |  |  |
| Observability and alerting |  |  |
| Backup and restore |  |  |
| Rollback trigger and procedure |  |  |
