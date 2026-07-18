#!/bin/bash

set -euo pipefail

MMDC_BIN="${MMDC_BIN:-mmdc}"
if ! command -v "$MMDC_BIN" >/dev/null 2>&1; then
    echo "Missing Mermaid CLI '$MMDC_BIN'. Install @mermaid-js/mermaid-cli or set MMDC_BIN." >&2
    exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-template-mermaid.XXXXXX")"

cleanup() {
    rm -rf "$WORK_DIR"
}
trap cleanup EXIT

document_index=0
while IFS= read -r -d '' document; do
    document_index=$((document_index + 1))
    awk -v output_prefix="$WORK_DIR/$document_index" '
        BEGIN { count=0 }
        /^```mermaid[[:space:]]*$/ { capture=1; diagram=""; next }
        capture && /^```[[:space:]]*$/ { count++; print diagram > (output_prefix "-" count ".mmd"); capture=0; next }
        capture { diagram = diagram $0 "\n" }
    ' "$document"
done < <(find "$ROOT_DIR/docs/current" "$ROOT_DIR/docs/templates" -type f -name '*.md' -print0)

diagram_count="$(find "$WORK_DIR" -type f -name '*.mmd' | wc -l | tr -d ' ')"
[ "$diagram_count" -gt 0 ] || { echo "No Mermaid diagrams found" >&2; exit 1; }

for diagram in "$WORK_DIR"/*.mmd; do
    "$MMDC_BIN" -i "$diagram" -o "${diagram%.mmd}.svg" >/dev/null
    [ -s "${diagram%.mmd}.svg" ] || { echo "Mermaid render produced no SVG: $diagram" >&2; exit 1; }
done

echo "PASS: rendered $diagram_count Mermaid diagram(s)"
