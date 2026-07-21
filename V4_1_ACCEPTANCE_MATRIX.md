# V4.1 Acceptance Matrix

Release target: `0.4.1`
Scope: reduce maintenance drift while preserving installer safety, documentation governance, and audit provenance. Scope approval: User approval — 2026-07-21.
Reviewer/sign-off: Local validation pending final review; release evidence remains draft until an immutable release artifact is committed.

| Area | Acceptance criterion | Validation |
|---|---|---|
| Release metadata | Manifest, README, changelog, and acceptance matrix identify `0.4.1`. | `python3 tests/validate-template-docs.py` |
| Profile source of truth | Advanced and legacy profile membership comes from `template-manifest.json`; installer parity remains covered. | `bash tests/setup.sh` |
| Profile safety | Source profiles reject unsafe/control-character/overlapping paths and unprofiled docs before preflight; an update rejects unsafe destination manifest paths without writing. | `bash tests/setup.sh` |
| Shared validation | Repository and downstream documentation validators use the same link/Mermaid implementation. | `bash tests/setup.sh`; `python3 tests/validate-project-docs.py`; `python3 tests/validate-template-docs.py` |
| Validator bundle integrity | A user-owned validator helper prevents installing either half of the shared validator bundle, including on `--update`, and the generated manifest does not claim either path. | `bash tests/setup.sh` |
| Documentation navigation | Onboarding links to canonical policy, MOC navigation reflects actual starter notes, and runtime guidance has no release-only gate. | `bash tests/validate-docs.sh`; `python3 tests/validate-project-docs.py` |
| Evidence semantics | A skipped runtime record is represented as `blocked-before-run`, distinct from a sequential fallback. | `python3 tests/validate-runtime-delegation-fixture.py` |
| Evidence discoverability | Internal evidence has a stable, non-destructive index. | `python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` |
| CI clarity | CI relies on installer regression coverage for installed downstream validation and does not repeat the same direct validator. | Workflow review; `bash tests/setup.sh` |

## Non-goals

- Rewriting the installer or weakening symlink, hard-link, preflight, backup, or recovery protections.
- Deleting, renaming, merging, or archiving completed evidence records.
- Claiming a measured CI performance improvement without runtime data.
