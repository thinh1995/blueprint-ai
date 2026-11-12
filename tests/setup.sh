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
expected_file_count=$((11 + core_doc_count))

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
[ -f "$target/docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md" ] || fail "default install did not copy Spec-Driven Feature Prompts"
[ -f "$target/docs/current/05 - Product Features/README.md" ] || fail "default install did not create Product Features workspace"
for template_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md" "4. Tasks.md" "README.md"; do
    [ -f "$target/docs/templates/feature-spec-template/$template_file" ] || fail "default install did not copy feature template: $template_file"
done
for sample_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md" "4. Tasks.md"; do
    [ -f "$target/docs/templates/examples/ai-support-agent/$sample_file" ] || fail "default install did not copy AI Agent sample: $sample_file"
done
[ -f "$target/docs/templates/3. Task Evidence Template.md" ] || fail "default install did not copy task evidence template"
[ -d "$target/task-evidence" ] || fail "default install did not create root task-evidence directory"
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
assert_file_contains "$target/GEMINI.md" "Antigravity CLI Project Instructions"
assert_file_contains "$target/GEMINI.md" "AGENTS.md"
assert_file_contains "$target/GEMINI.md" "@AGENTS.md"
assert_file_contains "$target/QWEN.md" "AGENTS.md"
[ -f "$target/tools/validate-task-evidence.py" ] || fail "default install did not copy task-evidence validator"
[ -f "$target/tools/docs_validation.py" ] || fail "default install did not copy shared documentation validator"
[ -f "$target/tools/validate-docs.py" ] || fail "default install did not copy downstream docs validator"
[ -f "$target/tools/new-feature.py" ] || fail "default install did not copy feature scaffolder"
[ -f "$target/tools/export-tasks.py" ] || fail "default install did not copy task exporter"
python3 "$target/tools/validate-docs.py" || fail "downstream docs validator failed after default install"
python3 "$target/tools/validate-task-evidence.py" || fail "downstream task-evidence validator failed without task records"

selected_models_target="$TEST_DIR/selected-models-target"
mkdir -p "$selected_models_target"
(
    cd "$selected_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity,qwen
) > "$TEST_DIR/selected-models-install.txt"
assert_file_contains "$TEST_DIR/selected-models-install.txt" "Selected model runtimes: antigravity,qwen"
[ -f "$selected_models_target/AGENTS.md" ] || fail "selected-model install did not copy canonical AGENTS.md"
[ -f "$selected_models_target/GEMINI.md" ] || fail "selected-model install did not copy GEMINI.md"
[ -f "$selected_models_target/QWEN.md" ] || fail "selected-model install did not copy QWEN.md"
[ ! -e "$selected_models_target/CLAUDE.md" ] || fail "selected-model install copied unselected CLAUDE.md"
python3 - "$selected_models_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["selected_models"] == ["antigravity", "qwen"]
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
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity,invalid
) > "$TEST_DIR/invalid-models.txt" 2>&1; then
    fail "setup accepted an invalid model selection"
fi
assert_file_contains "$TEST_DIR/invalid-models.txt" "Unknown model 'invalid'"
[ ! -e "$invalid_models_target/AGENTS.md" ] || fail "invalid model selection wrote files"

removed_model_target="$TEST_DIR/removed-model-target"
mkdir -p "$removed_model_target"
if (
    cd "$removed_model_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemini
) > "$TEST_DIR/removed-model.txt" 2>&1; then
    fail "setup accepted removed gemini model selection"
fi
assert_file_contains "$TEST_DIR/removed-model.txt" "Unknown model 'gemini'"
[ ! -e "$removed_model_target/AGENTS.md" ] || fail "removed model selection wrote files"

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
assert manifest["requested_models"] == ["antigravity", "gemma"]
assert manifest["managed_adapter_models"] == ["antigravity"]
PY

repeated_models_target="$TEST_DIR/repeated-models-target"
mkdir -p "$repeated_models_target"
if (
    cd "$repeated_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity --models qwen
) > "$TEST_DIR/repeated-models.txt" 2>&1; then
    fail "setup accepted --models more than once"
fi
assert_file_contains "$TEST_DIR/repeated-models.txt" "can only be provided once"

incremental_models_target="$TEST_DIR/incremental-models-target"
mkdir -p "$incremental_models_target"
(
    cd "$incremental_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity,qwen
    bash "$TEMPLATE_DIR/setup.sh" --models claude
) > "$TEST_DIR/incremental-models.txt"
[ -f "$incremental_models_target/CLAUDE.md" ] || fail "incremental install did not add CLAUDE.md"
python3 - "$incremental_models_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["selected_models"] == ["claude", "antigravity", "qwen"]
assert manifest["managed_adapter_models"] == ["claude", "antigravity", "qwen"]
assert all(adapter in manifest["profiles"]["core"] for adapter in ["CLAUDE.md", "GEMINI.md", "QWEN.md"])
PY

incremental_dry_run_target="$TEST_DIR/incremental-dry-run-target"
mkdir -p "$incremental_dry_run_target"
(
    cd "$incremental_dry_run_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --models claude
) > "$TEST_DIR/incremental-dry-run.txt"
assert_file_contains "$TEST_DIR/incremental-dry-run.txt" "UPDATE: template-manifest.json"

user_owned_adapter_target="$TEST_DIR/user-owned-adapter-target"
mkdir -p "$user_owned_adapter_target"
printf 'user-owned adapter\n' > "$user_owned_adapter_target/GEMINI.md"
(
    cd "$user_owned_adapter_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
) > "$TEST_DIR/user-owned-adapter.txt"
python3 - "$user_owned_adapter_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
assert manifest["requested_models"] == ["antigravity"]
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
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
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

