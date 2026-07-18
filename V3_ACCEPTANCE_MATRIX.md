# V3 Acceptance Matrix

Release target: `0.3.0`
Scope: separate downstream project docs from reusable templates and source-only records; ship whole-project documentation guidance and downstream validation.
Scope approval: `thinh1995` — 2026-07-18.
Reviewer/sign-off: `thinh1995` — 2026-07-18.

| Area | Acceptance criterion | Validation |
|---|---|---|
| Layout | `docs/current/` contains project notes; reusable material is in `docs/templates/`; source records are in `docs/internal/`. | `bash tests/setup.sh` |
| Installer boundary | `docs/internal/` is never installed, including when the destination already has internal files. | `bash tests/setup.sh` |
| Profile manifest | The `core` manifest profile expands to exactly the files installed by a default setup. | `bash tests/setup.sh` |
| Feature workspace | A fresh install contains `docs/current/05 - Product Features/` but no template/sample in that directory. | `bash tests/setup.sh` |
| Downstream validation | Fresh installs receive `tools/validate-docs.py` and `tools/validate-task-evidence.py`; local `file:` links are rejected. | `bash tests/setup.sh` |
| Documentation prompt | Onboarding supplies governed initialize and refresh prompts with authority and AC→validation rules. | `bash tests/validate-docs.sh` |
| Template quality | Source links, Mermaid fences, and sample traceability are structurally valid. | `python3 tests/validate-template-docs.py` |
| Repository evidence | Completed release records under `docs/internal/task-evidence/` validate independently of downstream task evidence. | `python3 tests/validate-task-evidence.py --evidence-dir docs/internal/task-evidence --require-completed` |

## Non-goals

- Automatically generating factual project documentation without inspecting source evidence.
- Requiring a particular static-site generator or Markdown renderer.
- Publishing or tagging v0.3.0 before the release PR is merged.
