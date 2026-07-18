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

echo "PASS: documentation guardrail validation"
