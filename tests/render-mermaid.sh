#!/bin/bash

set -euo pipefail

EXTRACT_ONLY=false
EXTRACT_OUT_DIR=""
while [ "$#" -gt 0 ]; do
    case "$1" in
        --extract-only)
            EXTRACT_ONLY=true
            if [ "${2:-}" != "" ] && [[ "${2:-}" != --* ]]; then
                EXTRACT_OUT_DIR="$2"
                shift 2
                continue
            fi
            shift
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

MMDC_BIN="${MMDC_BIN:-mmdc}"
MMDC_PUPPETEER_CONFIG="${MMDC_PUPPETEER_CONFIG:-}"
if [ "$EXTRACT_ONLY" = false ] && ! command -v "$MMDC_BIN" >/dev/null 2>&1; then
    echo "Missing Mermaid CLI '$MMDC_BIN'. Install @mermaid-js/mermaid-cli or set MMDC_BIN." >&2
    exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
if [ -n "$EXTRACT_OUT_DIR" ]; then
    mkdir -p "$EXTRACT_OUT_DIR"
    WORK_DIR="$EXTRACT_OUT_DIR"
    CLEANUP_WORK_DIR=false
else
    WORK_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-template-mermaid.XXXXXX")"
    CLEANUP_WORK_DIR=true
fi

if [ -n "$MMDC_PUPPETEER_CONFIG" ] && [[ "$MMDC_PUPPETEER_CONFIG" != /* ]]; then
    MMDC_PUPPETEER_CONFIG="$ROOT_DIR/$MMDC_PUPPETEER_CONFIG"
fi
if [ -n "$MMDC_PUPPETEER_CONFIG" ] && [ ! -f "$MMDC_PUPPETEER_CONFIG" ]; then
    echo "Missing Puppeteer config: $MMDC_PUPPETEER_CONFIG" >&2
    exit 2
fi

cleanup() {
    if [ "$CLEANUP_WORK_DIR" = true ]; then
        rm -rf "$WORK_DIR"
    fi
}
trap cleanup EXIT

diagram_count="$(
    python3 -B - "$ROOT_DIR" "$WORK_DIR" <<'PY'
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root_dir = Path(sys.argv[1]).resolve()
work_dir = Path(sys.argv[2]).resolve()
sys.path.insert(0, str(root_dir / "tools"))

from docs_validation import extract_mermaid_blocks, read_markdown  # noqa: E402

docs_dirs = [root_dir / "docs" / "current", root_dir / "docs" / "templates"]
md_files: list[Path] = []
for d in docs_dirs:
    if d.is_dir():
        md_files.extend(sorted(p for p in d.rglob("*.md") if not p.is_symlink() and p.is_file()))

manifest_lines: list[str] = []
idx = 0
for md_path in md_files:
    rel_label = md_path.relative_to(root_dir).as_posix()
    blocks = extract_mermaid_blocks(read_markdown(md_path), rel_label)
    for line_no, body in blocks:
        idx += 1
        mmd_name = f"{idx:04d}.mmd"
        (work_dir / mmd_name).write_text(body + "\n", encoding="utf-8")
        manifest_lines.append(f"{mmd_name} -> {rel_label}:{line_no}")

(work_dir / "manifest.txt").write_text("\n".join(manifest_lines) + ("\n" if manifest_lines else ""), encoding="utf-8")
print(idx)
PY
)"

[ "$diagram_count" -gt 0 ] || { echo "No Mermaid diagrams found" >&2; exit 1; }

if [ "$EXTRACT_ONLY" = true ]; then
    echo "PASS: extracted $diagram_count Mermaid diagram(s)"
    exit 0
fi

for diagram in "$WORK_DIR"/*.mmd; do
    base_name="$(basename "$diagram")"
    src_loc="$(grep -F "${base_name} -> " "$WORK_DIR/manifest.txt" | head -n 1 || true)"
    render_args=(-i "$diagram" -o "${diagram%.mmd}.svg")
    if [ -n "$MMDC_PUPPETEER_CONFIG" ]; then
        render_args=(-p "$MMDC_PUPPETEER_CONFIG" "${render_args[@]}")
    fi
    if ! "$MMDC_BIN" "${render_args[@]}" >/dev/null; then
        echo "Mermaid render failed (${src_loc:-$diagram})" >&2
        exit 1
    fi
    [ -s "${diagram%.mmd}.svg" ] || { echo "Mermaid render produced no SVG (${src_loc:-$diagram})" >&2; exit 1; }
done

echo "PASS: rendered $diagram_count Mermaid diagram(s)"
