---
status: completed
task_id: acceptance-matrix-reorg-and-readme-localization
recorded_at: 2026-11-12
recorded_by: Antigravity CLI (soso)
source_revision: 4ae6508d1ea77ec1427078adb16118dbb45a6bf4
completed_at: 2026-11-12T13:38:03+0700
reviewer: User approved Option 1 reorganization and README update in Antigravity CLI conversation — 2026-11-12
environment: local/dev
output_artifact_sha256: cef0454ae566b518d2fa3030f79a865a3f1a63c8934873c9a4a4481fbe6f292d
output_artifact_path: tests/validate-template-docs.py
---
# Task Evidence — Acceptance Matrix Reorganization and README Refinement

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-approved request | Antigravity CLI conversation, 2026-11-12 | Approved restructuring `README.md` in Vietnamese (dedicated SDD section + `template-manifest.json` tree entry) and moving all 10 `V*_ACCEPTANCE_MATRIX.md` files into `docs/internal/acceptance-matrices/`. |
| Internal evidence & manifest rules | `docs/internal/README.md#L1-L16`; `template-paths.sh#L88-L94`; `tests/validate-task-evidence.py#L84-L93` at `d5b5e47` | Confirms `docs/internal/` is excluded from downstream installs and historical completed evidence hashes are verified against historical Git commits (`git show <revision>:<path>`). |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | Relocated `V1`..`V5` acceptance matrices to `docs/internal/acceptance-matrices/`, indexed them in `docs/internal/README.md`, updated relative links in `V1`/`V4`, and updated validator/test references. | `bash tests/validate-docs.sh && bash tests/setup.sh < /dev/null` | PASS / 0 | 2026-11-12 local/dev |
| AC-02 | Restructured and localized `README.md` in Vietnamese with a dedicated Spec-Driven Development workflow section and `template-manifest.json` in the installed directory tree while preserving CI guardrail strings and valid local Markdown links. | `bash setup.sh --doctor && python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` | PASS / 0 | 2026-11-12 local/dev |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | `validate-task-evidence.py` verifies `output_artifact_path` via `git show <source_revision>:<path>`, so relocating `V1`..`V5` via `git mv` preserves 100% validation of historical completed evidence records (`v0.1`..`v0.5.0`). | `python3 -B tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` (`PASS`). |
| Assumption | Future release acceptance matrices (`V5_1+`, `V6+`) will live in `docs/internal/acceptance-matrices/` as enforced by `tests/validate-template-docs.py#L51`. | Approved Option 1 convention (2026-11-12). |
| Unknown | Live GitHub Actions CI run on branch `v0.5.0` remains pending until pushed to remote. | Local/dev boundary. |

## Safety and completion

- Environment and data-handling check (no secrets/PII in logs or report): `local/dev` only; zero downstream-installed files altered (only repository-level `README.md`, `docs/internal/**`, and `tests/**`).
- Command output artifact path and SHA-256 (or why unavailable): `tests/validate-template-docs.py`; `cef0454ae566b518d2fa3030f79a865a3f1a63c8934873c9a4a4481fbe6f292d` at `4ae6508d1ea77ec1427078adb16118dbb45a6bf4`.
- Changed files and docs changelog location: `README.md`, `docs/internal/README.md`, `docs/internal/acceptance-matrices/V*_ACCEPTANCE_MATRIX.md`, `tests/{validate-template-docs.py,validate-orchestration-contract.py,validate-docs.sh,setup.sh}`, and this record.
- Residual risk / rollback: `git revert` the reorganization commits on branch `v0.5.0` if needed.
- Reviewer/sign-off: User approved Option 1 reorganization and commit on branch `v0.5.0`, 2026-11-12.
