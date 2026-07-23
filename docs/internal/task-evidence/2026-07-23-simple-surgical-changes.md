---
status: completed
task_id: 2026-07-23-simple-surgical-changes
recorded_at: 2026-07-23
recorded_by: Codex /root
source_revision: 107f83334697d57c76e99a88c5f8367701899ac7
completed_at: 2026-07-23T15:53:46+0700
reviewer: User requested review and completion in Codex conversation — 2026-07-23
environment: local/dev
output_artifact_sha256: f5a4b5dbcab9c5cb1b8871216c9e927c450d4cb6cb707dfae25968d59acee30a
output_artifact_path: AGENTS.md
---
# Task Evidence — Simplicity First and Surgical Changes

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-approved requirement | Codex conversation, 2026-07-23 | Directly requires the two policy principles. |
| Existing workspace policy | `AGENTS.md`; `docs/current/00 - Onboarding/3. AI Agent Workflow.md` at `81b34ebf526f3912224541586cd2f7be97b08e31` | Defines the evidence-first policy and documentation-sync requirements that this change extends. |
| Validation contract | `tests/validate-docs.sh` at `81b34ebf526f3912224541586cd2f7be97b08e31` | Existing documentation validation entry point, extended to check the new policy text. |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | Canonical policy prohibits speculative abstractions or features beyond approved scope. | `bash tests/validate-docs.sh` | PASS / 0 | 2026-07-23 local/dev |
| AC-02 | Canonical policy prohibits unrelated refactors, deletions, formatting, and comment edits while preserving cleanup of artifacts caused by the current change. | `bash tests/validate-docs.sh` | PASS / 0 | 2026-07-23 local/dev |
| AC-03 | Onboarding workflow documents both principles for agents and human reviewers. | `bash tests/validate-docs.sh` | PASS / 0 | 2026-07-23 local/dev |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | `AGENTS.md` is the canonical workspace policy, and the onboarding workflow is its required evidence-first companion for behavior-changing work. | `AGENTS.md`; `docs/current/00 - Onboarding/3. AI Agent Workflow.md`. |
| Assumption | The requested principles should apply to all supported runtimes through the canonical policy, rather than only Claude Code. | Root adapters point to `AGENTS.md`; user can refine runtime-specific scope. |
| Unknown | Remote CI has not run. | Local validation passed; remote CI result must not be claimed. |

## Safety and completion

- Environment and data-handling check (no secrets/PII in logs or report): local/dev only; no external service, deployment, or destructive action.
- Command output artifact path and SHA-256 (or why unavailable): `AGENTS.md`; `f5a4b5dbcab9c5cb1b8871216c9e927c450d4cb6cb707dfae25968d59acee30a` at `107f83334697d57c76e99a88c5f8367701899ac7`.
- Changed files and docs changelog location: `AGENTS.md`, `docs/current/00 - Onboarding/3. AI Agent Workflow.md`, `tests/validate-docs.sh`, and this task evidence record; v0.4.4 release notes in `CHANGELOG.md` include the policy guardrails.
- Residual risk / rollback: The guidelines require judgment on what is related to a requested outcome; revert this scoped policy/documentation/test change if needed.
- Reviewer/sign-off: User requested review and completion in Codex conversation, 2026-07-23.
