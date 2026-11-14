# Changelog

## [0.6.1] - 2026-11-14

- Added a validated brownfield security and tech-debt register (`## Brownfield security and tech-debt triage` in `docs/current/02 - Architecture/Architecture.md`, 8-column `SEC-xx` table with `Open | In Progress | Mitigated | Accepted Risk` lifecycle statuses), paired with a `docs/current/**` high-confidence secret detector (PEM private keys, `AKIA...`, `ghp_...`, `sk-...`, credentialed URIs) and an explicit `.env*`/`*.pem`/`*.key`/`*.p12`/`.netrc`/`.npmrc` file-read denylist across `/sdd-docs` and `2. Documentation Subagent Contract.md`.
- Hardened `tools/docs_validation.py` with governance-scoped YAML frontmatter checks (`status`, `superseded_by`, `supersedes`, approval provenance — preserving Obsidian `tags: [...]` / `source_paths: [...]`), pre-`.resolve()` lexical symlink rejection across `docs/` walks, optional `docs/current/` wikilink prefixes, mandatory vault-wide `superseded_by` resolution across `docs/current/**` (`<= 16`-hop cycle-free chains, `--strict` terminal `approved`/`active` enforcement, historical approval preservation, and Git baseline tampering checks on superseded specs), and `supersedes` validation.
- Added anti-fragmentation governance and `tools/new-feature.py <slug> --supersede <existing-folder>` (reusing base slugs across `NNN-` numbering for Tier M -> Tier L promotion or full architectural replacement, stamping `supersedes: "05 - Product Features/<existing-folder>"`, and keeping the old pack active until atomic `/sdd-analyze` approval) while unconditionally refusing `superseded`/`archived` specs in `tools/export-tasks.py` even with `--allow-draft`.
- Added the 5th built-in SDD preset `security-hardening` across `setup.sh --preset`, `lib/installer_lib.py`, and `tools/new-feature.py` (both 4-file packs and `1. Mini Spec.md`), and recorded all `v0.6.0` canonical SHA-256 digests in `PRIOR_TEMPLATE_SHA256S` so `setup.sh --update --set-models` prunes deselected `v0.6.0` files without false `USER_SKILL` / `USER_ADAPTER` warnings.
- Updated all 8 canonical SDD skills (`skills/sdd-{docs,specify,clarify,plan,tasks,analyze,implement,fix}/SKILL.md`, each `<= 3950` B) for `superseded`/`archived` Auto-Resolution exclusion, Anti-Fragmentation Gate (`Spec Amendment` vs `--supersede`), atomic `/sdd-analyze` supersession, `SEC-xx -> Mitigated` convergence in `/sdd-implement` and `/sdd-fix`, and `--strict` validation parity, while keeping `core` Vault notes free of direct links to `--with-advanced-docs` `Infrastructure Spec.md`.

## [0.6.0] - 2026-11-13

