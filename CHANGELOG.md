# Changelog

## [0.5.0] - 2026-11-12

- Added a 4-file Spec-Driven Development feature pack (`4. Tasks.md` with embedded Pre-implementation Readiness Checklist, vertical MVP slicing, and `[P]` path-ownership boundaries) across `docs/templates/feature-spec-template/` and `docs/templates/examples/ai-support-agent/`.
- Added `docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md` covering the 6-stage `Specify -> Clarify -> Plan -> Tasks -> Analyze -> Implement, Converge & Evidence` workflow.
- Extended `docs_validation.py` and `tools/validate-docs.py` (`--require-tasks` optional) with code-stripped link scanning, Clarify Gate (`<=3` markers in `draft`, `0` markers/open checkboxes and required approval provenance on `approved`/`example` numbered feature specs), escaped-pipe header-driven cross-spec AC traceability, task DAG cycle checks, and segment-safe `[P]` `Owned paths` collision detection.
- Added `tools/new-feature.py` for numbered `NNN-<slug>` 4-file scaffolding with `--plain`, `--dry-run`, built-in archetypes (`general`, `web-api`, `cli-tool`, `ai-agent`), and custom `docs/templates/presets/<name>/` overlays.
- Added `tools/export-tasks.py` for offline task export (`json`, `markdown`, `gh-commands`), skipping `done` tasks by default (`--include-done`), blocking unapproved specs without `--allow-draft`, and supporting idempotent `gh issue list` + `gh issue create` execution only under explicit `--apply-gh --repo OWNER/REPO`.
- Added `setup.sh --preset` on install and `--update`, independent per-tool ownership preservation (`tools/new-feature.py`, `tools/export-tasks.py`), and source-template + downstream Spec/Clarify readiness checks in `setup.sh --doctor`.

## [0.4.4] - 2026-07-23

- Added `setup.sh --doctor`, a read-only readiness check for Bash/Python, selected runtime agents and adapters, manifest ownership, and local Markdown documentation links.
- Added `--dry-run --update --migration-plan PATH` to publish Markdown or JSON migration reports with replacement, preservation/manual-action, backup, and rollback guidance.
- Added simplicity-first and surgical-change policy guardrails, with onboarding guidance and regression validation.

## [0.4.3] - 2026-07-22

- Replaced the Gemini CLI installer selection with Antigravity CLI (`antigravity`) while retaining the documented `GEMINI.md` compatibility adapter.
- Added a validated, explicitly non-live Antigravity conformance fixture for `agy`, workspace context files, and `/agents`.
- Installed downstream task evidence in root `task-evidence/`, alongside `docs/`, and numbered reusable root template filenames.
- Safely reconcile unchanged v0.4.0–v0.4.2 template filenames during `--update`, while preserving user-modified files and symlinks.
- Required changelog entries created on the same date to share one date heading.

## [0.4.2] - 2026-07-21

- Added runtime-neutral agent orchestration guidance: select only available capabilities, delegate independent or high-risk review/security/QA/architecture work when warranted, and require explicit ownership plus evidence-based handoffs.
- Required code changes to map test or validation and receive review proportionate to risk.

## [0.4.1] - 2026-07-21

- Made `template-manifest.json` the source of profile membership and added installer parity coverage for its installed validator files.
- Validated the complete source manifest before preflight, rejecting traversal, control characters, malformed metadata, missing-profile, and unprofiled-document cases without writing the destination.
- Rejected overlapping profile paths and unsafe destination manifest paths during update; reserved profile definitions now always come from the current template.
- Shared Markdown link and Mermaid validation between repository and downstream validators.
- Made the shared downstream validator/helper an all-or-nothing bundle when user-owned files conflict, including during update; safely migrates a manifest-owned prior validator.
- Simplified update/onboarding navigation, corrected the vault map, and removed release-only runtime policy from downstream guidance.
- Added a non-destructive internal-evidence index and a `blocked-before-run` runtime-evidence mode.
- Marked AI-only spec rows as an explicit addendum to reduce unnecessary form filling for simple features.

## [0.4.0] - 2026-07-20

- Required documentation initialization and refresh to create applicable specialized sub-agents on hosts that expose delegation.
- Added role boundaries, evidence handoffs, coordinator ownership, conflict resolution and an explicit no-delegation sequential fallback.
- Added runtime capability guidance and structural validation for the orchestration contract.
- Added `setup.sh --update` for safe Bash upgrades: it requires a template-owned manifest, backs up replaced managed files and supports `--dry-run --update`.
- Hardened `--update` to preserve user-owned adapters, retain previously selected optional profiles, and write per-file recovery guidance in each backup.
- Made completed task evidence require an artifact present at its recorded Git revision; added runtime-delegation evidence schema validation and pinned the CI Node runtime.

## [0.3.1] - 2026-07-20

- Added native `GEMINI.md` and `QWEN.md` adapters that delegate to canonical `AGENTS.md` rules.
- Added runtime onboarding for context verification and a system/developer-prompt template for raw/custom model harnesses, including Gemma deployments.
- Clarified that prompting improves instruction priority but cannot replace runtime discovery, tool permissions, approvals, or model-specific compliance tests.

## [0.3.0] - 2026-07-18

- Separated downstream project notes, reusable templates, and source-only repository records.
- Added downstream documentation validation and whole-project documentation prompts.
- Strengthened installer boundaries, link validation, Mermaid structure validation, and sample traceability checks.
- Reject Markdown links that resolve outside the project root and syntax-check the Mermaid renderer in CI.
- Reject `file:` Markdown URIs and make the core manifest match the default installation exactly.
- Configure Mermaid's Puppeteer renderer without Chromium sandbox only on Ubuntu CI runners where the browser sandbox is unavailable.

## [0.2.0] - 2026-07-18

- Added BA Foundation templates for goals, stakeholders/RACI, personas, business rules, glossary, and risks.
- Declared Mermaid the official diagram standard, with required product and AI Agent diagram types.
- Expanded Product/Tech/QA feature templates with user-story, use-case, business-rule, traceability, and AI Agent safety guidance.
- Added a complete fictional AI Support Agent sample with product process, interaction, state/recovery, and data-boundary diagrams.
- Added v0.2.0 acceptance criteria and documentation validation.

## [0.1.0] - 2026-07-18

- Established the GitHub release baseline at version `0.1`.
- Finalized the initial template scope and acceptance matrix.
- Added evidence-first task records, a downstream task-evidence validator, inventory trust/freshness fields, approval lifecycle, and prompt-injection trust boundary.
- Hardened installer profiles, safety checks, metadata filtering, cross-platform CI, and documentation validation.
- Added task-evidence validator installation for downstream projects.
- Added profile capability manifest and dry-run blocked-path reporting.
