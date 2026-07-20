#!/bin/bash

# Setup script for AI Agent Obsidian Template
set -euo pipefail

FORCE=false
DRY_RUN=false
WITH_ADVANCED_DOCS=false
WITH_LEGACY_AGENTS=false
SELECTED_MODELS=""
MODELS_OPTION_PROVIDED=false
FORCE_INTERACTIVE=false
MANIFEST_BASE=""
REQUESTED_MODELS=""
MANAGED_ADAPTER_MODELS=""
MANIFEST_UPDATE_ALLOWED=true
GENERATED_MANIFEST=""
ACTIVE_TEMP_FILES=()
INSTALLED_COUNT=0
SKIPPED_COUNT=0
PLANNED_COUNT=0
PATH_BLOCKED=false
BLOCKED_COUNT=0
BLOCKED_PATHS=()

usage() {
    cat <<'EOF'
Usage: setup.sh [--dry-run] [--force] [--interactive] [--with-advanced-docs] [--with-legacy-agents] [--models LIST]

Installs the AI agent rules and Obsidian starter vault into the current directory.

  --dry-run  Show which files would be installed or skipped; make no changes.
  --force    Replace existing template-owned files. Without this flag, existing
             files are preserved. Symlinks are never overwritten.
  --with-advanced-docs  Install API, backend, infrastructure, and user-manual
                        starter notes.
  --with-legacy-agents  Install .agents/AGENTS.md for tools that require it.
  --interactive  Show the model-selection menu even when stdin is not a TTY.
  --models LIST  Comma-separated runtime adapters: claude,gemini,qwen,gemma,
                 or all. In an interactive terminal, omit this option to choose.
EOF
}

validate_models() {
    local model
    local seen_models=","

    if [ -z "$SELECTED_MODELS" ]; then
        echo "Error: --models requires at least one model." >&2
        return 1
    fi
    if [ "$SELECTED_MODELS" = "all" ]; then
        SELECTED_MODELS="claude,gemini,qwen,gemma"
        return 0
    fi

    case "$SELECTED_MODELS" in
        ,*|*,|*,,*)
            echo "Error: --models must be a comma-separated list without empty values." >&2
            return 1
            ;;
    esac

    IFS=',' read -r -a SELECTED_MODEL_LIST <<< "$SELECTED_MODELS"
    for model in "${SELECTED_MODEL_LIST[@]}"; do
        case "$model" in
            claude|gemini|qwen|gemma) ;;
            *) echo "Error: Unknown model '$model'. Use claude, gemini, qwen, gemma, or all." >&2; return 1 ;;
        esac
        if [[ "$seen_models" == *",$model,"* ]]; then
            echo "Error: Model '$model' was selected more than once." >&2
            return 1
        fi
        seen_models+="$model,"
    done
}

select_models_interactively() {
    local selection

    if [ "$MODELS_OPTION_PROVIDED" = true ]; then
        validate_models
        return
    fi

    if [ -t 0 ] || [ "$FORCE_INTERACTIVE" = true ]; then
        echo "Select model runtimes/guidance to configure (comma-separated; blank = all):"
        echo "  [1] Claude Code"
        echo "  [2] Gemini CLI"
        echo "  [3] Qwen Code"
        echo "  [4] Gemma / custom API harness (manual wiring)"
        printf "Selection [1,2,3,4]: "
        read -r selection
        case "$selection" in
            ""|all|1,2,3,4) SELECTED_MODELS="claude,gemini,qwen,gemma" ;;
            *)
                case "$selection" in
                    ,*|*,|*,,*)
                        echo "Error: Selection must be a comma-separated list without empty values." >&2
                        return 1
                        ;;
                esac
                SELECTED_MODELS=""
                IFS=',' read -r -a selected_numbers <<< "$selection"
                local seen_numbers=","
                for selection in "${selected_numbers[@]}"; do
                    case "$selection" in
                        1) SELECTED_MODELS+="${SELECTED_MODELS:+,}claude" ;;
                        2) SELECTED_MODELS+="${SELECTED_MODELS:+,}gemini" ;;
                        3) SELECTED_MODELS+="${SELECTED_MODELS:+,}qwen" ;;
                        4) SELECTED_MODELS+="${SELECTED_MODELS:+,}gemma" ;;
                        *) echo "Error: Selection must use 1, 2, 3, or 4." >&2; return 1 ;;
                    esac
                    if [[ "$seen_numbers" == *",$selection,"* ]]; then
                        echo "Error: Model selection '$selection' was selected more than once." >&2
                        return 1
                    fi
                    seen_numbers+="$selection,"
                done
                validate_models
                ;;
        esac
    else
        # Preserve a deterministic, backwards-compatible install in CI and scripts.
        SELECTED_MODELS="claude,gemini,qwen,gemma"
    fi

    validate_models
}

