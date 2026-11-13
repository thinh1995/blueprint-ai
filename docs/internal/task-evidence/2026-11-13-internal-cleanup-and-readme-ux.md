---
status: completed
task_id: internal-cleanup-and-readme-ux
recorded_at: 2026-11-13
recorded_by: Antigravity CLI (soso)
source_revision: 2ccd7a11e6e2a096d70ce0c0638b7a0612b9d204
completed_at: 2026-11-13T13:14:21+0700
reviewer: User approved internal cleanup, README onboarding update, and commit in Antigravity CLI conversation — 2026-11-13
environment: local/dev
output_artifact_sha256: bab2fdb556f445af53fcb08e4e21e1ebaf1289e8ecc34e68f35a692640d12da3
output_artifact_path: README.md
---
# Task Evidence — Internal Evidence Cleanup and README Onboarding Refinement

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-approved request | Antigravity CLI conversation, 2026-11-13 | Approved removing obsolete `docs/internal/runtime-delegation-evidence/` and applying all 6 UX/onboarding refinements to `README.md`. |
| Canonical workspace policy & workflow | `AGENTS.md#L1-L56`; `docs/current/00 - Onboarding/3. AI Agent Workflow.md#L1-L84` at `3168bfa` | Establishes Evidence-First Startup, Simplicity/Surgical rules, Contract Language Rule, and `docs/internal/task-evidence/` provenance gates. |
| Internal evidence & validator contracts | `docs/internal/README.md#L1-L18`; `docs/internal/acceptance-matrices/V4_ACCEPTANCE_MATRIX.md#L12-L18`; `docs/internal/acceptance-matrices/V6_ACCEPTANCE_MATRIX.md#L13`; `tests/validate-runtime-delegation-fixture.py#L31-L45` | Defines internal evidence index, historical link behavior under `setup.sh --doctor`, and `README.md` CI token invariants. |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | Removed obsolete `v0.4.0` `docs/internal/runtime-delegation-evidence/` (`skipped`/`draft` records), updated `docs/internal/README.md`, converted deleted relative links in `V4_ACCEPTANCE_MATRIX.md` to historical code references, and pruned directory scan from `tests/validate-runtime-delegation-fixture.py`. | `bash tests/validate-docs.sh && bash setup.sh --doctor` | PASS / 0 | 2026-11-13 local/dev |
| AC-02 | Upgraded `README.md` for zero-friction onboarding (`git clone` + 1-line interactive default install, initial Git `HEAD` commit & `1. Setup Guide.md` prerequisite notes, 4-step end-to-end chat walkthrough with approval stamping, natural-language fallback tip, downstream `tools/` execution note, and `--interactive` / `--doctor --strict` / CI alignment). | `bash tests/validate-docs.sh && bash setup.sh --doctor && bash tests/render-mermaid.sh --extract-only && python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` | PASS / 0 | 2026-11-13 local/dev |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | `setup.sh --doctor` (`cmd_doctor_links`) walks all non-ignored `.md` files including `docs/internal/acceptance-matrices/V4_ACCEPTANCE_MATRIX.md`, while historical `v0.4.0` completed task evidence verifies `V4_ACCEPTANCE_MATRIX.md` at historical Git commits via `git show <source_revision>:<path>`. | `bash setup.sh --doctor` (`READY`) & `python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` (`PASS`). |
| Assumption | Two-step Git SHA provenance is recorded across `Commit 1` (`2ccd7a11e6e2a096d70ce0c0638b7a0612b9d204` README/internal cleanup/tests) and `Commit 2` (this completed task evidence), so merging branch `v0.6.0` into `master` should use `--no-ff` merge or fast-forward merge (not squash/rebase) to keep Commit 1 reachable for `validate-task-evidence.py`. | Repository two-step provenance convention (`3168bfa`, `eb3d350`). |
| Unknown | Remote GitHub Actions CI run (`@mermaid-js/mermaid-cli` browser rendering on Linux/macOS) pending push. | Local/dev boundary (`render-mermaid.sh --extract-only` verified locally). |

## Safety and completion

- Environment and data-handling check (no secrets/PII in logs or report): `local/dev` only; zero downstream-installed runtime files or templates altered.
- Command output artifact path and SHA-256 (or why unavailable): `README.md`; `bab2fdb556f445af53fcb08e4e21e1ebaf1289e8ecc34e68f35a692640d12da3` at `2ccd7a11e6e2a096d70ce0c0638b7a0612b9d204`.
- Changed files and docs changelog location: deleted `docs/internal/runtime-delegation-evidence/*.md`, updated `docs/internal/README.md`, `docs/internal/acceptance-matrices/V4_ACCEPTANCE_MATRIX.md`, `tests/validate-runtime-delegation-fixture.py`, `README.md`, and finalized this task evidence record.
- Residual risk / rollback: `git revert` the two commits on branch `v0.6.0` if needed.
- Reviewer/sign-off: User approved internal cleanup, README onboarding update, and commit on branch `v0.6.0`, 2026-11-13.
