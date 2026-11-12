# V2 Acceptance Matrix

Release target: `0.2.0`
Scope: BA documentation foundation, Mermaid diagram standard, feature traceability, and an illustrative complete AI Agent sample.

| Area | Acceptance criterion | Validation |
|---|---|---|
| BA foundation | Core profile includes goals, stakeholders/RACI, personas, business rules, glossary, and risk register template. | `bash tests/validate-docs.sh` |
| Mermaid standard | Mermaid is named as the official standard and the required diagram index covers product and AI-agent flows. | `bash tests/validate-docs.sh` |
| Feature traceability | Product template traces story/use case/rules to AC; Tech and QA trace AC through implementation and test. | `bash tests/validate-docs.sh` |
| Complete sample | A fictional AI Support Agent includes Product, Tech, QA documents and Mermaid product, sequence, state, and data-boundary diagrams. | `bash tests/validate-docs.sh` |
| Installer profile | v0.2.0 core installation contains all v0.2.0 documentation files. | `bash tests/setup.sh` |

## Non-goals

- Rendering Mermaid to image assets or enforcing a specific static-site generator.
- Supplying factual requirements for a downstream project without discovery evidence.
- Implementing an AI Agent runtime.