unsafe_update_target="$TEST_DIR/unsafe-update-target"
mkdir -p "$unsafe_update_target"
(
    cd "$unsafe_update_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/unsafe-update-first.txt"
printf 'preserve me\n' > "$unsafe_update_target/AGENTS.md"
python3 - "$unsafe_update_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["profiles"]["--with-legacy-agents"] = ["../escape"]
manifest["managed_paths"].append("../escape")
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$unsafe_update_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/unsafe-update-output.txt" 2>&1; then
    fail "update accepted unsafe destination manifest paths"
fi
assert_file_contains "$TEST_DIR/unsafe-update-output.txt" "valid template-owned template-manifest"
assert_file_contains "$unsafe_update_target/AGENTS.md" "preserve me"

malformed_manifest_target="$TEST_DIR/malformed-manifest-target"
mkdir -p "$malformed_manifest_target"
printf '{"template":"ai-agent-obsidian-project-template"}\n' > "$malformed_manifest_target/template-manifest.json"
if (
    cd "$malformed_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
) > "$TEST_DIR/malformed-manifest.txt" 2>&1; then
    fail "setup accepted a malformed template-owned manifest"
fi
assert_file_contains "$TEST_DIR/malformed-manifest.txt" "invalid managed_paths"
[ ! -e "$malformed_manifest_target/AGENTS.md" ] || fail "malformed manifest allowed partial install"
if (
    cd "$malformed_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --models antigravity
) > "$TEST_DIR/malformed-manifest-dry-run.txt" 2>&1; then
    fail "dry-run accepted a malformed template-owned manifest"
fi

unmanaged_manifest_target="$TEST_DIR/unmanaged-manifest-target"
mkdir -p "$unmanaged_manifest_target"
printf '{"template":"user-owned","custom":true}\n' > "$unmanaged_manifest_target/template-manifest.json"
(
    cd "$unmanaged_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
) > "$TEST_DIR/unmanaged-manifest.txt"
assert_file_contains "$TEST_DIR/unmanaged-manifest.txt" "SKIP (unmanaged manifest)"
assert_file_contains "$unmanaged_manifest_target/template-manifest.json" '"template":"user-owned"'
[ -f "$unmanaged_manifest_target/GEMINI.md" ] || fail "unmanaged manifest blocked selected adapter install"

upgrade_manifest_target="$TEST_DIR/upgrade-manifest-target"
mkdir -p "$upgrade_manifest_target"
(
    cd "$upgrade_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity
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
python3 - "$upgrade_manifest_target/template-manifest.json" "$TEMPLATE_DIR/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
template = json.load(open(sys.argv[2]))
assert manifest["version"] == template["version"]
assert "docs/current/00 - Onboarding/5. Model Runtime Instructions.md" in manifest["profiles"]["core"]
PY

selected_adapter_directory_target="$TEST_DIR/selected-adapter-directory-target"
mkdir -p "$selected_adapter_directory_target/GEMINI.md"
printf 'preserve this file\n' > "$selected_adapter_directory_target/AGENTS.md"
if (
    cd "$selected_adapter_directory_target"
    bash "$TEMPLATE_DIR/setup.sh" --force --models antigravity
) > "$TEST_DIR/selected-adapter-directory.txt" 2>&1; then
    fail "force install accepted a directory where a selected adapter file is required"
fi
assert_file_contains "$TEST_DIR/selected-adapter-directory.txt" "Expected file but found directory"
assert_file_contains "$selected_adapter_directory_target/AGENTS.md" "preserve this file"
[ -d "$selected_adapter_directory_target/GEMINI.md" ] || fail "selected adapter directory was changed"

link_boundary_target="$TEST_DIR/link-boundary-target"
mkdir -p "$link_boundary_target/docs/current" "$link_boundary_target/tools"
cp "$TEMPLATE_DIR/tests/docs_validation.py" "$link_boundary_target/tools/docs_validation.py"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$link_boundary_target/tools/validate-docs.py"
printf 'outside fixture root\n' > "$TEST_DIR/outside-fixture.md"
printf '[outside](../../../outside-fixture.md)\n' > "$link_boundary_target/docs/current/escaping-link.md"
if python3 "$link_boundary_target/tools/validate-docs.py" > "$TEST_DIR/link-boundary-output.txt" 2>&1; then
    fail "downstream docs validator accepted a Markdown link outside the project root"
fi
assert_file_contains "$TEST_DIR/link-boundary-output.txt" "escapes project root"

file_uri_target="$TEST_DIR/file-uri-target"
mkdir -p "$file_uri_target/docs/current" "$file_uri_target/tools"
cp "$TEMPLATE_DIR/tests/docs_validation.py" "$file_uri_target/tools/docs_validation.py"
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
for managed_path in "AGENTS.md" "CLAUDE.md" "GEMINI.md" "QWEN.md" "template-manifest.json" "tools/validate-task-evidence.py" "tools/docs_validation.py" "tools/validate-docs.py" "tools/new-feature.py" "tools/export-tasks.py" "task-evidence" "docs/current" "docs/templates"; do
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
    "tools/docs_validation.py": "tests/docs_validation.py",
    "tools/validate-docs.py": "tests/validate-project-docs.py",
    "tools/new-feature.py": "tests/new-feature.py",
    "tools/export-tasks.py": "tests/export-tasks.py",
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
mkdir -p "$metadata_template/tests" "$metadata_template/task-evidence" "$metadata_target"
for template_file in setup.sh template-paths.sh AGENTS.md CLAUDE.md GEMINI.md QWEN.md template-manifest.json; do
    cp "$TEMPLATE_DIR/$template_file" "$metadata_template/$template_file"
done
cp "$TEMPLATE_DIR/tests/validate-task-evidence.py" "$metadata_template/tests/validate-task-evidence.py"
cp "$TEMPLATE_DIR/tests/docs_validation.py" "$metadata_template/tests/docs_validation.py"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$metadata_template/tests/validate-project-docs.py"
cp "$TEMPLATE_DIR/tests/new-feature.py" "$metadata_template/tests/new-feature.py"
cp "$TEMPLATE_DIR/tests/export-tasks.py" "$metadata_template/tests/export-tasks.py"
cp -R "$TEMPLATE_DIR/docs" "$metadata_template/docs"
touch "$metadata_template/task-evidence/.gitkeep"
printf 'finder metadata\n' > "$metadata_template/docs/.DS_Store"
(
    cd "$metadata_target"
    bash "$metadata_template/setup.sh"
) > "$TEST_DIR/metadata-filter.txt"
[ ! -e "$metadata_target/docs/.DS_Store" ] || fail "installer copied .DS_Store metadata"

invalid_profile_template="$TEST_DIR/invalid-profile-template"
invalid_profile_target="$TEST_DIR/invalid-profile-target"
mkdir -p "$invalid_profile_template/tests" "$invalid_profile_template/task-evidence" "$invalid_profile_target"
for template_file in setup.sh template-paths.sh AGENTS.md CLAUDE.md GEMINI.md QWEN.md template-manifest.json; do
    cp "$TEMPLATE_DIR/$template_file" "$invalid_profile_template/$template_file"
done
cp "$TEMPLATE_DIR/tests/validate-task-evidence.py" "$invalid_profile_template/tests/validate-task-evidence.py"
cp "$TEMPLATE_DIR/tests/docs_validation.py" "$invalid_profile_template/tests/docs_validation.py"
cp "$TEMPLATE_DIR/tests/validate-project-docs.py" "$invalid_profile_template/tests/validate-project-docs.py"
cp "$TEMPLATE_DIR/tests/new-feature.py" "$invalid_profile_template/tests/new-feature.py"
cp "$TEMPLATE_DIR/tests/export-tasks.py" "$invalid_profile_template/tests/export-tasks.py"
cp -R "$TEMPLATE_DIR/docs" "$invalid_profile_template/docs"
touch "$invalid_profile_template/task-evidence/.gitkeep"
python3 - "$invalid_profile_template/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["profiles"]["--with-legacy-agents"] = ["../../outside-target"]
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$invalid_profile_target"
    bash "$invalid_profile_template/setup.sh" --with-legacy-agents
) > "$TEST_DIR/invalid-profile-output.txt" 2>&1; then
    fail "installer accepted an unsafe source profile path"
fi
assert_file_contains "$TEST_DIR/invalid-profile-output.txt" "invalid profile paths"
[ ! -e "$TEST_DIR/outside-target" ] || fail "unsafe source profile wrote outside destination"
[ -z "$(find "$invalid_profile_target" -type f -print -quit)" ] || fail "invalid source profile wrote destination files"

invalid_control_target="$TEST_DIR/invalid-control-target"
mkdir -p "$invalid_control_target"
cp "$TEMPLATE_DIR/template-manifest.json" "$invalid_profile_template/template-manifest.json"
python3 - "$invalid_profile_template/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["profiles"]["--with-legacy-agents"] = [".agents/AGENTS.md\n../outside-control"]
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$invalid_control_target"
    bash "$invalid_profile_template/setup.sh" --with-legacy-agents
) > "$TEST_DIR/invalid-control-output.txt" 2>&1; then
    fail "installer accepted a control character in a source profile path"
