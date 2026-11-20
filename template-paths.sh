#!/bin/bash

# Profile paths are declared only in template-manifest.json. Validate the
# complete source manifest before exposing any path to the installer.
TEMPLATE_PATHS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

declare -a CORE_PROFILE_PATHS OPTIONAL_ADVANCED_DOCS OPTIONAL_LEGACY_PATHS
CORE_PROFILE_PATHS=()
OPTIONAL_ADVANCED_DOCS=()
OPTIONAL_LEGACY_PATHS=()

if ! _manifest_state_out="$(python3 -B "$TEMPLATE_PATHS_DIR/lib/installer_lib.py" load-manifest-state "$TEMPLATE_PATHS_DIR")"; then
    echo "Error: template-manifest.json has invalid profile paths." >&2
    unset _manifest_state_out
    return 1 2>/dev/null || exit 1
fi

while IFS=$'\t' read -r _tp_profile _tp_path _tp_extra; do
    [ -n "$_tp_profile" ] || [ -n "$_tp_path" ] || continue
    if [ -z "$_tp_profile" ] || [ -z "$_tp_path" ] || [ -n "$_tp_extra" ]; then
        echo "Error: template-manifest.json has invalid profile paths." >&2
        unset _manifest_state_out _tp_profile _tp_path _tp_extra
        return 1 2>/dev/null || exit 1
    fi
    case "$_tp_profile" in
        core) CORE_PROFILE_PATHS+=("$_tp_path") ;;
        --with-advanced-docs) OPTIONAL_ADVANCED_DOCS+=("$_tp_path") ;;
        --with-legacy-agents) OPTIONAL_LEGACY_PATHS+=("$_tp_path") ;;
        *)
            echo "Error: template-manifest.json has invalid profile paths." >&2
            unset _manifest_state_out _tp_profile _tp_path _tp_extra
            return 1 2>/dev/null || exit 1
            ;;
    esac
done <<< "$_manifest_state_out"
unset _manifest_state_out _tp_profile _tp_path _tp_extra
