#!/bin/bash

# Profile paths are declared only in template-manifest.json. Validate the
# complete source manifest before exposing any path to the installer.
TEMPLATE_PATHS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

validate_template_manifest() {
    python3 - "$TEMPLATE_PATHS_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path, PurePosixPath

root = Path(sys.argv[1])
manifest = json.loads((root / "template-manifest.json").read_text(encoding="utf-8"))
if manifest.get("template") != "ai-agent-obsidian-project-template":
    raise ValueError("manifest is not owned by ai-agent-obsidian-project-template")
if not isinstance(manifest.get("version"), str) or not re.fullmatch(r"\d+\.\d+\.\d+", manifest["version"]):
    raise ValueError("manifest version must be semantic version text")
profiles = manifest.get("profiles")
required = {"core", "--with-advanced-docs", "--with-legacy-agents"}
if not isinstance(profiles, dict) or not required.issubset(profiles):
    raise ValueError("manifest must define core, --with-advanced-docs, and --with-legacy-agents profiles")

overrides = {
    "tools/validate-task-evidence.py": "tests/validate-task-evidence.py",
    "tools/docs_validation.py": "tests/docs_validation.py",
    "tools/validate-docs.py": "tests/validate-project-docs.py",
    ".agents/AGENTS.md": "AGENTS.md",
}

def validate_path(value: object, profile: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{profile} contains an empty or non-string path")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ValueError(f"{profile} contains a control character")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"{profile} contains an unsafe path: {value}")
    return value

all_paths: dict[str, str] = {}
for name in required:
    entries = profiles[name]
    if not isinstance(entries, list):
        raise ValueError(f"{name} must be a list")
    for entry in entries:
        entry = validate_path(entry, name)
        if entry in all_paths:
            raise ValueError(f"manifest profile path is duplicated: {entry}")
        for existing, existing_profile in all_paths.items():
            if entry.startswith(existing + "/") or existing.startswith(entry + "/"):
                raise ValueError(f"manifest profile paths overlap: {existing_profile}:{existing} and {name}:{entry}")
        all_paths[entry] = name
        source = root / overrides.get(entry, entry)
        if not source.exists() or source.is_symlink():
            raise ValueError(f"manifest path is missing or unsafe in template: {entry}")

managed_paths = manifest.get("managed_paths")
if not isinstance(managed_paths, list):
    raise ValueError("managed_paths must be a list")
managed_set: set[str] = set()
for entry in managed_paths:
    entry = validate_path(entry, "managed_paths")
    if entry in managed_set:
        raise ValueError(f"managed_paths contains a duplicate: {entry}")
    managed_set.add(entry)
    source = root / overrides.get(entry, entry)
    if not source.exists() or source.is_symlink():
        raise ValueError(f"managed path is missing or unsafe in template: {entry}")

managed_profiles = manifest.get("managed_profiles")
if not isinstance(managed_profiles, list) or any(profile not in required for profile in managed_profiles):
    raise ValueError("managed_profiles must contain only known profile names")

def covers(entry: str, path: str) -> bool:
    return path == entry or path.startswith(entry + "/")

core = profiles["core"]
advanced = profiles["--with-advanced-docs"]
for source in (root / "docs").rglob("*"):
    if not source.is_file() or source.name == ".DS_Store" or "internal" in source.relative_to(root / "docs").parts:
        continue
    relative = source.relative_to(root).as_posix()
    if not any(covers(entry, relative) for entry in [*core, *advanced]):
        raise ValueError(f"template documentation is not declared by a profile: {relative}")
PY
}

load_profile_paths() {
    local profile="$1"

    python3 - "$TEMPLATE_PATHS_DIR/template-manifest.json" "$profile" <<'PY'
import json
import sys
from pathlib import Path

profile = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))["profiles"][sys.argv[2]]
print("\n".join(profile))
PY
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