fi
assert_file_contains "$TEST_DIR/invalid-control-output.txt" "control character"
[ ! -e "$TEST_DIR/outside-control" ] || fail "control-character profile wrote outside destination"
[ -z "$(find "$invalid_control_target" -type f -print -quit)" ] || fail "control-character profile wrote destination files"

overlap_profile_target="$TEST_DIR/overlap-profile-target"
mkdir -p "$overlap_profile_target"
cp "$TEMPLATE_DIR/template-manifest.json" "$invalid_profile_template/template-manifest.json"
python3 - "$invalid_profile_template/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["profiles"]["--with-advanced-docs"].append("docs/templates/1. Agent System Prompt Template.md")
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$overlap_profile_target"
    bash "$invalid_profile_template/setup.sh"
) > "$TEST_DIR/overlap-profile-output.txt" 2>&1; then
    fail "installer accepted overlapping profile paths"
fi
assert_file_contains "$TEST_DIR/overlap-profile-output.txt" "profile paths overlap"
[ -z "$(find "$overlap_profile_target" -type f -print -quit)" ] || fail "overlapping source profile wrote destination files"

invalid_schema_target="$TEST_DIR/invalid-schema-target"
mkdir -p "$invalid_schema_target"
python3 - "$invalid_profile_template/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["managed_paths"] = None
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$invalid_schema_target"
    bash "$invalid_profile_template/setup.sh"
) > "$TEST_DIR/invalid-schema-output.txt" 2>&1; then
    fail "installer accepted an invalid source manifest schema"
fi
assert_file_contains "$TEST_DIR/invalid-schema-output.txt" "invalid profile paths"
[ -z "$(find "$invalid_schema_target" -type f -print -quit)" ] || fail "invalid source manifest schema wrote destination files"

unprofiled_template="$TEST_DIR/unprofiled-template"
unprofiled_target="$TEST_DIR/unprofiled-target"
cp -R "$TEMPLATE_DIR" "$unprofiled_template"
mkdir -p "$unprofiled_target"
printf '# Unprofiled fixture\n' > "$unprofiled_template/docs/current/unprofiled-fixture.md"
if (
    cd "$unprofiled_target"
    bash "$unprofiled_template/setup.sh"
) > "$TEST_DIR/unprofiled-output.txt" 2>&1; then
    fail "installer accepted documentation missing from every profile"
fi
assert_file_contains "$TEST_DIR/unprofiled-output.txt" "not declared by a profile"
[ -z "$(find "$unprofiled_target" -type f -print -quit)" ] || fail "unprofiled template documentation wrote destination files"

validator_conflict_target="$TEST_DIR/validator-conflict-target"
mkdir -p "$validator_conflict_target/tools"
printf '# user-owned validator helper\n' > "$validator_conflict_target/tools/docs_validation.py"
(
    cd "$validator_conflict_target"
    bash "$TEMPLATE_DIR/setup.sh"
) > "$TEST_DIR/validator-conflict-output.txt"
assert_file_contains "$TEST_DIR/validator-conflict-output.txt" "SKIP (validator bundle conflict)"
assert_file_contains "$validator_conflict_target/tools/docs_validation.py" "user-owned validator helper"
[ ! -e "$validator_conflict_target/tools/validate-docs.py" ] || fail "validator bundle was partially installed"
python3 - "$validator_conflict_target/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
for path in ["tools/docs_validation.py", "tools/validate-docs.py"]:
    assert path not in manifest["managed_paths"]
    assert path not in manifest["profiles"]["core"]
