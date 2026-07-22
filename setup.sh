#!/bin/bash

# Setup script for AI Agent Obsidian Template
set -euo pipefail

FORCE=false
DRY_RUN=false
WITH_ADVANCED_DOCS=false
WITH_LEGACY_AGENTS=false
UPDATE=false
SELECTED_MODELS=""
MODELS_OPTION_PROVIDED=false
FORCE_INTERACTIVE=false
MANIFEST_BASE=""
REQUESTED_MODELS=""
MANAGED_ADAPTER_MODELS=""
UPDATE_MANAGED_ADAPTER_MODELS=""
MANAGED_PROFILES="core"
MANIFEST_UPDATE_ALLOWED=true
VALIDATOR_BUNDLE_MANAGED=true
GENERATED_MANIFEST=""
ACTIVE_TEMP_FILES=()
BACKUP_DIR=""
INSTALLED_COUNT=0
SKIPPED_COUNT=0
PLANNED_COUNT=0
PATH_BLOCKED=false
BLOCKED_COUNT=0
BLOCKED_PATHS=()

usage() {
    cat <<'EOF'
Usage: setup.sh [--dry-run] [--force] [--update] [--interactive] [--with-advanced-docs] [--with-legacy-agents] [--models LIST]

Installs the AI agent rules and Obsidian starter vault into the current directory.

  --dry-run  Show which files would be installed or skipped; make no changes.
  --force    Replace existing template-owned files. Without this flag, existing
             files are preserved. Symlinks are never overwritten.
  --update   Upgrade a project with a template-owned manifest. Existing managed
             files are backed up, then replaced by this template version.
  --with-advanced-docs  Install API, backend, infrastructure, and user-manual
                        starter notes.
  --with-legacy-agents  Install .agents/AGENTS.md for tools that require it.
  --interactive  Show the model-selection menu even when stdin is not a TTY.
  --models LIST  Comma-separated runtime adapters: claude,antigravity,qwen,gemma,
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
        SELECTED_MODELS="claude,antigravity,qwen,gemma"
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
            claude|antigravity|qwen|gemma) ;;
            *) echo "Error: Unknown model '$model'. Use claude, antigravity, qwen, gemma, or all." >&2; return 1 ;;
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
        echo "  [2] Antigravity CLI"
        echo "  [3] Qwen Code"
        echo "  [4] Gemma / custom API harness (manual wiring)"
        printf "Selection [1,2,3,4]: "
        read -r selection
        case "$selection" in
            ""|all|1,2,3,4) SELECTED_MODELS="claude,antigravity,qwen,gemma" ;;
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
                        2) SELECTED_MODELS+="${SELECTED_MODELS:+,}antigravity" ;;
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
        SELECTED_MODELS="claude,antigravity,qwen,gemma"
    fi

    validate_models
}

model_selected() {
    local wanted="$1"
    [[ ",$SELECTED_MODELS," == *",$wanted,"* ]]
}

adapter_selected_for_copy() {
    local model="$1"

    model_selected "$model" || return 1
    [ "$UPDATE" = false ] && return 0
    [[ ",$UPDATE_MANAGED_ADAPTER_MODELS," == *",$model,"* ]]
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --force) FORCE=true ;;
        --interactive) FORCE_INTERACTIVE=true ;;
        --update) UPDATE=true ;;
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

# template-paths.sh reads profile membership from the manifest, so load it
# only after the Python prerequisite has been checked.
if ! source "$SRC_DIR/template-paths.sh"; then
    echo "Error: Cannot safely load template profile paths." >&2
    exit 1
fi

