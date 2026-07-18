---
status: completed
task_id: mermaid-ci-sandbox-fix
recorded_at: 2026-07-18T15:28:55+07:00
recorded_by: Codex
source_revision: 39b0eeb46144a4563a04bc730c379329c0e04154
completed_at: 2026-07-18T15:40:36+07:00
reviewer: thinh1995
environment: local-and-github-actions
output_artifact_sha256: 38b0daf82a2d252dd08f0294eafc1eba45c91eac16ae54e3b434c3962d61708b
output_artifact_path: CHANGELOG.md
---
# Task Evidence — Mermaid CI Sandbox Fix

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-reported CI failure | Conversation, 2026-07-18 | Authorizes remediation of the GitHub Actions Mermaid render failure. |
| Mermaid CLI documentation | `mermaid-js/mermaid-cli` README, checked 2026-07-18 | Documents `-p` Puppeteer config and the Linux no-sandbox workaround. |
| Current renderer and CI workflow | `tests/render-mermaid.sh`, `.github/workflows/ai-template-validation.yml` | Defines the failing execution path. |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | Ubuntu CI gives Mermaid CLI a Puppeteer config with `--no-sandbox`; macOS keeps the default sandbox behavior. | `MMDC_PUPPETEER_CONFIG=tests/puppeteer-no-sandbox.json npm exec --yes --package=@mermaid-js/mermaid-cli@11.4.2 -- bash tests/render-mermaid.sh` | Pass / 0 | 2026-07-18 |
| AC-02 | Renderer fails clearly if its configured Puppeteer config is absent. | `bash tests/setup.sh` | Pass / 0 | 2026-07-18 |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | GitHub Ubuntu CI failed before rendering because Chromium reported no usable sandbox. | User-provided GitHub Actions log, 2026-07-18. |
| Fact | Mermaid CLI supports a Puppeteer config file through `-p`. | Mermaid CLI README, checked 2026-07-18. |
| Fact | `--no-sandbox` is accepted only for the ephemeral Ubuntu validation runner; macOS retains default browser sandbox behavior. | Reviewer/sign-off: `thinh1995`, 2026-07-18. |
| Fact | The GitHub Actions run after commit `39b0eeb` succeeded. | User-confirmed CI result, 2026-07-18. |

## Safety and completion

- Environment and data-handling check: Local files and ephemeral CI browser only; no secrets or production services.
- Command output artifact path and SHA-256: `CHANGELOG.md`; `38b0daf82a2d252dd08f0294eafc1eba45c91eac16ae54e3b434c3962d61708b`.
- Changed files and docs changelog location: Mermaid renderer, GitHub workflow, `tests/puppeteer-no-sandbox.json`, root changelog.
- Residual risk / rollback: `--no-sandbox` reduces browser isolation on Ubuntu CI; remove the Linux-only config and revert this task if it is not acceptable.
- Reviewer/sign-off: `thinh1995`, after successful GitHub Actions run on 2026-07-18.
