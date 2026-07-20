---
schema_version: 1
status: draft
runtime:
runtime_version:
host:
captured_at:
coordinator:
mode: # delegated | sequential-fallback
capability_check:
delegation_evidence:
---
# Runtime Delegation Evidence

Create one record for a real whole-project documentation initialization or refresh on each runtime/version used for release validation. This is runtime evidence, not a claim that a repository prompt alone created a sub-agent.

## Required fields

- `runtime`, `runtime_version`, `host`, `captured_at`, and `coordinator` identify the tested environment.
- `mode` is `delegated` only if the host created sub-agents; otherwise use `sequential-fallback`.
- `capability_check` records the exact host command, tool inspection, or session control used to determine availability.
- `delegation_evidence` contains a log, task ID, screenshot reference, or host result proving the sub-agent handoff; for a fallback it explains why no delegation was available.

## Role results

| Role | Created / fallback phase | Evidence | Fact / Assumption / Unknown | Conflict decision |
|---|---|---|---|---|
| Source discovery |  |  |  |  |
| Architecture/API |  |  |  |  |
| Product/BA |  |  |  |  |
| QA/traceability |  |  |  |  |

## Completion

Record the final note owner, validation commands/results, and unresolved risk. A host with delegation capability that has no delegation evidence fails this release check.