model_selected() {
    local wanted="$1"
    [[ ",$SELECTED_MODELS," == *",$wanted,"* ]]
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --force) FORCE=true ;;
        --interactive) FORCE_INTERACTIVE=true ;;
        --with-advanced-docs) WITH_ADVANCED_DOCS=true ;;
        --with-legacy-agents) WITH_LEGACY_AGENTS=true ;;
        --models)
            [ "$MODELS_OPTION_PROVIDED" = false ] || { echo "Error: --models can only be provided once." >&2; exit 1; }
            shift
            [ "$#" -gt 0 ] || { echo "Error: --models requires a value." >&2; exit 1; }
            MODELS_OPTION_PROVIDED=true
            SELECTED_MODELS="$1"
            ;;
        --models=*)
            [ "$MODELS_OPTION_PROVIDED" = false ] || { echo "Error: --models can only be provided once." >&2; exit 1; }
            MODELS_OPTION_PROVIDED=true
            SELECTED_MODELS="${1#--models=}"
            [ -n "$SELECTED_MODELS" ] || { echo "Error: --models requires a value." >&2; exit 1; }
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
    shift
done

# Set the source directory (where this script is located)
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "$SRC_DIR/template-paths.sh"

# Target directory is the current directory where the script is executed
DEST_DIR="$(pwd -P)"

