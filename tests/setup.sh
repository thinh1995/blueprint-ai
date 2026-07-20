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

    grep -Fq -- "$expected" "$file" || fail "Expected '$expected' in $file"
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
expected_file_count=$((7 + core_doc_count))

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
[ -f "$target/GEMINI.md" ] || fail "default install did not copy GEMINI.md"
[ -f "$target/QWEN.md" ] || fail "default install did not copy QWEN.md"
assert_file_contains "$target/GEMINI.md" "AGENTS.md"
assert_file_contains "$target/GEMINI.md" "@AGENTS.md"
assert_file_contains "$target/QWEN.md" "AGENTS.md"
[ -f "$target/tools/validate-task-evidence.py" ] || fail "default install did not copy task-evidence validator"
[ -f "$target/tools/validate-docs.py" ] || fail "default install did not copy downstream docs validator"
python3 "$target/tools/validate-docs.py" || fail "downstream docs validator failed after default install"
python3 "$target/tools/validate-task-evidence.py" || fail "downstream task-evidence validator failed without task records"

selected_models_target="$TEST_DIR/selected-models-target"
mkdir -p "$selected_models_target"
(
    cd "$selected_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini,qwen
) > "$TEST_DIR/selected-models-install.txt"
assert_file_contains "$TEST_DIR/selected-models-install.txt" "Selected model runtimes: gemini,qwen"
[ -f "$selected_models_target/AGENTS.md" ] || fail "selected-model install did not copy canonical AGENTS.md"
[ -f "$selected_models_target/GEMINI.md" ] || fail "selected-model install did not copy GEMINI.md"
[ -f "$selected_models_target/QWEN.md" ] || fail "selected-model install did not copy QWEN.md"
[ ! -e "$selected_models_target/CLAUDE.md" ] || fail "selected-model install copied unselected CLAUDE.md"
python3 - "$selected_models_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["selected_models"] == ["gemini", "qwen"]
assert "CLAUDE.md" not in manifest["managed_paths"]
assert "CLAUDE.md" not in manifest["profiles"]["core"]
assert "GEMINI.md" in manifest["profiles"]["core"]
assert "QWEN.md" in manifest["profiles"]["core"]
PY

gemma_models_target="$TEST_DIR/gemma-models-target"
mkdir -p "$gemma_models_target"
(
    cd "$gemma_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemma
) > "$TEST_DIR/gemma-models-install.txt"
assert_file_contains "$TEST_DIR/gemma-models-install.txt" "Gemma/custom API selected"
[ ! -e "$gemma_models_target/CLAUDE.md" ] || fail "Gemma-only install copied CLAUDE.md"
[ ! -e "$gemma_models_target/GEMINI.md" ] || fail "Gemma-only install copied GEMINI.md"
[ ! -e "$gemma_models_target/QWEN.md" ] || fail "Gemma-only install copied QWEN.md"
python3 - "$gemma_models_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["selected_models"] == ["gemma"]
assert all(adapter not in manifest["profiles"]["core"] for adapter in ["CLAUDE.md", "GEMINI.md", "QWEN.md"])
PY

invalid_models_target="$TEST_DIR/invalid-models-target"
mkdir -p "$invalid_models_target"
if (
    cd "$invalid_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini,invalid
) > "$TEST_DIR/invalid-models.txt" 2>&1; then
    fail "setup accepted an invalid model selection"
fi
assert_file_contains "$TEST_DIR/invalid-models.txt" "Unknown model 'invalid'"
[ ! -e "$invalid_models_target/AGENTS.md" ] || fail "invalid model selection wrote files"

for empty_option in "--models=" "--models"; do
    empty_models_target="$TEST_DIR/empty-models-target-${empty_option//=/}"
    mkdir -p "$empty_models_target"
    if [ "$empty_option" = "--models" ]; then
        command=(bash "$TEMPLATE_DIR/setup.sh" "$empty_option" "")
    else
        command=(bash "$TEMPLATE_DIR/setup.sh" "$empty_option")
    fi
    if (
        cd "$empty_models_target"
        "${command[@]}"
    ) > "$TEST_DIR/empty-models.txt" 2>&1; then
        fail "setup accepted an empty model selection: $empty_option"
    fi
    assert_file_contains "$TEST_DIR/empty-models.txt" "--models requires"
    [ ! -e "$empty_models_target/AGENTS.md" ] || fail "empty model selection wrote files"
