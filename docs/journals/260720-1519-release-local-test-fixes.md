---
date: 2026-07-20
context: v0.4.0 release local validation
status: completed
---

# Release local-test fixes

## Context

Ran the v0.4.0 local release validation suite.

## What happened

- Downstream install validation failed because a root-only link to `V4_ACCEPTANCE_MATRIX.md` appeared in installed documentation.
- Mermaid rendering required the pinned npm CLI. A global installation failed due to permissions; `npm exec` using Mermaid CLI v11.4.2 passed.

## Reflection

Downstream documentation must not depend on repository-root release artifacts. Prefer the pinned, project-scoped renderer over global tooling.

## Decisions

- Remove or replace root-only links from downstream-installed docs.
- Invoke Mermaid through the pinned npm CLI.

## Next

- Re-run the full local release validation suite before tagging.
