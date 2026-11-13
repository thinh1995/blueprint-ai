---
status: draft
owner: engineering
---
# Service Layer

Mô tả các phân hệ nghiệp vụ lõi ở tầng backend, ranh giới giữa các dịch vụ, quản lý giao dịch dữ liệu, tác vụ nền và quy ước xử lý lỗi.

## Module boundaries and domain services

| Service / module | Core domain responsibility | Public interface / entrypoints | Dependencies | Owner |
|---|---|---|---|---|
|  |  |  |  |  |

## Authorization, tenancy, and transaction rules

- Điểm cưỡng chế kiểm tra quyền truy cập và cô lập dữ liệu theo từng tenant:
- Quy ước biên giao dịch cơ sở dữ liệu (transaction boundaries) và phát sự kiện miền (domain events):

## Background jobs, queues, and idempotency

| Job / queue | Trigger / schedule | Idempotency strategy | Retry and dead-letter policy | Owner |
|---|---|---|---|---|
|  |  |  |  |  |

## Error handling and observability

- Quy tắc phân loại lỗi miền nghiệp vụ so với lỗi hạ tầng/tích hợp:
- Chuẩn ghi nhận structured log (không chứa secret/PII), chỉ số giám sát (metrics) và mã truy vết (trace ID):