PY
(
    cd "$validator_conflict_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/validator-conflict-update-output.txt"
assert_file_contains "$TEST_DIR/validator-conflict-update-output.txt" "SKIP (validator bundle conflict)"
assert_file_contains "$validator_conflict_target/tools/docs_validation.py" "user-owned validator helper"
[ ! -e "$validator_conflict_target/tools/validate-docs.py" ] || fail "update installed half of an unmanaged validator bundle"

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
git -C "$update_target" init -q
git -C "$update_target" config user.email "template-test@example.invalid"
git -C "$update_target" config user.name "Template Test"
git -C "$update_target" add .
git -C "$update_target" commit -qm "initial template install"
legacy_revision="$(git -C "$update_target" rev-parse HEAD)"
legacy_checksum="$(shasum -a 256 "$update_target/AGENTS.md" | awk '{print $1}')"
mkdir -p "$update_target/docs/current/00 - Onboarding/task-evidence"
printf '%s\n' \
    '---' \
    'status: completed' \
    'task_id: legacy-evidence' \
    'recorded_at: 2026-07-21' \
    'recorded_by: template test' \
    "source_revision: $legacy_revision" \
    'completed_at: 2026-07-21' \
    'reviewer: template test' \
    'environment: local/dev' \
    "output_artifact_sha256: $legacy_checksum" \
    'output_artifact_path: AGENTS.md' \
    '---' \
    '# Legacy evidence' \
    '' \
    '| AC-01 | Preserve legacy evidence | validator | Pass / 0 |' \
    > "$update_target/docs/current/00 - Onboarding/task-evidence/legacy-evidence.md"
printf 'custom managed rules\n' > "$update_target/AGENTS.md"
printf 'custom managed documentation prompt\n' > "$update_target/docs/current/00 - Onboarding/4. Whole-Project Documentation Update Prompt.md"
printf 'custom managed advanced documentation\n' > "$update_target/docs/current/03 - API & Integrations/API Reference.md"
printf 'custom managed legacy rules\n' > "$update_target/.agents/AGENTS.md"
python3 - "$update_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["version"] = "0.4.2"
for key in ["requested_models", "selected_models", "managed_adapter_models"]:
    manifest[key] = ["gemini" if model == "antigravity" else model for model in manifest.get(key, [])]
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
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan migration-plan.json
) > "$TEST_DIR/update-plan.txt"
[ -f "$update_target/migration-plan.json" ] || fail "migration planner did not write JSON output"
python3 - "$update_target/migration-plan.json" <<'PY'
import json
import sys

plan = json.load(open(sys.argv[1]))
assert plan["mode"] == "dry-run-update"
assert any(item["path"] == "AGENTS.md" for item in plan["will_replace"])
assert ".ai-template-backup.XXXXXX" in plan["backup_directory_pattern"]
assert "RECOVERY.md" in plan["rollback"]
PY
assert_file_contains "$TEST_DIR/update-plan.txt" "Migration plan: migration-plan.json"
assert_file_contains "$TEST_DIR/update-plan.txt" "no template-managed files will be changed"
(
    cd "$update_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan migration-plan.md
) > "$TEST_DIR/update-plan-markdown.txt"
assert_file_contains "$update_target/migration-plan.md" "# AI Template Migration Plan"
assert_file_contains "$update_target/migration-plan.md" "## Will replace"
assert_file_contains "$update_target/migration-plan.md" "RECOVERY.md"
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
python3 "$update_target/tools/validate-task-evidence.py" --require-completed > "$TEST_DIR/legacy-evidence-update.txt"
assert_file_contains "$TEST_DIR/legacy-evidence-update.txt" "WARN: validating legacy evidence directory during migration"
assert_file_contains "$TEST_DIR/legacy-evidence-update.txt" "PASS: task evidence and inventory validation"
python3 - "$update_target/template-manifest.json" "$TEMPLATE_DIR/template-manifest.json" <<'PY'
import json
import sys

manifest = json.load(open(sys.argv[1]))
template = json.load(open(sys.argv[2]))
assert manifest["version"] == template["version"]
PY

