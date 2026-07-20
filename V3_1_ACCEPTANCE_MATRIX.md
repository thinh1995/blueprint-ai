# V3.1 Acceptance Matrix

Release target: `0.3.1`
Scope: make the template's workspace policy discoverable by Gemini CLI and Qwen Code, and document the system-message integration boundary for Gemma/custom raw-model harnesses.
Scope approval: `thinh1995` — 2026-07-20.
Reviewer/sign-off: Pending.

| Area | Acceptance criterion | Validation |
|---|---|---|
| Gemini adapter | A default install contains a concise root `GEMINI.md` that delegates to canonical `AGENTS.md`. | `bash tests/setup.sh` |
| Qwen adapter | A default install contains a concise root `QWEN.md` that delegates to canonical `AGENTS.md`. | `bash tests/setup.sh` |
| Installer contract | The core manifest exactly matches default-install files, including both runtime adapters. | `bash tests/setup.sh` |
| Runtime selection | Interactive setup presents a multi-select; `--models` installs only the requested native adapters and rejects invalid values without modifying the destination. | `bash tests/setup.sh` |
| Runtime documentation | Downstream onboarding gives model-specific active-context checks and does not claim that a repository file is itself a system prompt. | `bash tests/validate-docs.sh` |
| Custom harness | A reusable system/developer-message template distinguishes instruction priority from tool-level enforcement. | `python3 tests/validate-template-docs.py` |
| Repository evidence | The completed v0.3.1 evidence record maps each acceptance criterion to a validation result. | `python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` |

## Non-goals

- Guaranteeing compliance from any particular model.
- Configuring a downstream Gemma/custom API harness without its implementation details.
- Replacing runtime permission controls, approval gates, or test-based evaluation with prompting.