select_update_models() {
    local existing_manifest="$DEST_DIR/template-manifest.json"
    local update_metadata
    local inferred_models
    local prior_advanced
    local prior_legacy

    if [ "$MODELS_OPTION_PROVIDED" = true ]; then
        echo "Error: --update derives runtime adapters from the installed manifest; use a normal install to add a new runtime adapter." >&2
        exit 1
    fi
    if [ ! -f "$existing_manifest" ] || [ -L "$existing_manifest" ]; then
        echo "Error: --update requires a regular, template-owned template-manifest.json. Use a normal install for a new project." >&2
        exit 1
    fi
    if ! update_metadata="$(python3 - "$existing_manifest" <<'PY'
import json
import sys
from pathlib import Path

manifest = json.loads(Path(sys.argv[1]).read_text())
if manifest.get("template") != "ai-agent-obsidian-project-template":
    raise ValueError("manifest is not owned by ai-agent-obsidian-project-template")
def safe_path(path):
    return isinstance(path, str) and path and not path.startswith("/") and "\n" not in path and "\r" not in path and all(part not in {"", ".", ".."} for part in path.split("/"))
if not isinstance(manifest.get("managed_paths"), list) or not all(safe_path(path) for path in manifest["managed_paths"]):
    raise ValueError("manifest has unsafe managed_paths")
known = ["claude", "antigravity", "qwen", "gemma", "gemini"]
models = manifest.get("requested_models", manifest.get("selected_models"))
if models is None:
    adapters = {"CLAUDE.md": "claude", "GEMINI.md": "antigravity", "QWEN.md": "qwen"}
    models = [adapters[path] for path in manifest.get("profiles", {}).get("core", []) if path in adapters]
if not isinstance(models, list) or any(model not in known for model in models):
    raise ValueError("manifest has invalid runtime selection")
models = ["antigravity" if model == "gemini" else model for model in models]
profiles = manifest.get("profiles")
if not isinstance(profiles, dict):
    raise ValueError("manifest has invalid profiles")
if any(not isinstance(paths, list) or not all(safe_path(path) for path in paths) for paths in profiles.values()):
    raise ValueError("manifest has unsafe profile paths")
advanced = bool(profiles.get("--with-advanced-docs"))
legacy = ".agents/AGENTS.md" in profiles.get("--with-legacy-agents", [])
managed = manifest.get("managed_adapter_models")
if managed is None:
    adapters = {"CLAUDE.md": "claude", "GEMINI.md": "antigravity", "QWEN.md": "qwen"}
    managed = [adapters[path] for path in manifest.get("managed_paths", []) if path in adapters]
if not isinstance(managed, list) or any(model not in known for model in managed):
    raise ValueError("manifest has invalid managed_adapter_models")
managed = ["antigravity" if model == "gemini" else model for model in managed]
managed_profiles = manifest.get("managed_profiles")
if managed_profiles is None:
    managed_profiles = ["core"]
elif not isinstance(managed_profiles, list) or any(profile not in {"core", "--with-advanced-docs", "--with-legacy-agents"} for profile in managed_profiles):
    raise ValueError("manifest has invalid managed_profiles")
print("|".join([",".join(models or known), str("--with-advanced-docs" in managed_profiles).lower(), str("--with-legacy-agents" in managed_profiles).lower(), ",".join(managed), ",".join(managed_profiles)]))
PY
    )"; then
        echo "Error: --update requires a valid template-owned template-manifest.json." >&2
        exit 1
    fi
    IFS='|' read -r inferred_models prior_advanced prior_legacy UPDATE_MANAGED_ADAPTER_MODELS MANAGED_PROFILES <<< "$update_metadata"
    SELECTED_MODELS="$inferred_models"
    [ "$prior_advanced" = true ] && WITH_ADVANCED_DOCS=true
    [ "$prior_legacy" = true ] && WITH_LEGACY_AGENTS=true
    validate_models
}

if [ "$UPDATE" = true ]; then
    select_update_models
else
    select_models_interactively
fi

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
def safe_path(path):
    return isinstance(path, str) and path and not path.startswith("/") and "\n" not in path and "\r" not in path and all(part not in {"", ".", ".."} for part in path.split("/"))
if not all(safe_path(path) for path in manifest["managed_paths"]):
    raise ValueError("existing manifest has unsafe managed_paths")
if any(not isinstance(paths, list) or not all(safe_path(path) for path in paths) for paths in profiles.values()):
    raise ValueError("existing manifest has unsafe profile paths")

requested = sys.argv[2].split(",")
known = ["claude", "antigravity", "qwen", "gemma", "gemini"]
existing = manifest.get("requested_models", manifest.get("selected_models"))
if existing is None:
    adapters = {"CLAUDE.md": "claude", "GEMINI.md": "antigravity", "QWEN.md": "qwen"}
    existing = [adapters[path] for path in manifest.get("profiles", {}).get("core", []) if path in adapters]

if not isinstance(existing, list) or any(model not in known for model in existing):
    raise ValueError("existing manifest has invalid selected_models")

