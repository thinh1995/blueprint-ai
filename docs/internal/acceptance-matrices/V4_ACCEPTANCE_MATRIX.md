# V4 Acceptance Matrix

Release target: `0.4.0`
Scope: require evidence-based, specialized sub-agent orchestration for whole-project documentation initialization and refresh on every host that exposes delegation; retain an explicit sequential fallback only for hosts without that capability; and provide a safe Bash upgrade path from an older template-managed installation.
Scope approval: User approval — 2026-07-20.
Reviewer/sign-off: Implementation validated locally; release evidence and sign-off remain pending until the release artifact is committed.

## Live runtime refresh evidence

Claude Code, Gemini CLI and Qwen Code remain supported runtime adapters, but the v0.4.0 release gate runs a live delegation refresh **only on Codex**. The records for the other three runtimes are retained as diagnostics and explicitly skipped from this release gate; they are not passing runtime executions.

| Runtime | Record | Current result |
|---|---|---|
| Codex desktop host | [2026-07-20-codex.md](../runtime-delegation-evidence/2026-07-20-codex.md) | Delegated refresh completed; awaiting committed release artifact/sign-off. |
| Claude Code | [2026-07-20-claude-code.md](../runtime-delegation-evidence/2026-07-20-claude-code.md) | Skipped from v0.4.0 live gate; prior API connection failure retained as diagnostic. |
| Gemini CLI | [2026-07-20-gemini-cli.md](../runtime-delegation-evidence/2026-07-20-gemini-cli.md) | Skipped from v0.4.0 live gate; executable absence retained as diagnostic. |
| Qwen Code | [2026-07-20-qwen-code.md](../runtime-delegation-evidence/2026-07-20-qwen-code.md) | Skipped from v0.4.0 live gate; executable absence retained as diagnostic. |

| Area | Acceptance criterion | Validation |
|---|---|---|
| Mandatory delegation | On a host exposing delegation, the documentation workflow requires creation of applicable specialized sub-agents before a documentation write. | `python3 tests/validate-orchestration-contract.py`; `python3 tests/validate-runtime-delegation-fixture.py`; Codex live host record at release sign-off. |
| Specialized roles | The role contract covers source discovery, architecture/API, product/BA and QA/traceability with bounded missions and ownership. | `python3 tests/validate-orchestration-contract.py` |
| Evidence and coordination | Every handoff carries evidence and Fact/Assumption/Unknown; the coordinator owns cross-cutting writes and conflict resolution. | `python3 tests/validate-orchestration-contract.py` |
| Unsupported host fallback | A host without delegation records the capability check and performs equivalent sequential phases without claiming delegation. | `python3 tests/validate-orchestration-contract.py`; `python3 tests/validate-runtime-delegation-fixture.py`; static contract check for v0.4.0 release. |
| Runtime guidance | Runtime onboarding distinguishes discovered instructions from host delegation capability and describes host checks for Codex-compatible, Claude, Gemini, Qwen and Gemma/custom deployments. | `bash tests/validate-docs.sh` |
| Repository integration | The release version, README, changelog, acceptance matrix and completed evidence remain consistent. | `bash tests/setup.sh`; `python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` |
| Safe Bash upgrade | `setup.sh --update` upgrades every previously selected template-managed profile, preserves user-owned adapters, backs up each replacement with recovery guidance, and supports a no-write dry run. | `bash tests/setup.sh` |

## Non-goals

- Claiming that a repository prompt can force a host that provides no delegation tool to create sub-agents.
- Replacing runtime permission controls, tool approvals, or host-specific safety policies.
- Allowing unbounded parallel writes by sub-agents to shared project documentation.
