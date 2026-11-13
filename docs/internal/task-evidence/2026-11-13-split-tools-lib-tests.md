---
status: completed
task_id: split-tools-lib-tests
recorded_at: 2026-11-13
recorded_by: Antigravity CLI (soso)
source_revision: 789e2d653d50fd0065e5a11be9167c39b1524697
completed_at: 2026-11-13T13:46:40+0700
reviewer: User approved Option A1 layout split, GitHub Actions CI updates, and commit in Antigravity CLI conversation — 2026-11-13
environment: local/dev
output_artifact_sha256: 93f1ec3779bf6be482f706c4910caddfb8bf3bd99827f9400369ad7e040d490e
output_artifact_path: lib/installer_lib.py
---
# Task Evidence — 3-Layer Source Layout Split (`tools/`, `lib/`, `tests/`)

## Authority and sources read

| Source | Revision / file:line | Why it is authoritative |
|---|---|---|
| User-approved request | Antigravity CLI conversation, 2026-11-13 | Explicitly selected Option A1 (`tách sạch tools/ + lib/installer_lib.py + tests/`) and approved optimizing `.github/workflows/ai-template-validation.yml` (`push` scoped to `master`, PRs, `workflow_dispatch`, `concurrency`, AST syntax check, and `setup.sh --doctor`). |
| Canonical workspace policy & workflow | `AGENTS.md#L1-L56`; `docs/current/00 - Onboarding/3. AI Agent Workflow.md#L1-L84` at `338b6bf6a86f68bfac04911e0646ddcd75c92f96` | Establishes Evidence-First Startup, Simplicity/Surgical rules, symlink prohibitions, and `docs/internal/task-evidence/` provenance gates. |
| Installer, tools, skills, and test contracts | `lib/installer_lib.py#L124-L162`; `setup.sh#L65-L89`; `template-paths.sh#L7-L14`; `tools/new-feature.py#L74-L90`; `tests/setup.sh#L438-L545`; `tests/validate-docs.sh#L80-L105` | Defines source-to-downstream path mappings, `PRIOR_TEMPLATE_SHA256S` deselection hashes, `--doctor` checks, and CI test suite boundaries. |

## Acceptance criteria and validation

| AC | Change / implementation | Test or validation command | Result / exit code | Run at |
|---|---|---|---|---|
| AC-01 | Moved all 5 downstream CLI tools from `tests/` to canonical `tools/` (`docs_validation.py`, `validate-docs.py` renamed from `validate-project-docs.py`, `new-feature.py`, `export-tasks.py`, `validate-task-evidence.py`) and moved `installer_lib.py` to `lib/installer_lib.py` without symlinks; removed the 5 `tools/*` overrides from `SOURCE_OVERRIDES`. | `bash -n setup.sh tests/setup.sh tests/validate-docs.sh tests/render-mermaid.sh template-paths.sh && bash setup.sh --doctor` | PASS / 0 | 2026-11-13 local/dev |
| AC-02 | Added `is_source_template_repository()` guard in `tools/new-feature.py` so `--list-presets` and `--dry-run` succeed directly in the template repository while mutating `docs/current/05 - Product Features/` in the source repository is refused; added regression assertions in `tests/setup.sh`. | `bash tests/setup.sh < /dev/null` | PASS / 0 | 2026-11-13 local/dev |
| AC-03 | Updated `AGENTS.md`, `README.md`, `skills/sdd-{docs,fix,implement}/SKILL.md` (preserving `0.6.0` hashes in `PRIOR_TEMPLATE_SHA256S`), `tests/validate-template-docs.py`, `tests/validate-skills-contract.py`, `tests/validate-docs.sh`, and `tests/render-mermaid.sh`. | `bash tests/validate-docs.sh && python3 -B tools/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed && bash tests/render-mermaid.sh --extract-only` | PASS / 0 | 2026-11-13 local/dev |
| AC-04 | Updated `.github/workflows/ai-template-validation.yml` to run on `pull_request`, `push` to `master`, and `workflow_dispatch`, added `concurrency` cancellation for non-`master` refs, added bytecode-free Python `ast.parse` syntax checking across `lib/`, `tools/`, and `tests/`, added `bash setup.sh --doctor` and `-B` flags, and guarded workflow invariants in `tests/validate-docs.sh`. | `python3 -B -c 'import ast, pathlib; [ast.parse(p.read_bytes(), filename=str(p)) for d in ("lib", "tools", "tests") for p in sorted(pathlib.Path(d).glob("*.py"))]' && bash tests/validate-docs.sh` | PASS / 0 | 2026-11-13 local/dev |

## Fact, assumption, unknown

| Type | Statement | Evidence / owner for confirmation |
|---|---|---|
| Fact | `tools/validate-task-evidence.py` verifies historical `completed` records via `git show <source_revision>:<output_artifact_path>`, so relocating `tests/*` to `tools/` and `lib/` without symlinks preserves all 19 historical release evidence records intact. | `python3 -B tools/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` (`PASS`). |
| Fact | Downstream `template-manifest.json` installation paths (`tools/*`), CLI flags, and `--update` / `--set-models` ownership behavior remain 100% backward-compatible with `0.6.0` and `0.5.1`. | `bash tests/setup.sh < /dev/null` (`PASS: setup installer regression tests`). |
| Assumption | Two-step Git SHA provenance is recorded across Commit 1 (`789e2d653d50fd0065e5a11be9167c39b1524697`) and Commit 2 (this completed task evidence), so merging branch `v0.6.0` into `master` should use `--no-ff` or fast-forward merge (not squash/rebase) to keep Commit 1 reachable for `tools/validate-task-evidence.py`. | Repository two-step provenance convention (`338b6bf`, `3168bfa`). |
| Unknown | Remote GitHub Actions CI run (`@mermaid-js/mermaid-cli` browser rendering on Linux/macOS) pending PR/push to `master` or `workflow_dispatch`. | Local/dev boundary (`tests/render-mermaid.sh --extract-only` verified locally). |

## Safety and completion

- Environment and data-handling check (no secrets/PII in logs or report): `local/dev` only; zero secrets or external network mutations.
- Command output artifact path and SHA-256 (or why unavailable): `lib/installer_lib.py`; `93f1ec3779bf6be482f706c4910caddfb8bf3bd99827f9400369ad7e040d490e` at `789e2d653d50fd0065e5a11be9167c39b1524697`.
- Changed files and docs changelog location: moved 5 scripts into `tools/` and `installer_lib.py` into `lib/`; updated `setup.sh`, `template-paths.sh`, `AGENTS.md`, `README.md`, `.github/workflows/ai-template-validation.yml`, `skills/sdd-{docs,fix,implement}/SKILL.md`, and `tests/{setup.sh,validate-docs.sh,render-mermaid.sh,validate-template-docs.py,validate-skills-contract.py}`; finalized this task evidence record.
- Residual risk / rollback: `git revert` the two commits on branch `v0.6.0` if needed.
- Reviewer/sign-off: User approved Option A1 layout split, GitHub Actions CI updates, and commit on branch `v0.6.0`, 2026-11-13.