if (
    cd "$gemma_models_target"
    bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-gemma.txt" 2>&1; then
    fail "doctor accepted a Gemma runtime without host-level injection verification"
fi
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "PASS Bash:"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "PASS Python:"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "PASS policy:"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "PASS manifest: template-owned"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "FAIL runtime gemma: host-level system-prompt injection cannot be verified"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "PASS docs links:"
assert_file_contains "$TEST_DIR/doctor-gemma.txt" "Doctor result: NOT READY"

doctor_unmanaged_adapter_target="$TEST_DIR/doctor-unmanaged-adapter"
mkdir -p "$doctor_unmanaged_adapter_target"
(
    cd "$doctor_unmanaged_adapter_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemma >/dev/null
)
python3 - "$doctor_unmanaged_adapter_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["requested_models"] = ["claude"]
manifest["selected_models"] = ["claude"]
manifest["managed_adapter_models"] = []
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$doctor_unmanaged_adapter_target"
    bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-unmanaged-adapter.txt" 2>&1; then
    fail "doctor accepted a selected runtime with no user-owned adapter"
fi
assert_file_contains "$TEST_DIR/doctor-unmanaged-adapter.txt" "WARN runtime claude: adapter is user-owned"
assert_file_contains "$TEST_DIR/doctor-unmanaged-adapter.txt" "FAIL runtime claude: missing regular CLAUDE.md"
assert_file_contains "$TEST_DIR/doctor-unmanaged-adapter.txt" "Doctor result: NOT READY"

doctor_unsafe_manifest_target="$TEST_DIR/doctor-unsafe-manifest"
mkdir -p "$doctor_unsafe_manifest_target"
(
    cd "$doctor_unsafe_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --models gemma >/dev/null
)
python3 - "$doctor_unsafe_manifest_target/template-manifest.json" <<'PY'
import json
import sys

path = sys.argv[1]
manifest = json.load(open(path))
manifest["managed_paths"].append("../outside")
open(path, "w").write(json.dumps(manifest))
PY
if (
    cd "$doctor_unsafe_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-unsafe-manifest.txt" 2>&1; then
    fail "doctor accepted an unsafe manifest"
fi
assert_file_contains "$TEST_DIR/doctor-unsafe-manifest.txt" "FAIL manifest: invalid template-owned manifest"
assert_file_contains "$TEST_DIR/doctor-unsafe-manifest.txt" "Doctor result: NOT READY"

doctor_missing_manifest_target="$TEST_DIR/doctor-missing-manifest"
mkdir -p "$doctor_missing_manifest_target"
if (
    cd "$doctor_missing_manifest_target"
    bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-missing-manifest.txt" 2>&1; then
    fail "doctor accepted a project without a manifest"
fi
assert_file_contains "$TEST_DIR/doctor-missing-manifest.txt" "FAIL manifest:"
assert_file_contains "$TEST_DIR/doctor-missing-manifest.txt" "Remediation:"
assert_file_contains "$TEST_DIR/doctor-missing-manifest.txt" "Doctor result: NOT READY"

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
    bash "$TEMPLATE_DIR/setup.sh" --update --models antigravity
) > "$TEST_DIR/update-models.txt" 2>&1; then
    fail "update accepted an explicit model selection"
fi
assert_file_contains "$TEST_DIR/update-models.txt" "derives runtime adapters"

v042_template_commit="1127e26bd04844d4a9a07d85223a62d5c434fbfd"
v042_template_source="$TEST_DIR/v042-template-source"
v040_template_commit="587c1c93dc073f6b05e485695bcf1e6ea85636b8"
v040_template_source="$TEST_DIR/v040-template-source"
legacy_template_rename_target="$TEST_DIR/legacy-template-rename-target"
legacy_template_modified_target="$TEST_DIR/legacy-template-modified-target"
legacy_v040_template_rename_target="$TEST_DIR/legacy-v040-template-rename-target"
fresh_legacy_template_target="$TEST_DIR/fresh-legacy-template-target"
mkdir -p "$v042_template_source" "$v040_template_source" "$legacy_template_rename_target" "$legacy_template_modified_target" "$legacy_v040_template_rename_target" "$fresh_legacy_template_target"
git -C "$TEMPLATE_DIR" archive "$v042_template_commit" | tar -x -C "$v042_template_source"
git -C "$TEMPLATE_DIR" archive "$v040_template_commit" | tar -x -C "$v040_template_source"
(
    cd "$legacy_template_rename_target"
    bash "$v042_template_source/setup.sh" --models gemini
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/legacy-template-rename.txt"
for old_template in \
    "docs/templates/agent-system-prompt-template.md" \
    "docs/templates/documentation-subagent-contract.md" \
    "docs/templates/task-evidence-template.md" \
    "docs/templates/runtime-delegation-evidence-template.md"; do
    [ ! -e "$legacy_template_rename_target/$old_template" ] || fail "update retained unchanged renamed template: $old_template"
done
for new_template in \
    "docs/templates/1. Agent System Prompt Template.md" \
    "docs/templates/2. Documentation Subagent Contract.md" \
    "docs/templates/3. Task Evidence Template.md" \
    "docs/templates/4. Runtime Delegation Evidence Template.md"; do
    [ -f "$legacy_template_rename_target/$new_template" ] || fail "update did not install renamed template: $new_template"
done
assert_file_contains "$TEST_DIR/legacy-template-rename.txt" "MIGRATED (renamed template)"
(
    cd "$legacy_template_modified_target"
    bash "$v042_template_source/setup.sh" --models gemini
) > "$TEST_DIR/legacy-template-modified-first-install.txt"
printf 'user customization\n' >> "$legacy_template_modified_target/docs/templates/task-evidence-template.md"
(
    cd "$legacy_template_modified_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan legacy-migration-plan.json
) > "$TEST_DIR/legacy-template-modified-plan.txt"
python3 - "$legacy_template_modified_target/legacy-migration-plan.json" <<'PY'
import json
import sys

plan = json.load(open(sys.argv[1]))
assert any(
    item["path"] == "docs/templates/task-evidence-template.md"
    for item in plan["will_preserve"]
)
PY
(
    cd "$legacy_template_modified_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/legacy-template-modified.txt"
[ -f "$legacy_template_modified_target/docs/templates/task-evidence-template.md" ] || fail "update removed user-modified legacy template"
assert_file_contains "$legacy_template_modified_target/docs/templates/task-evidence-template.md" "user customization"
assert_file_contains "$TEST_DIR/legacy-template-modified.txt" "SKIP (user-modified legacy template): docs/templates/task-evidence-template.md"
(
    cd "$legacy_v040_template_rename_target"
    bash "$v040_template_source/setup.sh" --models gemini
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/legacy-v040-template-rename.txt"
[ ! -e "$legacy_v040_template_rename_target/docs/templates/runtime-delegation-evidence-template.md" ] || fail "update retained unchanged v0.4.0 renamed runtime-delegation template"
[ -f "$legacy_v040_template_rename_target/docs/templates/4. Runtime Delegation Evidence Template.md" ] || fail "update did not install v0.4.0 renamed runtime-delegation template"
assert_file_contains "$TEST_DIR/legacy-v040-template-rename.txt" "MIGRATED (renamed template): docs/templates/runtime-delegation-evidence-template.md"
(
    cd "$fresh_legacy_template_target"
    bash "$TEMPLATE_DIR/setup.sh"
    cp "$v042_template_source/docs/templates/task-evidence-template.md" "docs/templates/task-evidence-template.md"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/fresh-legacy-template.txt"
[ -f "$fresh_legacy_template_target/docs/templates/task-evidence-template.md" ] || fail "update removed a legacy-named file created after v0.4.3 installation"
if grep -Fq "MIGRATED (renamed template): docs/templates/task-evidence-template.md" "$TEST_DIR/fresh-legacy-template.txt"; then
    fail "update migrated a legacy-named file created after v0.4.3 installation"
fi

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

# --- v0.5.0 Spec-Driven Development Pack regression tests ---

# 1. --preset on install & --update, custom preset directory guard, and custom preset preservation
preset_bad_target="$TEST_DIR/preset-bad-target"
mkdir -p "$preset_bad_target"
if (
    cd "$preset_bad_target"
    bash "$TEMPLATE_DIR/setup.sh" --preset missing-custom
) > "$TEST_DIR/preset-bad.txt" 2>&1; then
    fail "setup accepted nonexistent custom preset directory"
fi
assert_file_contains "$TEST_DIR/preset-bad.txt" "docs/templates/presets/missing-custom"
[ ! -e "$preset_bad_target/AGENTS.md" ] || fail "failed --preset wrote destination files"

preset_target="$TEST_DIR/preset-target"
mkdir -p "$preset_target"
(
    cd "$preset_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity --preset web-api
) > "$TEST_DIR/preset-install.txt"
python3 -B -c 'import json, sys; assert json.load(open(sys.argv[1]))["default_preset"] == "web-api"' "$preset_target/template-manifest.json"

(
    cd "$preset_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --preset cli-tool
) > "$TEST_DIR/preset-update.txt"
python3 -B -c 'import json, sys; assert json.load(open(sys.argv[1]))["default_preset"] == "cli-tool"' "$preset_target/template-manifest.json"

(
    cd "$preset_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/preset-bare-update.txt"
python3 -B -c 'import json, sys; assert json.load(open(sys.argv[1]))["default_preset"] == "cli-tool"' "$preset_target/template-manifest.json"

mkdir -p "$preset_target/docs/templates/presets/team-api"
printf '# Custom Team API — [Feature name]\n\n- [[1. Product Spec]]\n- [[2. Tech Spec]]\n- [[3. QA Spec]]\n- [[4. Tasks]]\n' \
    > "$preset_target/docs/templates/presets/team-api/README.md"
ln -s "$TEST_DIR" "$preset_target/docs/templates/presets/evil-symlink"
if (
    cd "$preset_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --preset evil-symlink
) > "$TEST_DIR/preset-symlink.txt" 2>&1; then
    fail "setup --update accepted symlinked custom preset directory"
fi
rm -f "$preset_target/docs/templates/presets/evil-symlink"
(
    cd "$preset_target"
    bash "$TEMPLATE_DIR/setup.sh" --update --preset team-api
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/preset-custom-update.txt"
[ -f "$preset_target/docs/templates/presets/team-api/README.md" ] || fail "update removed custom preset directory"
python3 -B -c 'import json, sys; assert json.load(open(sys.argv[1]))["default_preset"] == "team-api"' "$preset_target/template-manifest.json"

# 2. tools/new-feature.py: 4-file default pack, auto-numbering, presets, --plain, --dry-run, empty draft source_revision, and immediate validate-docs.py pass
python3 -B "$preset_target/tools/new-feature.py" --list-presets > "$TEST_DIR/list-presets.txt"
assert_file_contains "$TEST_DIR/list-presets.txt" "web-api (built-in)"
assert_file_contains "$TEST_DIR/list-presets.txt" "team-api (custom:"

python3 -B "$preset_target/tools/new-feature.py" dry-check --preset general --dry-run > "$TEST_DIR/new-feature-dry.txt"
[ ! -e "$preset_target/docs/current/05 - Product Features/001-dry-check" ] || fail "new-feature --dry-run created files"

python3 -B "$preset_target/tools/new-feature.py" auth --preset general > "$TEST_DIR/nf-1.txt"
python3 -B "$preset_target/tools/new-feature.py" billing --preset web-api > "$TEST_DIR/nf-2.txt"
python3 -B "$preset_target/tools/new-feature.py" sync-cli --preset cli-tool > "$TEST_DIR/nf-3.txt"
python3 -B "$preset_target/tools/new-feature.py" triage-bot --preset ai-agent > "$TEST_DIR/nf-4.txt"

[ -d "$preset_target/docs/current/05 - Product Features/001-auth" ] || fail "new-feature did not create 001-auth"
[ -d "$preset_target/docs/current/05 - Product Features/002-billing" ] || fail "new-feature did not create 002-billing"
[ ! -e "$preset_target/docs/current/05 - Product Features/001-auth/README.md" ] || fail "new-feature copied template README.md by default"
for spec_file in "1. Product Spec.md" "2. Tech Spec.md" "3. QA Spec.md" "4. Tasks.md"; do
    [ -f "$preset_target/docs/current/05 - Product Features/001-auth/$spec_file" ] || fail "missing $spec_file in 001-auth"
    grep -Eq '^source_revision:[[:space:]]*$' "$preset_target/docs/current/05 - Product Features/001-auth/$spec_file" || fail "scaffolded draft spec had non-empty source_revision: $spec_file"
done

if python3 -B "$preset_target/tools/new-feature.py" auth > "$TEST_DIR/nf-dup.txt" 2>&1; then
    fail "new-feature accepted duplicate slug auth"
fi
if python3 -B "$preset_target/tools/new-feature.py" "../evil" > "$TEST_DIR/nf-evil.txt" 2>&1; then
    fail "new-feature accepted traversal slug"
fi

# Custom preset (default_preset == team-api from manifest) with --plain includes custom README.md (5 files)
python3 -B "$preset_target/tools/new-feature.py" custom-svc --plain > "$TEST_DIR/nf-custom.txt"
[ -f "$preset_target/docs/current/05 - Product Features/custom-svc/README.md" ] || fail "custom preset README.md was not scaffolded"
[ "$(find "$preset_target/docs/current/05 - Product Features/custom-svc" -maxdepth 1 -type f | wc -l | tr -d ' ')" -eq 5 ] || fail "expected 5 files for custom preset with README.md"

python3 -B "$preset_target/tools/validate-docs.py" > "$TEST_DIR/nf-validate.txt"
assert_file_contains "$TEST_DIR/nf-validate.txt" "PASS: downstream documentation links and Mermaid structure"

# 3. tools/export-tasks.py: draft gate, non-done default filter (--include-done), title prefix, and mock gh deduplication
if python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" > "$TEST_DIR/export-draft-fail.txt" 2>&1; then
    fail "export-tasks exported draft feature without --allow-draft"
fi
assert_file_contains "$TEST_DIR/export-draft-fail.txt" "--allow-draft"

python3 -B - "$preset_target/docs/current/05 - Product Features/001-auth" <<'PY'
import re
import sys
from pathlib import Path

feat = Path(sys.argv[1])
for spec in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md", "4. Tasks.md"):
    p = feat / spec
    text = p.read_text(encoding="utf-8")
    text = text.replace("status: draft", "status: approved", 1)
    text = text.replace("approved_by:", "approved_by: product-lead", 1)
    text = text.replace("approved_at:", "approved_at: 2026-11-12", 1)
    text = text.replace("approval_evidence:", "approval_evidence: PR-101", 1)
    text = text.replace("source_revision:", "source_revision: b8b83557c19217002b0586c052b68e2684706057", 1)
    text = text.replace("- [ ]", "- [x]")
    p.write_text(text, encoding="utf-8")

tasks_p = feat / "4. Tasks.md"
t_text = tasks_p.read_text(encoding="utf-8")
t_text = re.sub(
    r"^\| T-01 \|.*$",
    "| T-01 | done | no | - | AC-01 | `src/auth/model.py` | Completed auth model | `pytest tests/test_model.py` |\n"
    "| T-02 | todo | no | T-01 | AC-01 | `src/auth/api.py` | Wire login endpoint | `pytest tests/test_api.py` |",
    t_text,
    flags=re.M,
)
tasks_p.write_text(t_text, encoding="utf-8")
PY

python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --format json > "$TEST_DIR/export-default.json"
python3 -B - "$TEST_DIR/export-default.json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert [t["task_id"] for t in payload["tasks"]] == ["T-02"], payload
assert payload["tasks"][0]["title"] == "[001-auth][T-02] Wire login endpoint"
PY

python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --include-done --format json > "$TEST_DIR/export-all.json"
python3 -B - "$TEST_DIR/export-all.json" <<'PY'
import json, sys
payload = json.load(open(sys.argv[1]))
assert [t["task_id"] for t in payload["tasks"]] == ["T-01", "T-02"], payload
PY

python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --format gh-commands --repo acme/demo > "$TEST_DIR/export-gh-cmds.txt"
assert_file_contains "$TEST_DIR/export-gh-cmds.txt" "[001-auth][T-02] Wire login endpoint"

if python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --apply-gh > "$TEST_DIR/export-no-repo.txt" 2>&1; then
    fail "export-tasks --apply-gh succeeded without --repo"
fi

mkdir -p "$TEST_DIR/bin"
cat > "$TEST_DIR/bin/gh" <<'EOF'
#!/bin/bash
set -euo pipefail
STORE="${MOCK_GH_STORE:?}"
LOG="${MOCK_GH_LOG:?}"
echo "$*" >> "$LOG"
if [ "$1" = "issue" ] && [ "$2" = "list" ]; then
    cat "$STORE"
    exit 0
fi
if [ "$1" = "issue" ] && [ "$2" = "create" ]; then
    title=""
    while [ "$#" -gt 0 ]; do
        if [ "$1" = "--title" ]; then
            title="$2"
            shift 2
            continue
        fi
        shift
    done
    python3 -B - "$STORE" "$title" <<'PY'
import json, sys
path, title = sys.argv[1], sys.argv[2]
items = json.load(open(path))
num = len(items) + 1
url = f"https://example.invalid/acme/demo/issues/{num}"
items.append({"number": num, "title": title, "url": url})
open(path, "w").write(json.dumps(items))
print(url)
PY
    exit 0
fi
exit 1
EOF
chmod +x "$TEST_DIR/bin/gh"
printf '[]\n' > "$TEST_DIR/mock-gh-store.json"
: > "$TEST_DIR/mock-gh.log"

MOCK_GH_STORE="$TEST_DIR/mock-gh-store.json" MOCK_GH_LOG="$TEST_DIR/mock-gh.log" PATH="$TEST_DIR/bin:$PATH" \
    python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --apply-gh --repo acme/demo > "$TEST_DIR/apply-gh-1.txt"
assert_file_contains "$TEST_DIR/apply-gh-1.txt" "CREATED: [001-auth][T-02]"

MOCK_GH_STORE="$TEST_DIR/mock-gh-store.json" MOCK_GH_LOG="$TEST_DIR/mock-gh.log" PATH="$TEST_DIR/bin:$PATH" \
    python3 -B "$preset_target/tools/export-tasks.py" "$preset_target/docs/current/05 - Product Features/001-auth" --apply-gh --repo acme/demo > "$TEST_DIR/apply-gh-2.txt"
assert_file_contains "$TEST_DIR/apply-gh-2.txt" "SKIP: [001-auth][T-02] already exists"
python3 -B -c 'import json, sys; assert len(json.load(open(sys.argv[1]))) == 1' "$TEST_DIR/mock-gh-store.json"

# 4. Upgrading a v0.4.4 project: clean SDD install vs independent user-owned tools/export-tasks.py preservation
v044_clean_target="$TEST_DIR/v044-clean-target"
v044_partial_target="$TEST_DIR/v044-partial-target"
mkdir -p "$v044_clean_target" "$v044_partial_target"
(
    cd "$v044_clean_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity >/dev/null
)
(
    cd "$v044_partial_target"
    bash "$TEMPLATE_DIR/setup.sh" --models antigravity >/dev/null
)
for sim_dir in "$v044_clean_target" "$v044_partial_target"; do
    rm -f "$sim_dir/tools/new-feature.py" "$sim_dir/tools/export-tasks.py"
    python3 -B - "$sim_dir/template-manifest.json" <<'PY'
import json, sys
p = sys.argv[1]
m = json.load(open(p))
m["version"] = "0.4.4"
sdd = {"tools/new-feature.py", "tools/export-tasks.py", "docs/current/00 - Onboarding/6. Spec-Driven Feature Prompts.md"}
m["managed_paths"] = [x for x in m["managed_paths"] if x not in sdd]
m["profiles"]["core"] = [x for x in m["profiles"]["core"] if x not in sdd]
open(p, "w").write(json.dumps(m, indent=2) + "\n")
PY
done
(
    cd "$v044_clean_target"
    bash "$TEMPLATE_DIR/setup.sh" --update >/dev/null
)
[ -f "$v044_clean_target/tools/new-feature.py" ] || fail "v0.4.4 update did not install tools/new-feature.py"
[ -f "$v044_clean_target/tools/export-tasks.py" ] || fail "v0.4.4 update did not install tools/export-tasks.py"

printf '# custom user exporter\n' > "$v044_partial_target/tools/export-tasks.py"
(
    cd "$v044_partial_target"
    bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan partial-sdd-plan.json >/dev/null
)
python3 -B - "$v044_partial_target/partial-sdd-plan.json" <<'PY'
import json, sys
plan = json.load(open(sys.argv[1]))
assert any(item["path"] == "tools/export-tasks.py" for item in plan["manual_action"]), plan["manual_action"]
assert any(item["path"] == "tools/new-feature.py" for item in plan["will_install"]), plan["will_install"]
PY
(
    cd "$v044_partial_target"
    bash "$TEMPLATE_DIR/setup.sh" --update
) > "$TEST_DIR/v044-partial-update.txt"
assert_file_contains "$v044_partial_target/tools/export-tasks.py" "# custom user exporter"
[ -f "$v044_partial_target/tools/new-feature.py" ] || fail "v0.4.4 partial update did not install tools/new-feature.py"
python3 -B - "$v044_partial_target/template-manifest.json" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))
assert "tools/new-feature.py" in m["managed_paths"] and "tools/new-feature.py" in m["profiles"]["core"]
assert "tools/export-tasks.py" not in m["managed_paths"] and "tools/export-tasks.py" not in m["profiles"]["core"]
PY

# 5. setup.sh --doctor: source-template mode (no runtime binaries required), clean downstream mode, legacy 3-file WARN, missing tool FAIL, and Clarify gate FAIL
doctor_src_bin="$TEST_DIR/doctor-src-bin"
mkdir -p "$doctor_src_bin"
ln -s "$(command -v python3)" "$doctor_src_bin/python3"
for sys_cmd in bash dirname pwd grep find rm mktemp cp mv cat tr; do
    if command -v "$sys_cmd" >/dev/null 2>&1; then
        ln -sf "$(command -v "$sys_cmd")" "$doctor_src_bin/$sys_cmd"
    fi
done
(
    cd "$TEMPLATE_DIR"
    PATH="$doctor_src_bin" bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-source-template.txt"
assert_file_contains "$TEST_DIR/doctor-source-template.txt" "PASS adapters:"
assert_file_contains "$TEST_DIR/doctor-source-template.txt" "PASS tools: source SDD and validation scripts verified"
assert_file_contains "$TEST_DIR/doctor-source-template.txt" "PASS spec readiness:"
assert_file_contains "$TEST_DIR/doctor-source-template.txt" "Doctor result: READY"

printf '#!/bin/bash\nexit 0\n' > "$TEST_DIR/bin/agy"
chmod +x "$TEST_DIR/bin/agy"
(
    cd "$v044_clean_target"
    PATH="$TEST_DIR/bin:$PATH" bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-downstream-ready.txt"
assert_file_contains "$TEST_DIR/doctor-downstream-ready.txt" "PASS tools: managed downstream tools verified"
assert_file_contains "$TEST_DIR/doctor-downstream-ready.txt" "PASS spec readiness:"
assert_file_contains "$TEST_DIR/doctor-downstream-ready.txt" "Doctor result: READY"

# Legacy 3-file approved feature emits WARN (exit 0), not FAIL
cp -R "$preset_target/docs/current/05 - Product Features/001-auth" "$v044_clean_target/docs/current/05 - Product Features/001-legacy"
rm -f "$v044_clean_target/docs/current/05 - Product Features/001-legacy/4. Tasks.md"
python3 -B - "$v044_clean_target/docs/current/05 - Product Features/001-legacy" <<'PY'
import sys
from pathlib import Path

legacy_dir = Path(sys.argv[1])
for spec_name in ("1. Product Spec.md", "2. Tech Spec.md", "3. QA Spec.md"):
    spec_path = legacy_dir / spec_name
    lines = [line for line in spec_path.read_text(encoding="utf-8").splitlines() if "[[4. Tasks]]" not in line]
    spec_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY
(
    cd "$v044_clean_target"
    PATH="$TEST_DIR/bin:$PATH" bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-legacy-warn.txt"
assert_file_contains "$TEST_DIR/doctor-legacy-warn.txt" "WARN spec readiness:"
assert_file_contains "$TEST_DIR/doctor-legacy-warn.txt" "Doctor result: READY"

# Missing managed tool fails doctor
mv "$v044_clean_target/tools/new-feature.py" "$TEST_DIR/saved-new-feature.py"
if (
    cd "$v044_clean_target"
    PATH="$TEST_DIR/bin:$PATH" bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-missing-tool.txt" 2>&1; then
    fail "doctor accepted missing managed tools/new-feature.py"
fi
assert_file_contains "$TEST_DIR/doctor-missing-tool.txt" "FAIL tools: missing or symlinked managed tool tools/new-feature.py"
mv "$TEST_DIR/saved-new-feature.py" "$v044_clean_target/tools/new-feature.py"

# Clarify violation in approved spec fails doctor
printf '\n[NEEDS CLARIFICATION: blocking question]\n' >> "$v044_clean_target/docs/current/05 - Product Features/001-legacy/1. Product Spec.md"
if (
    cd "$v044_clean_target"
    PATH="$TEST_DIR/bin:$PATH" bash "$TEMPLATE_DIR/setup.sh" --doctor
) > "$TEST_DIR/doctor-clarify-fail.txt" 2>&1; then
    fail "doctor accepted approved spec with unresolved NEEDS CLARIFICATION marker"
fi
assert_file_contains "$TEST_DIR/doctor-clarify-fail.txt" "FAIL spec readiness:"
assert_file_contains "$TEST_DIR/doctor-clarify-fail.txt" "Doctor result: NOT READY"

echo "PASS: setup installer regression tests"
