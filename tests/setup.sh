#!/bin/bash

set -euo pipefail

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$TEMPLATE_DIR/template-paths.sh"
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-template-test.XXXXXX")"

cleanup() {
    rm -rf "$TEST_DIR"
}
trap cleanup EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

assert_file_contains() {
    local file="$1"
    local expected="$2"

    grep -Fq "$expected" "$file" || fail "Expected '$expected' in $file"
}

assert_file_matches() {
    local file="$1"
    local pattern="$2"

    grep -Eq "$pattern" "$file" || fail "Expected pattern '$pattern' in $file"
}

file_mode() {
    local file="$1"

    case "$(uname -s)" in
        Darwin) stat -f '%Lp' "$file" ;;
        *) stat -c '%a' "$file" ;;
    esac
}

target="$TEST_DIR/target"
mkdir -p "$target"
core_doc_count=0
while IFS= read -r source_file; do
    relative_path="${source_file#"$TEMPLATE_DIR/"}"
    is_optional=false
    for optional_doc in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
        [ "$relative_path" = "$optional_doc" ] && is_optional=true
    done
    [ "$is_optional" = true ] || core_doc_count=$((core_doc_count + 1))
done < <(find "$TEMPLATE_DIR/docs" -path "$TEMPLATE_DIR/docs/internal" -prune -o -type f ! -name '.DS_Store' -print)
expected_file_count=$((5 + core_doc_count))

(
    cd "$target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run
) > "$TEST_DIR/dry-run.txt"

[ ! -e "$target/AGENTS.md" ] || fail "dry-run wrote AGENTS.md"
assert_file_contains "$TEST_DIR/dry-run.txt" "Dry run complete: $expected_file_count file(s) would be installed"

