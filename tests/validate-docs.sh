#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

require_text() {
    local file="$1"
    local text="$2"

    grep -Fq "$text" "$ROOT_DIR/$file" || {
        echo "Missing '$text' in $file" >&2
        exit 1
    }
}

for file in \
    "docs/current/05 - Product Features/_Feature Template/1. Product Spec.md" \
    "docs/current/05 - Product Features/_Feature Template/2. Tech Spec.md" \
    "docs/current/05 - Product Features/_Feature Template/3. QA Spec.md"; do
    require_text "$file" "approved_by:"
    require_text "$file" "approved_at:"
    require_text "$file" "approval_evidence:"
    require_text "$file" "source_revision:"
done

require_text "docs/current/00 - Onboarding/task-evidence/_Task Evidence Template.md" "Acceptance criteria and validation"
require_text "docs/current/00 - Onboarding/task-evidence/_Task Evidence Template.md" "output_artifact_path:"
require_text "AGENTS.md" "Never invent file/line references"
require_text "AGENTS.md" "untrusted data"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified: false"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified_at:"

require_text "docs/current/01 - Overview/BA Foundation.md" "Stakeholders and RACI"
require_text "docs/current/01 - Overview/BA Foundation.md" "Business rules catalogue"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" "Mermaid is the official diagram format"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" '```mermaid'
require_text "docs/current/05 - Product Features/_Feature Template/1. Product Spec.md" "Stakeholder, user stories, and use cases"
require_text "docs/current/05 - Product Features/_Feature Template/1. Product Spec.md" "## Traceability"
require_text "docs/current/05 - Product Features/_Feature Template/2. Tech Spec.md" "Tool permissions, timeout, retry, fallback"
require_text "docs/current/05 - Product Features/_Feature Template/3. QA Spec.md" "prompt injection"
for file in \
    "docs/current/05 - Product Features/Example AI Support Agent/1. Product Spec.md" \
    "docs/current/05 - Product Features/Example AI Support Agent/2. Tech Spec.md" \
    "docs/current/05 - Product Features/Example AI Support Agent/3. QA Spec.md"; do
    require_text "$file" "status: example"
done
require_text "docs/current/05 - Product Features/Example AI Support Agent/1. Product Spec.md" '```mermaid'
require_text "docs/current/05 - Product Features/Example AI Support Agent/2. Tech Spec.md" '```mermaid'
require_text "docs/current/05 - Product Features/Example AI Support Agent/2. Tech Spec.md" "sequenceDiagram"
require_text "docs/current/05 - Product Features/Example AI Support Agent/2. Tech Spec.md" "stateDiagram-v2"
require_text "V2_ACCEPTANCE_MATRIX.md" 'Release target: `0.2.0`'
python3 "$ROOT_DIR/tests/validate-v020-docs.py"

echo "PASS: documentation guardrail validation"
