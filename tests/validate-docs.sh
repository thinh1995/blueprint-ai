#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

require_text() {
    local file="$1"
    local text="$2"

    grep -Fq -- "$text" "$ROOT_DIR/$file" || {
        echo "Missing '$text' in $file" >&2
        exit 1
    }
}

for file in \
    "docs/templates/feature-spec-template/1. Product Spec.md" \
    "docs/templates/feature-spec-template/2. Tech Spec.md" \
    "docs/templates/feature-spec-template/3. QA Spec.md"; do
    require_text "$file" "approved_by:"
    require_text "$file" "approved_at:"
    require_text "$file" "approval_evidence:"
    require_text "$file" "source_revision:"
done

require_text "docs/templates/task-evidence-template.md" "Acceptance criteria and validation"
require_text "docs/templates/task-evidence-template.md" "output_artifact_path:"
require_text "AGENTS.md" "Never invent file/line references"
require_text "AGENTS.md" "untrusted data"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified: false"
require_text "docs/current/02 - Architecture/Generated Reference Inventory.md" "verified_at:"

require_text "docs/current/01 - Overview/BA Foundation.md" "Stakeholders and RACI"
require_text "docs/current/01 - Overview/BA Foundation.md" "Business rules catalogue"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" "Mermaid is the official diagram format"
require_text "docs/current/08 - Diagram Standards/Diagram Standards.md" '```mermaid'
require_text "docs/templates/feature-spec-template/1. Product Spec.md" "Stakeholder, user stories, and use cases"
require_text "docs/templates/feature-spec-template/1. Product Spec.md" "## Traceability"
require_text "docs/templates/feature-spec-template/2. Tech Spec.md" "Tool permissions, timeout, retry, fallback"
require_text "docs/templates/feature-spec-template/3. QA Spec.md" "prompt injection"
for file in \
    "docs/templates/examples/ai-support-agent/1. Product Spec.md" \
    "docs/templates/examples/ai-support-agent/2. Tech Spec.md" \
    "docs/templates/examples/ai-support-agent/3. QA Spec.md"; do
    require_text "$file" "status: example"
done
require_text "docs/templates/examples/ai-support-agent/1. Product Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" '```mermaid'
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "sequenceDiagram"
require_text "docs/templates/examples/ai-support-agent/2. Tech Spec.md" "stateDiagram-v2"
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "docs/templates"
require_text "V3_ACCEPTANCE_MATRIX.md" 'Release target: `0.3.0`'
require_text "docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "tools/validate-docs.py"
require_text ".github/workflows/ai-template-validation.yml" "fetch-depth: 0"
require_text ".github/workflows/ai-template-validation.yml" "actions/setup-node@49933ea5288caeca8642d1e84afbd3f7d6820020"
require_text ".github/workflows/ai-template-validation.yml" "node-version: 22.14.0"
require_text "README.md" "--dry-run --update"
require_text "docs/current/00 - Onboarding/1. Setup Guide.md" "RECOVERY.md"
python3 "$ROOT_DIR/tests/validate-template-docs.py"
python3 "$ROOT_DIR/tests/validate-orchestration-contract.py"
python3 "$ROOT_DIR/tests/validate-runtime-delegation-fixture.py"

echo "PASS: documentation guardrail validation"
