---
status: active
owner: product-and-engineering
diagram_format: mermaid
---
# Diagram Standards

Mermaid is the official diagram format for this vault. Keep diagrams in the Markdown note that owns the decision or flow; use image attachments only when Mermaid cannot express the artifact.

## Required diagram index

| Context | Required diagram | Owner note |
|---|---|---|
| Product/feature | User or business-process flow with success, alternative, and failure paths | Product Spec |
| AI Agent feature | Interaction sequence and agent state/failure flow | Tech Spec; Product Spec links to the relevant diagrams |
| AI Agent using knowledge/tools | Data flow showing trust, access, and retention boundaries | Tech Spec |
| System boundary | Context/container flow when external actors or systems matter | Architecture |
| Persistent business data | ERD or explicit justification for no persistent model | Architecture or Tech Spec |

## Authoring rules

- Use fenced `mermaid` blocks; do not paste rendered images as the only source.
- Give every diagram a heading and state the scope, source assumptions, and linked requirement IDs.
- Label alternate, denied, retry, escalation, and terminal paths where they materially affect the user or business.
- Keep node labels concise and do not include credentials, personal data, or production identifiers.
- Update the diagram and its traceability rows in the same change as a behavior change.

## Supported patterns

### Business process

```mermaid
flowchart TD
  Start([Trigger]) --> Validate{Valid request?}
  Validate -->|Yes| Complete([Outcome])
  Validate -->|No| Recover[Explain or escalate]
  Recover --> Complete
```

### Interaction sequence

```mermaid
sequenceDiagram
  participant U as User
  participant A as AI Agent
  participant T as Approved Tool
  U->>A: Request
  A->>T: Authorized operation
  T-->>A: Result or failure
  A-->>U: Grounded answer or escalation
```

### Agent state and recovery

```mermaid
stateDiagram-v2
  [*] --> Understand
  Understand --> Retrieve: knowledge needed
  Retrieve --> Respond: grounded result
  Retrieve --> Escalate: no safe answer
  Respond --> [*]
  Escalate --> [*]
```

### Data model

```mermaid
erDiagram
  CUSTOMER ||--o{ SUPPORT_REQUEST : creates
  SUPPORT_REQUEST ||--o{ HANDOFF : may_create
```
