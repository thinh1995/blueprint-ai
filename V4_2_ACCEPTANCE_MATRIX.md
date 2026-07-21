# V4.2 Acceptance Matrix

Release target: `0.4.2`
Scope: add runtime-neutral agent orchestration guidance without defining a fixed catalog of agents or changing the mandatory whole-project documentation workflow. Scope approval: User approval — 2026-07-21.
Reviewer/sign-off: User authorized release completion in Codex conversation — 2026-07-21. Local validation passed; completed evidence is recorded in a follow-up immutable commit.

| Area | Acceptance criterion | Validation |
|---|---|---|
| Available capabilities | The policy selects collaborating agents only from capabilities available in the active host. | `python3 tests/validate-orchestration-contract.py` |
| Risk-based delegation | When supported and warranted, the policy calls for delegation of independent or high-risk review, security, test/QA, and architecture work. | `python3 tests/validate-orchestration-contract.py` |
| Accountable handoffs | Delegated work has explicit ownership, evidence, and separate Fact / Assumption / Unknown entries. | `python3 tests/validate-orchestration-contract.py` |
| Code quality gate | Code changes map to test or validation and receive review proportional to risk. | `python3 tests/validate-orchestration-contract.py` |
| Release consistency | Manifest, README, changelog, and acceptance matrix identify `0.4.2`. | `python3 tests/validate-template-docs.py` |

## Non-goals

- Defining a fixed agent catalog or assuming agent names are portable across hosts.
- Requiring delegation for every task or changing the existing mandatory delegation rule for whole-project documentation work.
- Imposing universal coverage, immutability, API-envelope, or repository-pattern rules.