existing = ["antigravity" if model == "gemini" else model for model in existing]

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

    if [ -L "$destination_file" ] && { [ "$FORCE" = true ] || [ "$UPDATE" = true ]; }; then
        echo "Error: Refusing to overwrite symlink: $relative_path" >&2
        return 1
    fi

    if { [ -e "$destination_file" ] || [ -L "$destination_file" ]; } && [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
        echo "SKIP (exists): $relative_path"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return
    fi

    if [ "$DRY_RUN" = true ]; then
        if [ -e "$destination_file" ] || [ -L "$destination_file" ]; then
            echo "UPDATE (backup): $relative_path"
        else
            echo "INSTALL: $relative_path"
        fi
        PLANNED_COUNT=$((PLANNED_COUNT + 1))
        return
    fi

    local destination_dir
    local temporary_file

    backup_existing_file "$relative_path"

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

backup_existing_file() {
    local relative_path="$1"
    local destination_file="$DEST_DIR/$relative_path"
    local backup_file

    [ "$UPDATE" = true ] || return 0
    [ -e "$destination_file" ] || return 0
    if [ -z "$BACKUP_DIR" ]; then
        BACKUP_DIR="$(mktemp -d "$DEST_DIR/.ai-template-backup.XXXXXX")"
        write_backup_recovery_note
        echo "BACKUP: $BACKUP_DIR"
    fi
    backup_file="$BACKUP_DIR/$relative_path"
    mkdir -p "$(dirname "$backup_file")"
    cp -p "$destination_file" "$backup_file"
}

write_backup_recovery_note() {
    local recovery_note="$BACKUP_DIR/RECOVERY.md"

    printf '%s\n' \
        '# Template update recovery' \
        '' \
        'This update replaces files one at a time. If it is interrupted or fails, the project can contain a mix of versions.' \
        '' \
        'The backup tree mirrors the project root. To restore one replaced file, run from the project root:' \
        '' \
        '```bash' \
        'cp -p ".ai-template-backup.XXXXXX/path/to/file" "path/to/file"' \
        '```' \
        '' \
        'Replace `.ai-template-backup.XXXXXX` and `path/to/file` with the reported backup directory and desired path. Files newly added by the update are not removed automatically.' \
        > "$recovery_note"
}

collect_managed_adapter_models() {
    local mapping
    local model
    local adapter

    MANAGED_ADAPTER_MODELS=""
    for mapping in "claude:CLAUDE.md" "antigravity:GEMINI.md" "qwen:QWEN.md"; do
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
            if [ "$UPDATE" = true ]; then
                echo "UPDATE (backup): template-manifest.json"
            else
                echo "UPDATE: template-manifest.json"
            fi
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
    if ! python3 - "$SRC_DIR/template-manifest.json" "$MANIFEST_BASE" "$GENERATED_MANIFEST" "$REQUESTED_MODELS" "$MANAGED_ADAPTER_MODELS" "$WITH_ADVANCED_DOCS" "$WITH_LEGACY_AGENTS" "$VALIDATOR_BUNDLE_MANAGED" <<'PY'
import json
import sys
from pathlib import Path

template_source = Path(sys.argv[1])
existing_source = Path(sys.argv[2])
destination = Path(sys.argv[3])
requested = sys.argv[4].split(",")
managed = [model for model in sys.argv[5].split(",") if model]
with_advanced = sys.argv[6] == "true"
with_legacy = sys.argv[7] == "true"
validator_bundle_managed = sys.argv[8] == "true"
adapter_models = {
    "CLAUDE.md": "claude",
    "GEMINI.md": "antigravity",
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
    if name not in {"core", "--with-advanced-docs", "--with-legacy-agents"}:
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
managed_profiles = existing.get("managed_profiles", ["core"])
if not isinstance(managed_profiles, list) or any(profile not in {"core", "--with-advanced-docs", "--with-legacy-agents"} for profile in managed_profiles):
    raise ValueError("existing manifest has invalid managed_profiles")
managed_profiles = set(managed_profiles)
managed_profiles.add("core")
if with_advanced:
    managed_profiles.add("--with-advanced-docs")
if with_legacy:
    managed_profiles.add("--with-legacy-agents")
data["managed_profiles"] = [profile for profile in ["core", "--with-advanced-docs", "--with-legacy-agents"] if profile in managed_profiles]
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
validator_paths = {"tools/docs_validation.py", "tools/validate-docs.py"}
if not validator_bundle_managed:
    data["managed_paths"] = [path for path in data["managed_paths"] if path not in validator_paths]
    data["profiles"]["core"] = [path for path in data["profiles"]["core"] if path not in validator_paths]
destination.write_text(json.dumps(data, indent=2) + "\n")
PY
    then
        return 1
    fi

    backup_existing_file "template-manifest.json"

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

    local profile_path

    for profile_path in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
        if [ "$relative_path" = "$profile_path" ] || [[ "$relative_path" == "$profile_path/"* ]]; then
            [ "$WITH_ADVANCED_DOCS" = true ]
            return
        fi
    done

    for profile_path in "${CORE_PROFILE_PATHS[@]}"; do
        if [ "$relative_path" = "$profile_path" ] || [[ "$relative_path" == "$profile_path/"* ]]; then
            return 0
        fi
    done

    echo "Error: Template documentation is not assigned to an installation profile: $relative_path" >&2
    return 1
}

prepare_validator_bundle() {
    local relative_path
    local ownership

    VALIDATOR_BUNDLE_MANAGED=true
    [ "$FORCE" = true ] && return 0
    if [ "$UPDATE" = true ]; then
        ownership="$(python3 - "$DEST_DIR/template-manifest.json" "$DEST_DIR/tools/docs_validation.py" "$DEST_DIR/tools/validate-docs.py" <<'PY'
import json
import sys
from pathlib import Path

manifest_path, helper_path, validator_path = map(Path, sys.argv[1:])
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    managed = set(manifest.get("managed_paths", []))
    core = set(manifest.get("profiles", {}).get("core", []))
except (OSError, ValueError, TypeError):
    print("unmanaged")
    raise SystemExit(0)

helper = "tools/docs_validation.py"
validator = "tools/validate-docs.py"
if {helper, validator}.issubset(managed) and {helper, validator}.issubset(core):
    print("managed")
elif not helper_path.exists() and validator in managed and validator in core:
    # Migrate the prior single-file validator only when its manifest owned it.
    print("managed")
elif not helper_path.exists() and not validator_path.exists():
    print("managed")
else:
    print("unmanaged")
PY
        )"
        if [ "$ownership" = managed ]; then
            return 0
        fi
        VALIDATOR_BUNDLE_MANAGED=false
        return 0
    fi
    for relative_path in "tools/docs_validation.py" "tools/validate-docs.py"; do
        if [ -e "$DEST_DIR/$relative_path" ] || [ -L "$DEST_DIR/$relative_path" ]; then
            VALIDATOR_BUNDLE_MANAGED=false
            return 0
        fi
    done
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

legacy_template_migration_allowed() {
    local old_relative_path="$1"

    python3 - "$DEST_DIR/template-manifest.json" "$old_relative_path" <<'PY'
import json
import sys
from pathlib import Path

manifest_path = Path(sys.argv[1])
legacy_path = sys.argv[2]
try:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = manifest.get("version")
    paths = [*manifest.get("managed_paths", []), *manifest.get("profiles", {}).get("core", [])]
except (OSError, ValueError, TypeError):
    raise SystemExit(1)

affected_versions = {"0.4.0", "0.4.1", "0.4.2"}
is_managed = any(isinstance(path, str) and (path == legacy_path or legacy_path.startswith(path + "/")) for path in paths)
raise SystemExit(0 if version in affected_versions and is_managed else 1)
PY
}

migrate_renamed_template_files() {
    local mapping
    local old_relative_path
    local new_relative_path
    local expected_sha256
    local old_path

    [ "$UPDATE" = true ] || return 0

    # Renamed template files were template-owned in v0.4.0–v0.4.2. Only those
    # manifests are eligible, and an old filename is removed only when its
    # contents match a known release; preserve any user edit or symlink.
    for mapping in \
        "docs/templates/agent-system-prompt-template.md|docs/templates/1. Agent System Prompt Template.md|aa6e9c623f27ad7c77d0b9b053a9c885c837942175fdd88d8ee4c9257b7c5a6e" \
        "docs/templates/documentation-subagent-contract.md|docs/templates/2. Documentation Subagent Contract.md|57d3c4b586c86429bc852db1c35c40e13f8a6fd2ca4f33dd6225d20411b76430" \
        "docs/templates/task-evidence-template.md|docs/templates/3. Task Evidence Template.md|9dda6623fddc2eeb07c70e756c29e7ce2a8b26765722260625e34a573bce23a1" \
        "docs/templates/runtime-delegation-evidence-template.md|docs/templates/4. Runtime Delegation Evidence Template.md|3d8960ff20f3b27c7311e61942552112aadf5ebdc25910b11bc92927af6f62e4,6fb83edc810b6e2bc70a089e84277f8b35966598e9ed986ab00d012332e01b25"; do
        IFS='|' read -r old_relative_path new_relative_path expected_sha256 <<< "$mapping"
        old_path="$DEST_DIR/$old_relative_path"

        [ -e "$old_path" ] || [ -L "$old_path" ] || continue
        legacy_template_migration_allowed "$old_relative_path" || continue
        if [ -L "$old_path" ]; then
            echo "SKIP (symlink legacy template): $old_relative_path"
            continue
        fi
        if [ ! -f "$old_path" ]; then
            echo "SKIP (non-file legacy template): $old_relative_path"
            continue
        fi
        if ! python3 - "$old_path" "$expected_sha256" <<'PY'
import hashlib
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected = sys.argv[2]
raise SystemExit(0 if hashlib.sha256(path.read_bytes()).hexdigest() in expected.split(",") else 1)
PY
        then
            echo "SKIP (user-modified legacy template): $old_relative_path"
            continue
        fi

        if [ "$DRY_RUN" = true ]; then
            echo "MIGRATE (remove renamed template): $old_relative_path -> $new_relative_path"
            PLANNED_COUNT=$((PLANNED_COUNT + 1))
            continue
        fi

        backup_existing_file "$old_relative_path"
        rm -f "$old_path"
        echo "MIGRATED (renamed template): $old_relative_path -> $new_relative_path"
    done
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
            if [ "$path_index" -eq "$((${#path_parts[@]} - 1))" ] && [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
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
    prepare_validator_bundle

    for relative_path in "AGENTS.md" "template-manifest.json" "tools/validate-task-evidence.py" "task-evidence/.gitkeep"; do
        check_destination_path "$relative_path" || failed=true
    done
    if [ "$VALIDATOR_BUNDLE_MANAGED" = true ]; then
        for relative_path in "tools/docs_validation.py" "tools/validate-docs.py"; do
            check_destination_path "$relative_path" || failed=true
        done
    fi
    if adapter_selected_for_copy claude; then
        check_destination_path "CLAUDE.md" || failed=true
    fi
    if adapter_selected_for_copy antigravity; then
        check_destination_path "GEMINI.md" || failed=true
    fi
    if adapter_selected_for_copy qwen; then
        check_destination_path "QWEN.md" || failed=true
    fi
    if [ "$WITH_LEGACY_AGENTS" = true ]; then
        for relative_path in "${OPTIONAL_LEGACY_PATHS[@]}"; do
            check_destination_path "$relative_path" || failed=true
        done
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
if [ "$UPDATE" = true ]; then
    echo "Update mode: existing managed files will be backed up then replaced."
fi
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
if adapter_selected_for_copy claude; then
    copy_file "$SRC_DIR/CLAUDE.md" "CLAUDE.md"
fi

# Antigravity CLI preserves Gemini-compatible `GEMINI.md` discovery; Qwen Code
# has its own native file. Both adapters point to AGENTS.md as the canonical source.
if adapter_selected_for_copy antigravity; then
    copy_file "$SRC_DIR/GEMINI.md" "GEMINI.md"
fi
if adapter_selected_for_copy qwen; then
    copy_file "$SRC_DIR/QWEN.md" "QWEN.md"
fi

copy_file "$SRC_DIR/tests/validate-task-evidence.py" "tools/validate-task-evidence.py"
copy_file "$SRC_DIR/task-evidence/.gitkeep" "task-evidence/.gitkeep"
if [ "$VALIDATOR_BUNDLE_MANAGED" = true ]; then
    copy_file "$SRC_DIR/tests/docs_validation.py" "tools/docs_validation.py"
    copy_file "$SRC_DIR/tests/validate-project-docs.py" "tools/validate-docs.py"
else
    echo "SKIP (validator bundle conflict): tools/docs_validation.py, tools/validate-docs.py"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 2))
fi

if [ "$WITH_LEGACY_AGENTS" = true ]; then
    for relative_path in "${OPTIONAL_LEGACY_PATHS[@]}"; do
        copy_file "$SRC_DIR/AGENTS.md" "$relative_path"
    done
fi

while IFS= read -r -d '' source_file; do
    relative_path="${source_file#"$SRC_DIR/"}"
    should_include_doc "$relative_path" || continue
    copy_file "$source_file" "$relative_path"
done < <(find_template_docs)

migrate_renamed_template_files

# Publish the manifest only after every selected file has been copied.
copy_selected_manifest

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
echo "2. Confirm your selected runtime loads its project instructions; Gemma/custom API harnesses must inject docs/templates/1. Agent System Prompt Template.md."
if model_selected gemma; then
    echo "3. Gemma/custom API selected: no repository filename is auto-loaded. Configure the host to inject docs/templates/1. Agent System Prompt Template.md before enabling write tools."
fi
echo "----------------------------------------"
