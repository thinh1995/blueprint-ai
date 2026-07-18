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

Khi project có công cụ inventory/code intelligence, ghi hoặc liên kết danh sách route, command, permission, queue/scheduler đã được sinh tự động tại đây. Không dùng note này làm source of truth cho đến khi `generated: true`, `verified: true`, `verified_at`, `verified_by`, `verification_method`, `verification_evidence`, `artifact_checksum`, `valid_until`, `generated_at`, `source_revision`, `generation_command`, `artifact_path` và `scope` được điền.

## Verification record

| Field | Required evidence |
|---|---|
| Generated at | Timestamp with timezone |
| Source revision | Commit SHA, release tag, or other immutable source reference |
| Generation command | Exact reproducible command and working directory |
| Artifact path | Path or stable link to the generated output |
| Scope | Included routes, commands, permissions, queues/schedulers and known exclusions |
| Owner | Person/team responsible for refreshing the inventory |

## Inventory

Add generated output or a link to it here. Do not manually curate this section without marking the inventory as non-generated.