printf 'custom rules\n' > "$target/AGENTS.md"
(
    cd "$target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/default-install.txt"
assert_file_contains "$target/AGENTS.md" "custom rules"
[ -f "$target/docs/current/Vault Index MOC.md" ] || fail "default install did not copy docs"
[ -f "$target/docs/current/01 - Overview/BA Foundation.md" ] || fail "default install did not copy BA Foundation"
[ -f "$target/docs/current/08 - Diagram Standards/Diagram Standards.md" ] || fail "default install did not copy Diagram Standards"
[ -f "$target/docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" ] || fail "default install did not copy documentation update prompt"
[ -f "$target/docs/current/05 - Product Features/README.md" ] || fail "default install did not create Product Features workspace"
for template_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md" "README.md"; do
    [ -f "$target/docs/templates/feature-spec-template/$template_file" ] || fail "default install did not copy feature template: $template_file"
done
for sample_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md"; do
    [ -f "$target/docs/templates/examples/ai-support-agent/$sample_file" ] || fail "default install did not copy AI Agent sample: $sample_file"
done
[ -f "$target/docs/templates/task-evidence-template.md" ] || fail "default install did not copy task evidence template"
[ ! -e "$target/docs/current/05 - Product Features/_Feature Template" ] || fail "default install mixed feature template with project docs"
[ ! -e "$target/docs/current/05 - Product Features/Example AI Support Agent" ] || fail "default install mixed sample with project docs"
[ ! -e "$target/docs/internal" ] || fail "default install copied source-only internal docs"
if grep -R -E '^(\*Changelog:|\*Khởi tạo:)' "$target/docs/current" "$target/docs/templates"; then
    fail "default install copied template-repository changelog text"
fi
[ -f "$target/template-manifest.json" ] || fail "default install did not copy template manifest"
[ -f "$target/CLAUDE.md" ] || fail "default install did not copy CLAUDE.md"
[ -f "$target/tools/validate-task-evidence.py" ] || fail "default install did not copy task-evidence validator"
[ -f "$target/tools/validate-docs.py" ] || fail "default install did not copy downstream docs validator"
python3 "$target/tools/validate-docs.py" || fail "downstream docs validator failed after default install"
python3 "$target/tools/validate-task-evidence.py" || fail "downstream task-evidence validator failed without task records"

link_boundary_target="$TEST_DIR/link-boundary-target"
mkdir -p "$link_boundary_target/docs/current" "$link_boundary_target/tools"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$link_boundary_target/tools/validate-docs.py"
printf 'outside fixture root\n' > "$TEST_DIR/outside-fixture.md"
printf '[outside](../../../outside-fixture.md)\n' > "$link_boundary_target/docs/current/escaping-link.md"
if python3 "$link_boundary_target/tools/validate-docs.py" > "$TEST_DIR/link-boundary-output.txt" 2>&1; then
    fail "downstream docs validator accepted a Markdown link outside the project root"
fi
assert_file_contains "$TEST_DIR/link-boundary-output.txt" "escapes project root"

file_uri_target="$TEST_DIR/file-uri-target"
mkdir -p "$file_uri_target/docs/current" "$file_uri_target/tools"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$file_uri_target/tools/validate-docs.py"
printf '[outside](file:///outside-fixture.md)\n' > "$file_uri_target/docs/current/file-uri-link.md"
if python3 "$file_uri_target/tools/validate-docs.py" > "$TEST_DIR/file-uri-output.txt" 2>&1; then
    fail "downstream docs validator accepted a file URI"
fi
assert_file_contains "$TEST_DIR/file-uri-output.txt" "unsupported Markdown URI scheme file:"

[ ! -e "$target/.agents/AGENTS.md" ] || fail "default install copied optional nested AGENTS.md"
assert_file_matches "$target/template-manifest.json" '"version"[[:space:]]*:[[:space:]]*"[0-9]+\.[0-9]+\.[0-9]+"'
python3 -m json.tool "$target/template-manifest.json" >/dev/null || fail "installer wrote invalid manifest JSON"
for managed_path in "AGENTS.md" "CLAUDE.md" "template-manifest.json" "tools/validate-task-evidence.py" "tools/validate-docs.py" "docs/current" "docs/templates"; do
    assert_file_contains "$target/template-manifest.json" "\"$managed_path\""
done
python3 - "$TEMPLATE_DIR" "$target" <<'PY'
import json
import sys
from pathlib import Path

template_root = Path(sys.argv[1])
target_root = Path(sys.argv[2])
profile = json.loads((template_root / "template-manifest.json").read_text())["profiles"]["core"]
source_overrides = {
    "tools/validate-task-evidence.py": "tests/validate-task-evidence.py",
    "tools/validate-docs.py": "tests/validate-project-docs.py",
}
expected: set[str] = set()
for relative in profile:
    source = template_root / source_overrides.get(relative, relative)
    if source.is_file():
        expected.add(relative)
    elif source.is_dir():
        expected.update(path.relative_to(template_root).as_posix() for path in source.rglob("*") if path.is_file())
    else:
        raise SystemExit(f"FAIL: manifest core path is missing from template: {relative}")
installed = {path.relative_to(target_root).as_posix() for path in target_root.rglob("*") if path.is_file()}
if expected != installed:
    missing = sorted(expected - installed)
    unexpected = sorted(installed - expected)
    raise SystemExit(f"FAIL: manifest core does not match default install; missing={missing}, unexpected={unexpected}")
PY
[ "$(file_mode "$target/AGENTS.md")" = "$(file_mode "$TEMPLATE_DIR/AGENTS.md")" ] || fail "installer changed AGENTS.md mode"
[ "$(file_mode "$target/docs/current/Vault Index MOC.md")" = "$(file_mode "$TEMPLATE_DIR/docs/current/Vault Index MOC.md")" ] || fail "installer changed docs mode"

metadata_template="$TEST_DIR/template-with-metadata"
metadata_target="$TEST_DIR/metadata-target"
mkdir -p "$metadata_template/tests" "$metadata_target"
for template_file in setup.sh template-paths.sh AGENTS.md CLAUDE.md template-manifest.json; do
    cp "$TEMPLATE_DIR/$template_file" "$metadata_template/$template_file"
done
cp "$TEMPLATE_DIR/tests/validate-task-evidence.py" "$metadata_template/tests/validate-task-evidence.py"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$metadata_template/tests/validate-project-docs.py"
cp -R "$TEMPLATE_DIR/docs" "$metadata_template/docs"
printf 'finder metadata\n' > "$metadata_template/docs/.DS_Store"
(
    cd "$metadata_target"
    bash "$metadata_template/setup.sh"
) > "$TEST_DIR/metadata-filter.txt"
[ ! -e "$metadata_target/docs/.DS_Store" ] || fail "installer copied .DS_Store metadata"

optional_target="$TEST_DIR/optional-target"
mkdir -p "$optional_target"
(
    cd "$optional_target"
    bash "$TEMPLATE_DIR/setup.sh" --with-advanced-docs --with-legacy-agents
) > "$TEST_DIR/optional-install.txt"
[ -f "$optional_target/.agents/AGENTS.md" ] || fail "optional install did not copy nested AGENTS.md"
for optional_doc in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
    [ -f "$optional_target/$optional_doc" ] || fail "optional install did not copy $optional_doc"
done
[ ! -e "$optional_target/docs/internal" ] || fail "advanced install copied source-only internal docs"
[ -f "$target/docs/current/02 - Architecture/Generated Reference Inventory.md" ] || fail "core install did not copy generated inventory"

internal_target="$TEST_DIR/internal-target"
mkdir -p "$internal_target/docs/internal"
printf 'preserve this source-only note\n' > "$internal_target/docs/internal/sentinel.txt"
(
    cd "$internal_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/internal-preservation.txt"
assert_file_contains "$internal_target/docs/internal/sentinel.txt" "preserve this source-only note"
[ ! -e "$internal_target/docs/internal/task-evidence" ] || fail "installer wrote source evidence into an existing internal directory"

dry_run_target="$TEST_DIR/dry-run-blocked-target"
mkdir -p "$dry_run_target"
ln -s /private/tmp/external-agent-rules "$dry_run_target/AGENTS.md"
(
    cd "$dry_run_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --force
) > "$TEST_DIR/dry-run-blocked.txt"
assert_file_contains "$TEST_DIR/dry-run-blocked.txt" "BLOCKED (symlink): AGENTS.md"
assert_file_contains "$TEST_DIR/dry-run-blocked.txt" "Dry run complete:"
[ "$(grep -Fc 'BLOCKED (symlink): AGENTS.md' "$TEST_DIR/dry-run-blocked.txt")" -eq 1 ] || fail "dry-run reported a blocked path more than once"
[ -L "$dry_run_target/AGENTS.md" ] || fail "dry-run changed a symlink"

(
    cd "$target"
    bash "$TEMPLATE_DIR/setup.sh" --force
) > "$TEST_DIR/force-install.txt"
assert_file_contains "$target/AGENTS.md" "AI Agent Workspace Rules"

symlink_target="$TEST_DIR/symlink-target"
mkdir -p "$symlink_target"
ln -s /private/tmp/external-agent-rules "$symlink_target/AGENTS.md"
(
    cd "$symlink_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/default-symlink.txt"
assert_file_contains "$TEST_DIR/default-symlink.txt" "SKIP (exists): AGENTS.md"
[ -L "$symlink_target/AGENTS.md" ] || fail "default install replaced a symlink"
[ -f "$symlink_target/docs/current/Vault Index MOC.md" ] || fail "default install did not copy docs beside a symlink"

hardlink_target="$TEST_DIR/hardlink-target"
outside_file="$TEST_DIR/outside-agent-rules"
mkdir -p "$hardlink_target"
printf 'outside file must not change\n' > "$outside_file"
ln "$outside_file" "$hardlink_target/AGENTS.md"
(
    cd "$hardlink_target"
    bash "$TEMPLATE_DIR/setup.sh" --force
) > "$TEST_DIR/hardlink.txt"
assert_file_contains "$outside_file" "outside file must not change"
assert_file_contains "$hardlink_target/AGENTS.md" "AI Agent Workspace Rules"

partial_target="$TEST_DIR/partial-target"
mkdir -p "$partial_target/docs/templates/feature-spec-template"
printf 'keep this file\n' > "$partial_target/AGENTS.md"
ln -s /private/tmp/not-a-template-file "$partial_target/docs/templates/feature-spec-template/1. Product Spec.md"
if (
    cd "$partial_target"
    bash "$TEMPLATE_DIR/setup.sh" --force
) > "$TEST_DIR/preflight.txt" 2>&1; then
    fail "force install accepted a symlinked destination"
fi
assert_file_contains "$TEST_DIR/preflight.txt" "No files were changed"
assert_file_contains "$partial_target/AGENTS.md" "keep this file"

ancestor_target="$TEST_DIR/ancestor-target"
outside_docs="$TEST_DIR/outside-docs"
mkdir -p "$ancestor_target" "$outside_docs"
ln -s "$outside_docs" "$ancestor_target/docs"
if (
    cd "$ancestor_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/ancestor-symlink.txt" 2>&1; then
    fail "default install accepted a symlinked parent directory"
fi
assert_file_contains "$TEST_DIR/ancestor-symlink.txt" "Refusing to write through symlink"
[ ! -e "$ancestor_target/AGENTS.md" ] || fail "preflight wrote before rejecting a parent symlink"
[ ! -e "$outside_docs/current/Vault Index MOC.md" ] || fail "installer wrote through a parent symlink"

collision_target="$TEST_DIR/collision-target"
mkdir -p "$collision_target/docs"
printf 'this must remain a file\n' > "$collision_target/docs/templates"
if (
    cd "$collision_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/path-collision.txt" 2>&1; then
    fail "install accepted a file where a template directory is required"
fi
assert_file_contains "$TEST_DIR/path-collision.txt" "Expected directory but found file"
assert_file_contains "$TEST_DIR/path-collision.txt" "No files were changed"
[ ! -e "$collision_target/AGENTS.md" ] || fail "preflight wrote before rejecting a file-directory collision"
[ ! -e "$collision_target/docs/current/Vault Index MOC.md" ] || fail "preflight copied docs before rejecting a file-directory collision"

echo "PASS: setup installer regression tests"
