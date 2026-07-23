# v0.4.4 Acceptance Matrix

Release target: `0.4.4`

| Area | Acceptance criterion | Validation |
|---|---|---|
| Simplicity and surgical scope | Canonical policy requires the smallest approved change and prohibits unrelated refactors, deletions, formatting, and comment edits. | `bash tests/validate-docs.sh` |
| Environment readiness | `setup.sh --doctor` read-only checks Bash/Python, selected runtime adapters and commands, manifest ownership, and local Markdown links; failures include remediation and produce a non-zero exit. | `bash tests/setup.sh` |
| Migration planner | `setup.sh --dry-run --update --migration-plan PATH` writes Markdown or JSON without changing template-managed files, and reports replacement, preservation/manual-action, backup, and rollback information. | `bash tests/setup.sh` |
| Release integration | Version, release notes, acceptance matrix, installer syntax, docs, and task evidence remain internally consistent. | `bash tests/setup.sh`; `bash tests/validate-docs.sh`; `python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence` |
