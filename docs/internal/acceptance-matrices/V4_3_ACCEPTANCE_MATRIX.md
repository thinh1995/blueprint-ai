# v0.4.3 Acceptance Matrix

Release target: `0.4.3`

| Area | Acceptance criterion | Validation |
|---|---|---|
| Antigravity runtime | The installer selects `antigravity`, presents Antigravity CLI, and installs its documented compatibility adapter `GEMINI.md`. | `bash tests/setup.sh` |
| Conformance fixture | A versioned, explicitly non-live fixture locks the `agy`, `AGENTS.md`, `GEMINI.md`, and `/agents` contract. | `python3 tests/validate-antigravity-conformance-fixture.py` |
| Evidence location | A fresh downstream install creates `task-evidence/` at project root, alongside `docs/`, and its validator defaults to that location. | `bash tests/setup.sh` |
| Template navigation | Reusable root template files have ordered names and all installed documentation links resolve to them. | `bash tests/validate-docs.sh` |
| Release notes | Entries published on the same date are grouped under one date heading. | `python3 tests/validate-template-docs.py` |