- Extracted all inline Python blocks from `setup.sh` (`< 750` lines) and `template-paths.sh` into `tests/installer_lib.py` (`sys.dont_write_bytecode = True`) with component-wise symlink rejection, `O_NOFOLLOW` reads, `cp -Pp` atomic/backup copies, and restricted-`PATH` compatibility (no `env` or `git` dependency).
- Expanded runtime support to 8 targets (`claude`, `antigravity`, `qwen`, `opencode`, `codex`, `cursor`, `copilot`, `gemma`), added `adapters/cursor-agents.mdc` (`.cursor/rules/agents.mdc`, `alwaysApply: true`) and `adapters/copilot-instructions.md` (`.github/copilot-instructions.md`), upgraded `CLAUDE.md` (`@AGENTS.md`) and `AGENTS.md`, deduplicated `.agents/skills/` across 5 runtimes (`37 + core_doc_count` default install), and excluded `gemma` from omitted `--models` and blank interactive `Enter` defaults so `setup.sh && setup.sh --doctor` passes out-of-the-box.
- Added `setup.sh --set-models <list>` (standalone, `--force`, and `--update --set-models`) to install newly added adapters via `copy-if-absent`, back up and prune deselected template-managed adapters/skills while preserving user-modified files (`WARN`), and recover interrupted `--update` runs via `CREATED_FILES.txt` and canonical SHA-256 matching.
- Hardened `setup.sh --doctor` (`[--strict]`) to skip `plans/`, `node_modules/`, `.venv/`, and `.ai-template-backup.*/` during link scanning, verify `disable-model-invocation: true` and `alwaysApply: true`, warn on unignored backup directories and `AGENTS.override.md`, and separate default `WARN` (`exit 0`) from `--strict` `FAIL` (`exit 1`) for missing local CLIs, brownfield adapters lacking `AGENTS.md`, and legacy short-SHA `source_revision` values.
- Introduced **3-Tier Spec-Driven Development**: `Tier S` (`/sdd-fix` fast-track bugfix skill without feature-folder overhead), `Tier M` (`1. Mini Spec.md` via `tools/new-feature.py <slug> --mini`), and `Tier L` (full 4-file pack), updating all 8 canonical `skills/sdd-*/SKILL.md` (`<= 4 KB`, `argument-hint`, `disable-model-invocation: true`, injection-safe folder auto-resolution) and `validate-skills-contract.py`.
- Hardened `docs_validation.py`, `validate-project-docs.py`, `new-feature.py`, `export-tasks.py` (`1. Mini Spec.md`, `Related AC = -`, single scoped `gh issue list --search`, `--label`), `validate-task-evidence.py` (draft-only `--allow-working-tree`, `O_NOFOLLOW`, scoped `evidence-corrections.json`), and `render-mermaid.sh` (`--extract-only`, fence-length-aware Mermaid extraction) with fail-closed `status` enums, duplicate `NNN-` prefix checks, pre-unquote URI/traversal rejection, 40-hex `source_revision`, and earliest-approved-commit tampering detection.
- Standardized the **Contract Language Rule** across all 18 `docs/current/**` notes, 15 `docs/templates/**` notes, and `README.md` (100% English structural anchors — YAML keys/enums, Markdown headings, and parser-validated table headers — paired with natural Vietnamese prose) and added root `.gitignore`.

## [0.5.1] - 2026-11-12

- Added 7 canonical progressive-disclosure `sdd-*` Agent Skills (`skills/sdd-{docs,specify,clarify,plan,tasks,analyze,implement}/SKILL.md`, each `<= 4 KB` with portable `{name, description}` frontmatter, explicit-intent read-only guardrails, depth-safe inline code path references, and active feature folder auto-resolution) delegating without duplication to `AGENTS.md` and `docs/current/00 - Onboarding/` (`4` & `6`).
- Added `tests/validate-skills-contract.py` (`--self-test` supported) to enforce canonical skill directory structure, strict frontmatter keys, byte budget, code-stripped link/wikilink/clarify hygiene, and policy/trust delegation.
- Updated `setup.sh`, `template-paths.sh`, and `template-manifest.json` (`0.5.1`) to install the 7 skills by default into `.claude/skills/`, `.agents/skills/`, and `.qwen/skills/` per selected `--models` (`gemma` installs 0 skill directories), with `--without-skills` opt-out (`"skills_enabled": false`), non-destructive `--update --without-skills` preservation, incremental normal-install re-enable, and per-skill user-ownership preservation + `.ai-template-backup.*` (`RECOVERY.md`) updates.
- Extended `setup.sh --doctor` to verify the 7 canonical SDD skills in source-template mode and verify managed runtime skill files (or report `INFO skills: disabled via --without-skills`) in downstream projects.
- Updated `README.md` (beginner 5-minute Quickstart showcasing `/sdd-docs` and `/sdd-specify` -> `/sdd-implement` alongside natural-language fallback) and onboarding notes `1`, `4`, `5`, and `6`.

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