if [[ "$SRC_DIR" == "$DEST_DIR" || "$DEST_DIR" == "$SRC_DIR"/* ]]; then
    echo "Error: Target directory must not be the template directory or a subdirectory of it."
    echo "Usage: /path/to/ai-project-template/setup.sh"
    exit 1
fi

if [[ "$SRC_DIR" == "$DEST_DIR"/* ]]; then
    echo "Note: Template folder is inside the target project; existing target files will still be preserved by default."
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "Error: Python 3 is required to validate and generate the template manifest." >&2
    exit 1
fi

select_models_interactively

cleanup_temporary_files() {
    local temporary_file

    if [ -n "$GENERATED_MANIFEST" ] && [ -e "$GENERATED_MANIFEST" ]; then
        rm -f "$GENERATED_MANIFEST"
    fi
    for temporary_file in "${ACTIVE_TEMP_FILES[@]-}"; do
        [ -e "$temporary_file" ] && rm -f "$temporary_file"
    done
    return 0
}
trap cleanup_temporary_files EXIT
trap 'cleanup_temporary_files; exit 130' INT TERM

prepare_manifest_models() {
    local existing_manifest="$DEST_DIR/template-manifest.json"

    REQUESTED_MODELS="$SELECTED_MODELS"
    MANIFEST_BASE="$SRC_DIR/template-manifest.json"
    MANIFEST_UPDATE_ALLOWED=true
    if [ ! -e "$existing_manifest" ] && [ ! -L "$existing_manifest" ]; then
        return
    fi
    if [ -L "$existing_manifest" ]; then
        MANIFEST_UPDATE_ALLOWED=false
        return
    fi

    if ! REQUESTED_MODELS="$(python3 - "$existing_manifest" "$SELECTED_MODELS" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
if manifest.get("template") != "ai-agent-obsidian-project-template":
    print("UNMANAGED")
    raise SystemExit(0)

if not isinstance(manifest.get("managed_paths"), list) or not all(isinstance(path, str) for path in manifest["managed_paths"]):
    raise ValueError("existing manifest has invalid managed_paths")
profiles = manifest.get("profiles")
if not isinstance(profiles, dict) or not isinstance(profiles.get("core"), list) or not all(isinstance(path, str) for path in profiles["core"]):
    raise ValueError("existing manifest has invalid profiles.core")

requested = sys.argv[2].split(",")
known = ["claude", "gemini", "qwen", "gemma"]
existing = manifest.get("requested_models", manifest.get("selected_models"))
if existing is None:
    adapters = {"CLAUDE.md": "claude", "GEMINI.md": "gemini", "QWEN.md": "qwen"}
    existing = [adapters[path] for path in manifest.get("profiles", {}).get("core", []) if path in adapters]

if not isinstance(existing, list) or any(model not in known for model in existing):
    raise ValueError("existing manifest has invalid selected_models")

combined = [model for model in known if model in existing or model in requested]
print(",".join(combined))
PY
    )"; then
        echo "Error: Cannot safely update template-manifest.json selection; use a valid template-owned manifest." >&2
        return 1
    fi
    if [ "$REQUESTED_MODELS" = "UNMANAGED" ]; then
        MANIFEST_UPDATE_ALLOWED=false
        REQUESTED_MODELS="$SELECTED_MODELS"
        return
    fi
    MANIFEST_BASE="$existing_manifest"
}

copy_file() {
    local source_file="$1"
    local relative_path="$2"
    local destination_file="$DEST_DIR/$relative_path"

    # Revalidate immediately before each file operation. Preflight catches
    # ordinary conflicts up front; this narrows the window for later changes.
    check_destination_path "$relative_path"
    if [ "$DRY_RUN" = true ] && [ "$PATH_BLOCKED" = true ]; then
        return
    fi

    if [ -L "$destination_file" ] && [ "$FORCE" = true ]; then
        echo "Error: Refusing to overwrite symlink: $relative_path" >&2
        return 1
    fi

    if { [ -e "$destination_file" ] || [ -L "$destination_file" ]; } && [ "$FORCE" = false ]; then
        echo "SKIP (exists): $relative_path"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        echo "INSTALL: $relative_path"
        PLANNED_COUNT=$((PLANNED_COUNT + 1))
        return
    fi

    local destination_dir
    local temporary_file

    destination_dir="$(dirname "$destination_file")"
    mkdir -p "$destination_dir"
    temporary_file="$(mktemp "$destination_dir/.ai-template.XXXXXX")"
    ACTIVE_TEMP_FILES+=("$temporary_file")

    # Preserve the template file mode while still replacing the destination
    # directory entry atomically below.
    if ! cp -p "$source_file" "$temporary_file"; then
        rm -f "$temporary_file"
        return 1
    fi

    # Replacing the directory entry instead of copying over it prevents a
    # forced install from modifying another path that shares a hard link.
    mv -f "$temporary_file" "$destination_file"
    ACTIVE_TEMP_FILES=("${ACTIVE_TEMP_FILES[@]:0:${#ACTIVE_TEMP_FILES[@]}-1}")
    echo "INSTALLED: $relative_path"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
}

collect_managed_adapter_models() {
    local mapping
    local model
    local adapter

    MANAGED_ADAPTER_MODELS=""
    for mapping in "claude:CLAUDE.md" "gemini:GEMINI.md" "qwen:QWEN.md"; do
        model="${mapping%%:*}"
        adapter="${mapping#*:}"
        if [ -f "$DEST_DIR/$adapter" ] && [ ! -L "$DEST_DIR/$adapter" ] && cmp -s "$SRC_DIR/$adapter" "$DEST_DIR/$adapter"; then
            MANAGED_ADAPTER_MODELS+="${MANAGED_ADAPTER_MODELS:+,}$model"
        fi
    done
}

copy_selected_manifest() {
    if [ "$MANIFEST_UPDATE_ALLOWED" = false ]; then
        echo "SKIP (unmanaged manifest): template-manifest.json"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return
    fi
    if [ "$DRY_RUN" = true ]; then
        if [ -e "$DEST_DIR/template-manifest.json" ] || [ -L "$DEST_DIR/template-manifest.json" ]; then
            echo "UPDATE: template-manifest.json"
        else
            echo "INSTALL: template-manifest.json"
        fi
        PLANNED_COUNT=$((PLANNED_COUNT + 1))
        return
    fi

    collect_managed_adapter_models
    GENERATED_MANIFEST="$(mktemp "$DEST_DIR/.ai-template-manifest.XXXXXX")"
    if ! cp -p "$SRC_DIR/template-manifest.json" "$GENERATED_MANIFEST"; then
        return 1
    fi
    if ! python3 - "$SRC_DIR/template-manifest.json" "$MANIFEST_BASE" "$GENERATED_MANIFEST" "$REQUESTED_MODELS" "$MANAGED_ADAPTER_MODELS" <<'PY'
import json
import sys
from pathlib import Path

template_source = Path(sys.argv[1])
existing_source = Path(sys.argv[2])
destination = Path(sys.argv[3])
requested = sys.argv[4].split(",")
managed = [model for model in sys.argv[5].split(",") if model]
adapter_models = {
    "CLAUDE.md": "claude",
    "GEMINI.md": "gemini",
    "QWEN.md": "qwen",
}

data = json.loads(template_source.read_text())
existing = json.loads(existing_source.read_text())
installer_keys = {"template", "version", "managed_paths", "profiles", "requested_models", "selected_models", "managed_adapter_models"}
for key, value in existing.items():
    if key not in installer_keys:
        data[key] = value

existing_profiles = existing.get("profiles", {})
for name, profile in existing_profiles.items():
    if name != "core":
        data["profiles"][name] = profile
for path in existing_profiles.get("core", []):
    if path not in data["profiles"]["core"] and path not in adapter_models:
        data["profiles"]["core"].append(path)
for path in existing.get("managed_paths", []):
    if path not in data["managed_paths"] and path not in adapter_models:
        data["managed_paths"].append(path)
data["requested_models"] = requested
data["selected_models"] = requested  # Backward-compatible alias; prefer requested_models.
data["managed_adapter_models"] = managed
data["managed_paths"] = [
    path for path in data["managed_paths"]
    if path not in adapter_models or adapter_models[path] in managed
]
data["profiles"]["core"] = [
    path for path in data["profiles"]["core"]
    if path not in adapter_models or adapter_models[path] in managed
]
for adapter, model in adapter_models.items():
    if model in managed:
        if adapter not in data["managed_paths"]:
            data["managed_paths"].append(adapter)
        if adapter not in data["profiles"]["core"]:
            data["profiles"]["core"].append(adapter)
destination.write_text(json.dumps(data, indent=2) + "\n")
PY
    then
        return 1
    fi

    # The validated template-owned manifest is replaced atomically; custom
    # metadata and profiles were merged into GENERATED_MANIFEST above.
    if [ -L "$DEST_DIR/template-manifest.json" ]; then
        echo "Error: Refusing to overwrite symlink: template-manifest.json" >&2
        return 1
    fi
    mv -f "$GENERATED_MANIFEST" "$DEST_DIR/template-manifest.json"
    GENERATED_MANIFEST=""
    echo "INSTALLED: template-manifest.json"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
}

should_include_doc() {
    local relative_path="$1"

    local optional_doc

    for optional_doc in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
        if [ "$relative_path" = "$optional_doc" ]; then
            [ "$WITH_ADVANCED_DOCS" = true ]
            return
        fi
    done

    return 0
}

report_blocked_path() {
    local reason="$1"
    local relative_path="$2"
    local blocked_path

    for blocked_path in "${BLOCKED_PATHS[@]-}"; do
        [ "$blocked_path" = "$relative_path" ] && return
    done

    echo "BLOCKED ($reason): $relative_path"
    BLOCKED_PATHS+=("$relative_path")
    BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
}

find_template_docs() {
    find "$SRC_DIR/docs" -path "$SRC_DIR/docs/internal" -prune -o -type f ! -name '.DS_Store' -print0
}

check_destination_path() {
    local relative_path="$1"
    local path_part
    local current_path="$DEST_DIR"
    local path_index
    local IFS='/'
    local -a path_parts
    PATH_BLOCKED=false

    read -r -a path_parts <<< "$relative_path"
    for path_index in "${!path_parts[@]}"; do
        path_part="${path_parts[$path_index]}"
        current_path="$current_path/$path_part"
        if [ -L "$current_path" ]; then
            # A final symlink is an existing file and is safely skipped in the
            # default mode. Parent symlinks could redirect a later write, and
            # --force would replace the final symlink, so both are rejected.
            if [ "$path_index" -eq "$((${#path_parts[@]} - 1))" ] && [ "$FORCE" = false ]; then
                continue
            fi
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "symlink" "$relative_path"
                PATH_BLOCKED=true
                return 0
            fi
            echo "Error: Refusing to write through symlink: $relative_path" >&2
            return 1
        fi

        if [ "$path_index" -eq "$((${#path_parts[@]} - 1))" ] && [ -e "$current_path" ] && [ -d "$current_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "path conflict" "$relative_path"
                PATH_BLOCKED=true
                return 0
            fi
            echo "Error: Expected file but found directory in template path: $relative_path" >&2
            return 1
        fi

        # Every non-final path component must be a directory when it already
        # exists. Otherwise mkdir -p would fail after earlier files were copied.
        if [ "$path_index" -lt "$((${#path_parts[@]} - 1))" ] && [ -e "$current_path" ] && [ ! -d "$current_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "path conflict" "$relative_path"
                PATH_BLOCKED=true
                return 0
            fi
            echo "Error: Expected directory but found file in template path: $relative_path" >&2
            return 1
        fi
    done
}

preflight_destinations() {
    local source_file
    local relative_path
    local failed=false

    prepare_manifest_models || failed=true

    for relative_path in "AGENTS.md" "template-manifest.json" "tools/validate-task-evidence.py" "tools/validate-docs.py"; do
        check_destination_path "$relative_path" || failed=true
    done
    if model_selected claude; then
        check_destination_path "CLAUDE.md" || failed=true
    fi
    if model_selected gemini; then
        check_destination_path "GEMINI.md" || failed=true
    fi
    if model_selected qwen; then
        check_destination_path "QWEN.md" || failed=true
    fi
    if [ "$WITH_LEGACY_AGENTS" = true ]; then
        check_destination_path ".agents/AGENTS.md" || failed=true
    fi

    while IFS= read -r -d '' source_file; do
        relative_path="${source_file#"$SRC_DIR/"}"
        should_include_doc "$relative_path" || continue
        check_destination_path "$relative_path" || failed=true
    done < <(find_template_docs)

    if [ "$failed" = true ]; then
        echo "No files were changed because the destination has an unsafe or conflicting template path." >&2
        return 1
    fi
}

echo "Setting up AI Agent Obsidian Template in: $DEST_DIR"
echo "Selected model runtimes: $SELECTED_MODELS"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run only — no files will be changed."
fi

# Check every destination before copying anything. This prevents a later
# symlink error from leaving a forced installation only partially applied.
preflight_destinations

# Root AGENTS.md is the canonical convention for Codex and other compatible agents.
copy_file "$SRC_DIR/AGENTS.md" "AGENTS.md"

# Claude Code reads CLAUDE.md at the project root. It delegates to the same
# canonical rules so the two agent entrypoints cannot drift.
if model_selected claude; then
    copy_file "$SRC_DIR/CLAUDE.md" "CLAUDE.md"
fi

# Gemini CLI and Qwen Code load their native project context files. Both
# adapters point to AGENTS.md so workspace policy has one canonical source.
if model_selected gemini; then
    copy_file "$SRC_DIR/GEMINI.md" "GEMINI.md"
fi
if model_selected qwen; then
    copy_file "$SRC_DIR/QWEN.md" "QWEN.md"
fi

# Record the template version and the adapters actually selected for later audits/upgrades.
copy_selected_manifest

copy_file "$SRC_DIR/tests/validate-task-evidence.py" "tools/validate-task-evidence.py"
copy_file "$SRC_DIR/tests/validate-project-docs.py" "tools/validate-docs.py"

if [ "$WITH_LEGACY_AGENTS" = true ]; then
    copy_file "$SRC_DIR/AGENTS.md" ".agents/AGENTS.md"
fi

while IFS= read -r -d '' source_file; do
    relative_path="${source_file#"$SRC_DIR/"}"
    should_include_doc "$relative_path" || continue
    copy_file "$source_file" "$relative_path"
done < <(find_template_docs)

echo "----------------------------------------"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run complete: $PLANNED_COUNT file(s) would be installed; $SKIPPED_COUNT existing file(s) would be preserved; $BLOCKED_COUNT path(s) are blocked."
elif [ "$INSTALLED_COUNT" -eq 0 ]; then
    echo "No files installed: $SKIPPED_COUNT existing file(s) were preserved. Use --force only if you intend to replace them."
else
    echo "✅ Setup complete: installed $INSTALLED_COUNT file(s); preserved $SKIPPED_COUNT existing file(s)."
fi
echo ""
echo "Next steps:"
echo "1. Open this project folder in Obsidian as a Vault."
echo "2. Confirm your selected runtime loads its project instructions; Gemma/custom API harnesses must inject docs/templates/agent-system-prompt-template.md."
if model_selected gemma; then
    echo "3. Gemma/custom API selected: no repository filename is auto-loaded. Configure the host to inject docs/templates/agent-system-prompt-template.md before enabling write tools."
fi
echo "----------------------------------------"
