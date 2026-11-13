#!/bin/bash

# Profile paths are declared only in template-manifest.json. Validate the
# complete source manifest before exposing any path to the installer.
TEMPLATE_PATHS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

validate_template_manifest() {
    python3 -B "$TEMPLATE_PATHS_DIR/lib/installer_lib.py" validate-source-manifest "$TEMPLATE_PATHS_DIR"
}

load_profile_paths() {
    local profile="$1"
    python3 -B "$TEMPLATE_PATHS_DIR/lib/installer_lib.py" load-profile-paths "$TEMPLATE_PATHS_DIR/template-manifest.json" "$profile"
}

load_paths_into_array() {
    local profile="$1"
    local array_name="$2"
    local output
    local path

    if ! output="$(load_profile_paths "$profile")"; then
        return 1
    fi
    case "$array_name" in
        CORE_PROFILE_PATHS) CORE_PROFILE_PATHS=() ;;
        OPTIONAL_ADVANCED_DOCS) OPTIONAL_ADVANCED_DOCS=() ;;
        OPTIONAL_LEGACY_PATHS) OPTIONAL_LEGACY_PATHS=() ;;
        *) return 1 ;;
    esac
    while IFS= read -r path; do
        [ -n "$path" ] || continue
        case "$array_name" in
            CORE_PROFILE_PATHS) CORE_PROFILE_PATHS+=("$path") ;;
            OPTIONAL_ADVANCED_DOCS) OPTIONAL_ADVANCED_DOCS+=("$path") ;;
            OPTIONAL_LEGACY_PATHS) OPTIONAL_LEGACY_PATHS+=("$path") ;;
        esac
    done <<< "$output"
}

if ! validate_template_manifest; then
    echo "Error: template-manifest.json has invalid profile paths." >&2
    return 1
fi

declare -a CORE_PROFILE_PATHS OPTIONAL_ADVANCED_DOCS OPTIONAL_LEGACY_PATHS
load_paths_into_array "core" CORE_PROFILE_PATHS || return 1
load_paths_into_array "--with-advanced-docs" OPTIONAL_ADVANCED_DOCS || return 1
load_paths_into_array "--with-legacy-agents" OPTIONAL_LEGACY_PATHS || return 1
