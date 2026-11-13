# Internal Evidence Index

This directory is source-repository audit material and is never installed into downstream projects.

| Area | Purpose | Retention |
|---|---|---|
| `acceptance-matrices/` | Per-release acceptance criteria and validation matrices (`V1`..`V6+`). | Keep historical matrices; link current release from `README.md`. |
| `task-evidence/` | Per-task authority, acceptance criteria, validation and immutable release provenance. | Keep completed records and artifacts unchanged. |

## Lookup

- Acceptance matrices use `V<version>_ACCEPTANCE_MATRIX.md` in `acceptance-matrices/`.
- Release records use `YYYY-MM-DD-v<version>-<scope>.md` in `task-evidence/`.
- Search frontmatter fields `status` or `source_revision` before relying on filename order.

Do not rename, merge, or archive completed evidence until the evidence validator and every inbound reference support the migration.