done

interactive_invalid_target="$TEST_DIR/interactive-invalid-target"
mkdir -p "$interactive_invalid_target"
if (
    cd "$interactive_invalid_target"
    printf '1,\n' | bash "$TEMPLATE_DIR/setup.sh" --interactive
) > "$TEST_DIR/interactive-invalid.txt" 2>&1; then
    fail "interactive setup accepted a trailing delimiter"
fi
assert_file_contains "$TEST_DIR/interactive-invalid.txt" "without empty values"
[ ! -e "$interactive_invalid_target/AGENTS.md" ] || fail "invalid interactive selection wrote files"

interactive_duplicate_target="$TEST_DIR/interactive-duplicate-target"
mkdir -p "$interactive_duplicate_target"
if (
    cd "$interactive_duplicate_target"
    printf '1,1\n' | bash "$TEMPLATE_DIR/setup.sh" --interactive
) > "$TEST_DIR/interactive-duplicate.txt" 2>&1; then
    fail "interactive setup accepted a duplicate selection"
fi
assert_file_contains "$TEST_DIR/interactive-duplicate.txt" "selected more than once"

interactive_success_target="$TEST_DIR/interactive-success-target"
mkdir -p "$interactive_success_target"
(
    cd "$interactive_success_target"
    printf '2,4\n' | bash "$TEMPLATE_DIR/setup.sh" --interactive
) > "$TEST_DIR/interactive-success.txt"
[ -f "$interactive_success_target/GEMINI.md" ] || fail "interactive setup did not install GEMINI.md"
[ ! -e "$interactive_success_target/CLAUDE.md" ] || fail "interactive setup installed unselected CLAUDE.md"
[ ! -e "$interactive_success_target/QWEN.md" ] || fail "interactive setup installed unselected QWEN.md"
python3 - "$interactive_success_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["requested_models"] == ["gemini", "gemma"]
assert manifest["managed_adapter_models"] == ["gemini"]
PY

repeated_models_target="$TEST_DIR/repeated-models-target"
mkdir -p "$repeated_models_target"
if (
    cd "$repeated_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini --models qwen
) > "$TEST_DIR/repeated-models.txt" 2>&1; then
    fail "setup accepted --models more than once"
fi
assert_file_contains "$TEST_DIR/repeated-models.txt" "can only be provided once"

incremental_models_target="$TEST_DIR/incremental-models-target"
mkdir -p "$incremental_models_target"
(
    cd "$incremental_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini,qwen
    bash "$TEMPLATE_DIR/setup.sh" --models claude
) > "$TEST_DIR/incremental-models.txt"
[ -f "$incremental_models_target/CLAUDE.md" ] || fail "incremental install did not add CLAUDE.md"
python3 - "$incremental_models_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["selected_models"] == ["claude", "gemini", "qwen"]
assert manifest["managed_adapter_models"] == ["claude", "gemini", "qwen"]
assert all(adapter in manifest["profiles"]["core"] for adapter in ["CLAUDE.md", "GEMINI.md", "QWEN.md"])
PY

incremental_dry_run_target="$TEST_DIR/incremental-dry-run-target"
mkdir -p "$incremental_dry_run_target"
(
    cd "$incremental_dry_run_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --models claude
) > "$TEST_DIR/incremental-dry-run.txt"
assert_file_contains "$TEST_DIR/incremental-dry-run.txt" "UPDATE: template-manifest.json"

