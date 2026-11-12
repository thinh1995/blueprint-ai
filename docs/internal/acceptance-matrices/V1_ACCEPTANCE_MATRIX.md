# V1 Acceptance Matrix

Release target: `0.1`
Scope: safe installer, core/advanced docs, evidence-first rules, per-task evidence, inventory trust gate, validator, and CI template.

| Area | Acceptance criterion | Validation | Final review |
|---|---|---|---|
| Installer safety | Dry-run does not write; preserve/force/symlink/hard-link/path-collision/metadata cases are safe. | `bash tests/setup.sh` | Pass — 2026-07-17 |
| Installation profiles | Core excludes opt-in files; advanced and legacy profiles install their declared content. | `bash tests/setup.sh` | Pass — 2026-07-17 |
| Template docs | Agent rules, approval fields, task-evidence template, inventory trust metadata and links are present. | `bash tests/validate-docs.sh` | Pass — 2026-07-17 |
| Task evidence | Completed records require identity, revision, AC validation, environment, reviewer and verified output artifact hash. | `python3 tests/validate-task-evidence.py` | Pass — 2026-07-17 |
| Downstream use | Installed project receives the task-evidence validator. | `bash tests/setup.sh` | Pass — 2026-07-17 |
| CI template | Ubuntu/macOS matrix, read-only permission, timeout, syntax/tests/docs/task-evidence validation are configured. | Review [.github/workflows/ai-template-validation.yml](../../../.github/workflows/ai-template-validation.yml) | Pass — 2026-07-17 |

## V1 non-goals / backlog

- Infer behavior-changing intent from arbitrary git diffs.
- Verify human reviewer identity or approval source outside the repository.
- Guarantee immutable multi-file installer transactions under filesystem races or failures.
- Automatically install a downstream CI workflow for every CI provider.

## Final review commands

```bash
bash -n setup.sh tests/setup.sh tests/validate-docs.sh template-paths.sh
bash tests/setup.sh
bash tests/validate-docs.sh
python3 tests/validate-task-evidence.py
```

Release rule: all rows must pass. New findings outside the stated scope are backlog items unless they invalidate an acceptance criterion above.
