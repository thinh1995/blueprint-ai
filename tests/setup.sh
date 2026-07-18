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
done < <(find "$TEMPLATE_DIR/docs" -type f ! -name '.DS_Store')
expected_file_count=$((4 + core_doc_count))

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
for sample_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md"; do
    [ -f "$target/docs/current/05 - Product Features/Example AI Support Agent/$sample_file" ] || fail "default install did not copy AI Agent sample: $sample_file"
done
[ -f "$target/template-manifest.json" ] || fail "default install did not copy template manifest"
[ -f "$target/CLAUDE.md" ] || fail "default install did not copy CLAUDE.md"
[ -f "$target/tools/validate-task-evidence.py" ] || fail "default install did not copy task-evidence validator"
[ ! -e "$target/.agents/AGENTS.md" ] || fail "default install copied optional nested AGENTS.md"
assert_file_matches "$target/template-manifest.json" '"version"[[:space:]]*:[[:space:]]*"[0-9]+\.[0-9]+\.[0-9]+"'
python3 -m json.tool "$target/template-manifest.json" >/dev/null || fail "installer wrote invalid manifest JSON"
for managed_path in "AGENTS.md" "CLAUDE.md" "template-manifest.json" "tools/validate-task-evidence.py" "docs/current"; do
    assert_file_contains "$target/template-manifest.json" "\"$managed_path\""
done
[ "$(file_mode "$target/AGENTS.md")" = "$(file_mode "$TEMPLATE_DIR/AGENTS.md")" ] || fail "installer changed AGENTS.md mode"
[ "$(file_mode "$target/docs/current/Vault Index MOC.md")" = "$(file_mode "$TEMPLATE_DIR/docs/current/Vault Index MOC.md")" ] || fail "installer changed docs mode"

metadata_template="$TEST_DIR/template-with-metadata"
metadata_target="$TEST_DIR/metadata-target"
mkdir -p "$metadata_template/tests" "$metadata_target"
for template_file in setup.sh template-paths.sh AGENTS.md CLAUDE.md template-manifest.json; do
    cp "$TEMPLATE_DIR/$template_file" "$metadata_template/$template_file"
done
cp "$TEMPLATE_DIR/tests/validate-task-evidence.py" "$metadata_template/tests/validate-task-evidence.py"
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
[ -f "$target/docs/current/02 - Architecture/Generated Reference Inventory.md" ] || fail "core install did not copy generated inventory"

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
mkdir -p "$partial_target/docs/current/05 - Product Features/_Feature Template"
printf 'keep this file\n' > "$partial_target/AGENTS.md"
ln -s /private/tmp/not-a-template-file "$partial_target/docs/current/05 - Product Features/_Feature Template/1. Product Spec.md"
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
mkdir -p "$collision_target/docs/current"
printf 'this must remain a file\n' > "$collision_target/docs/current/05 - Product Features"
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