user_owned_adapter_target="$TEST_DIR/user-owned-adapter-target"
mkdir -p "$user_owned_adapter_target"
printf 'user-owned adapter\n' > "$user_owned_adapter_target/GEMINI.md"
(
    cd "$user_owned_adapter_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/user-owned-adapter.txt"
python3 - "$user_owned_adapter_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["requested_models"] == ["gemini"]
assert manifest["managed_adapter_models"] == []
assert "GEMINI.md" not in manifest["managed_paths"]
PY
(
    cd "$user_owned_adapter_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/user-owned-adapter-update.txt"
assert_file_contains "$user_owned_adapter_target/GEMINI.md" "user-owned adapter"
user_owned_backup_dir="$(find "$user_owned_adapter_target" -maxdepth 1 -type d -name '.ai-template-backup.*' -print -quit)"
[ -n "$user_owned_backup_dir" ] || fail "user-owned adapter update did not create a backup for managed files"
[ ! -e "$user_owned_backup_dir/GEMINI.md" ] || fail "update backed up and replaced user-owned GEMINI.md"

custom_manifest_target="$TEST_DIR/custom-manifest-target"
mkdir -p "$custom_manifest_target"
(
    cd "$custom_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/custom-manifest-first.txt"
python3 - "$custom_manifest_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["custom_field"] = "preserve-me"
manifest["profiles"]["custom"] = ["custom/path"]
open(path, "w").write(json.dumps(manifest))
PY
(
    cd "$custom_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models claude
) > "$TEST_DIR/custom-manifest-second.txt"
python3 - "$custom_manifest_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["custom_field"] == "preserve-me"
assert manifest["profiles"]["custom"] == ["custom/path"]
PY

malformed_manifest_target="$TEST_DIR/malformed-manifest-target"
mkdir -p "$malformed_manifest_target"
printf '{"template":"ai-agent-obsidian-project-template"}\n' > "$malformed_manifest_target/template-manifest.json"
if (
    cd "$malformed_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/malformed-manifest.txt" 2>&1; then
    fail "setup accepted a malformed template-owned manifest"
fi
assert_file_contains "$TEST_DIR/malformed-manifest.txt" "invalid managed_paths"
[ ! -e "$malformed_manifest_target/AGENTS.md" ] || fail "malformed manifest allowed partial install"
if (
    cd "$malformed_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --models gemini
) > "$TEST_DIR/malformed-manifest-dry-run.txt" 2>&1; then
    fail "dry-run accepted a malformed template-owned manifest"
fi

unmanaged_manifest_target="$TEST_DIR/unmanaged-manifest-target"
mkdir -p "$unmanaged_manifest_target"
printf '{"template":"user-owned","custom":true}\n' > "$unmanaged_manifest_target/template-manifest.json"
(
    cd "$unmanaged_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/unmanaged-manifest.txt"
assert_file_contains "$TEST_DIR/unmanaged-manifest.txt" "SKIP (unmanaged manifest)"
assert_file_contains "$unmanaged_manifest_target/template-manifest.json" '"template":"user-owned"'
[ -f "$unmanaged_manifest_target/GEMINI.md" ] || fail "unmanaged manifest blocked selected adapter install"

upgrade_manifest_target="$TEST_DIR/upgrade-manifest-target"
mkdir -p "$upgrade_manifest_target"
(
    cd "$upgrade_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/upgrade-manifest-first.txt"
python3 - "$upgrade_manifest_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["version"] = "0.3.0"
manifest["profiles"]["core"] = [path for path in manifest["profiles"]["core"] if "Model Runtime Instructions" not in path]
open(path, "w").write(json.dumps(manifest))
PY
(
    cd "$upgrade_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models claude
) > "$TEST_DIR/upgrade-manifest-second.txt"
python3 - "$upgrade_manifest_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["version"] == "0.4.0"
assert "docs/current/00 - Onboarding/5. Model Runtime Instructions.md" in manifest["profiles"]["core"]
PY

selected_adapter_directory_target="$TEST_DIR/selected-adapter-directory-target"
mkdir -p "$selected_adapter_directory_target/GEMINI.md"
printf 'preserve this file\n' > "$selected_adapter_directory_target/AGENTS.md"
if (
    cd "$selected_adapter_directory_target"
    bash "$TEMPLATE_DIR/setup.sh" --force --models gemini
) > "$TEST_DIR/selected-adapter-directory.txt" 2>&1; then
    fail "force install accepted a directory where a selected adapter file is required"
fi
assert_file_contains "$TEST_DIR/selected-adapter-directory.txt" "Expected file but found directory"
assert_file_contains "$selected_adapter_directory_target/AGENTS.md" "preserve this file"
[ -d "$selected_adapter_directory_target/GEMINI.md" ] || fail "selected adapter directory was changed"

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

if MMDC_BIN=true MMDC_PUPPETEER_CONFIG=tests/missing-puppeteer-config.json bash "$TEMPLATE_DIR/tests/render-mermaid.sh" > "$TEST_DIR/missing-puppeteer-config-output.txt" 2>&1; then
    fail "Mermaid renderer accepted a missing Puppeteer config"
fi
assert_file_contains "$TEST_DIR/missing-puppeteer-config-output.txt" "Missing Puppeteer config"

[ ! -e "$target/.agents/AGENTS.md" ] || fail "default install copied optional nested AGENTS.md"
assert_file_matches "$target/template-manifest.json" '"version"[[:space:]]*:[[:space:]]*"[0-9]+\.[0-9]+\.[0-9]+"'
python3 -m json.tool "$target/template-manifest.json" >/dev/null || fail "installer wrote invalid manifest JSON"
for managed_path in "AGENTS.md" "CLAUDE.md" "GEMINI.md" "QWEN.md" "template-manifest.json" "tools/validate-task-evidence.py" "tools/validate-docs.py" "docs/current" "docs/templates"; do
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
for template_file in setup.sh template-paths.sh AGENTS.md CLAUDE.md GEMINI.md QWEN.md template-manifest.json; do
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

update_target="$TEST_DIR/update-target"
mkdir -p "$update_target"
(
    cd "$update_target"
    bash "$TEMPLATE_DIR/setup.sh" --with-advanced-docs --with-legacy-agents
) > "$TEST_DIR/update-first-install.txt"
printf 'custom managed rules\n' > "$update_target/AGENTS.md"
printf 'custom managed documentation prompt\n' > "$update_target/docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md"
printf 'custom managed advanced documentation\n' > "$update_target/docs/current/03 - API & Integrations/API Reference.md"
printf 'custom managed legacy rules\n' > "$update_target/.agents/AGENTS.md"
python3 - "$update_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["version"] = "0.3.1"
open(path, "w").write(json.dumps(manifest))
PY
(
    cd "$update_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --update
) > "$TEST_DIR/update-dry-run.txt"
assert_file_contains "$TEST_DIR/update-dry-run.txt" "Update mode: existing managed files will be backed up then replaced."
assert_file_contains "$TEST_DIR/update-dry-run.txt" "UPDATE (backup): AGENTS.md"
[ -z "$(find "$update_target" -maxdepth 1 -type d -name '.ai-template-backup.*' -print -quit)" ] || fail "dry-run update created a backup"
assert_file_contains "$update_target/AGENTS.md" "custom managed rules"
(
    cd "$update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/update.txt"
assert_file_contains "$TEST_DIR/update.txt" "BACKUP:"
assert_file_contains "$update_target/AGENTS.md" "AI Agent Workspace Rules"
assert_file_contains "$update_target/docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "BẮT BUỘC tạo"
assert_file_contains "$update_target/docs/current/03 - API & Integrations/API Reference.md" "# API Reference"
assert_file_contains "$update_target/.agents/AGENTS.md" "AI Agent Workspace Rules"
update_backup_dir="$(find "$update_target" -maxdepth 1 -type d -name '.ai-template-backup.*' -print -quit)"
[ -n "$update_backup_dir" ] || fail "update did not create a backup directory"
assert_file_contains "$update_backup_dir/AGENTS.md" "custom managed rules"
assert_file_contains "$update_backup_dir/docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md" "custom managed documentation prompt"
assert_file_contains "$update_backup_dir/docs/current/03 - API & Integrations/API Reference.md" "custom managed advanced documentation"
assert_file_contains "$update_backup_dir/.agents/AGENTS.md" "custom managed legacy rules"
assert_file_contains "$update_backup_dir/RECOVERY.md" "mix of versions"
python3 - "$update_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["version"] == "0.4.0"
PY

update_without_manifest_target="$TEST_DIR/update-without-manifest-target"
mkdir -p "$update_without_manifest_target"
if (
    cd "$update_without_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/update-without-manifest.txt" 2>&1; then
    fail "update accepted a target without a manifest"
fi
assert_file_contains "$TEST_DIR/update-without-manifest.txt" "--update requires"
[ ! -e "$update_without_manifest_target/AGENTS.md" ] || fail "update without manifest wrote files"

if (
    cd "$update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --models gemini
) > "$TEST_DIR/update-models.txt" 2>&1; then
    fail "update accepted an explicit model selection"
fi
assert_file_contains "$TEST_DIR/update-models.txt" "derives runtime adapters"

core_only_update_target="$TEST_DIR/core-only-update-target"
mkdir -p "$core_only_update_target"
(
    cd "$core_only_update_target"
    bash "$TEMPLATE_DIR/setup.sh"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/core-only-update.txt"
[ ! -e "$core_only_update_target/docs/current/03 - API & Integrations/API Reference.md" ] || fail "core-only update installed an unselected advanced profile"
[ ! -e "$core_only_update_target/.agents/AGENTS.md" ] || fail "core-only update installed an unselected legacy profile"

legacy_manifest_update_target="$TEST_DIR/legacy-manifest-update-target"
mkdir -p "$legacy_manifest_update_target"
(
    cd "$legacy_manifest_update_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/legacy-manifest-first-install.txt"
python3 - "$legacy_manifest_update_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest.pop("managed_profiles", None)
open(path, "w").write(json.dumps(manifest))
PY
(
    cd "$legacy_manifest_update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/legacy-manifest-bare-update.txt"
[ ! -e "$legacy_manifest_update_target/docs/current/03 - API & Integrations/API Reference.md" ] || fail "legacy bare update installed advanced profile"
[ ! -e "$legacy_manifest_update_target/.agents/AGENTS.md" ] || fail "legacy bare update installed legacy profile"
(
    cd "$legacy_manifest_update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --with-advanced-docs
) > "$TEST_DIR/legacy-manifest-advanced-update.txt"
[ -f "$legacy_manifest_update_target/docs/current/03 - API & Integrations/API Reference.md" ] || fail "legacy explicit advanced update did not install advanced profile"
[ ! -e "$legacy_manifest_update_target/.agents/AGENTS.md" ] || fail "legacy explicit advanced update installed legacy profile"
(
    cd "$legacy_manifest_update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --with-legacy-agents
) > "$TEST_DIR/legacy-manifest-legacy-update.txt"
[ -f "$legacy_manifest_update_target/.agents/AGENTS.md" ] || fail "legacy explicit legacy update did not install legacy profile"
python3 - "$legacy_manifest_update_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["managed_profiles"] == ["core", "--with-advanced-docs", "--with-legacy-agents"]
PY

strict_evidence_dir="$TEST_DIR/strict-evidence"
mkdir -p "$strict_evidence_dir"
strict_source_revision="$(git -C "$TEMPLATE_DIR" rev-list --max-parents=0 HEAD)"
strict_checksum="$(shasum -a 256 "$TEMPLATE_DIR/V4_ACCEPTANCE_MATRIX.md" | awk '{print $1}')"
printf '%s\n' \
    '---' \
    'status: completed' \
    'task_id: strict-working-tree-fixture' \
    'recorded_at: 2026-07-20' \
    'recorded_by: fixture' \
    "source_revision: $strict_source_revision" \
    'completed_at: 2026-07-20T00:00:00Z' \
    'reviewer: fixture' \
    'environment: local/dev' \
    "output_artifact_sha256: $strict_checksum" \
    'output_artifact_path: V4_ACCEPTANCE_MATRIX.md' \
    '---' \
    '| AC-01 | fixture | fixture | PASS / 0 |' \
    > "$strict_evidence_dir/working-tree-fallback.md"
if python3 "$TEMPLATE_DIR/tests/validate-task-evidence.py" --evidence-dir "$strict_evidence_dir" --require-completed > "$TEST_DIR/strict-evidence-output.txt" 2>&1; then
    fail "task evidence validator accepted a working-tree artifact missing from source revision"
fi

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
