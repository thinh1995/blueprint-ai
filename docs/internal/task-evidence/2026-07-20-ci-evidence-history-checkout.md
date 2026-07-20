---
status: completed
task_id: ci-evidence-history-checkout
recorded_at: 2026-07-20
recorded_by: thinh1995
source_revision: 96bd76eb683d147f7f72b03cff5d178ae7eeae95
completed_at: 2026-07-20T11:12:00+0700
reviewer: thinh1995
environment: local/dev
output_artifact_sha256: 18ef434a699295315d59ddc981c2a79997447e2f59acde03376a353123126a19
output_artifact_path: .github/workflows/ai-template-validation.yml
---
# Task Evidence — CI evidence-history checkout

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-reported GitHub Actions failure | 2026-07-20 conversation; `git rev-parse` could not resolve `c723283…` | Authorizes the CI hotfix. |
| CI workflow | `.github/workflows/ai-template-validation.yml` | Defines the checkout and validation commands that failed. |
| Evidence validator | `tests/validate-task-evidence.py` | Requires every completed record's `source_revision` to resolve to a commit. |
| Task-evidence guidance | `docs/current/00 - Onboarding/2. Task Evidence.md` | Requires completed evidence revisions to remain available through Git. |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | CI checkout fetches full repository history before verifying immutable task-evidence revisions. | `bash tests/validate-docs.sh` (asserts `fetch-depth: 0`), manual review of workflow checkout step | Pass / 0 | 2026-07-20 local/dev |
| AC-02 | Existing installer, downstream docs, and task-evidence validation remain green. | `bash tests/setup.sh && python3 tests/validate-project-docs.py && python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed && git diff --check` | Pass / 0 | 2026-07-20 local/dev |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | `actions/checkout` previously had no `fetch-depth` input, while the validator resolves historical evidence commits. | Files above; user-provided CI traceback. |
| Fact | The workflow now configures `fetch-depth: 0`. | `.github/workflows/ai-template-validation.yml` at `96bd76e`. |
| Assumption | GitHub Actions `actions/checkout` honours the configured full-history fetch in the hosted runner. | Configuration follows the action contract; next GitHub Actions run confirms it. |
| Unknown | The result of the next remote GitHub Actions run. | Check the run after this commit is pushed. |

## Safety and completion

- Environment and data-handling check (no secrets/PII in logs or report): local/dev only; no external services called and no secrets handled.
- Command output artifact path and SHA-256: `.github/workflows/ai-template-validation.yml`; `18ef434a699295315d59ddc981c2a79997447e2f59acde03376a353123126a19` from source revision `96bd76eb683d147f7f72b03cff5d178ae7eeae95`.
- Changed files and docs changelog location: `.github/workflows/ai-template-validation.yml`, `tests/validate-docs.sh`; this evidence record documents the CI behavior change.
- Residual risk / rollback: full history increases checkout time and bandwidth. Revert commit `96bd76e` only if CI resource impact is unacceptable; historical evidence validation will then again require another history strategy.
- Reviewer/sign-off: thinh1995.
