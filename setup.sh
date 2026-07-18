#!/bin/bash

# Setup script for AI Agent Obsidian Template
set -euo pipefail

FORCE=false
DRY_RUN=false
WITH_ADVANCED_DOCS=false
WITH_LEGACY_AGENTS=false
INSTALLED_COUNT=0
SKIPPED_COUNT=0
PLANNED_COUNT=0
PATH_BLOCKED=false
BLOCKED_COUNT=0
BLOCKED_PATHS=()

usage() {
    cat <<'EOF'
Usage: setup.sh [--dry-run] [--force] [--with-advanced-docs] [--with-legacy-agents]

Installs the AI agent rules and Obsidian starter vault into the current directory.

  --dry-run  Show which files would be installed or skipped; make no changes.
  --force    Replace existing template-owned files. Without this flag, existing
             files are preserved. Symlinks are never overwritten.
  --with-advanced-docs  Install API, backend, infrastructure, and user-manual
                        starter notes.
  --with-legacy-agents  Install .agents/AGENTS.md for tools that require it.
EOF
}

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --force) FORCE=true ;;
        --with-advanced-docs) WITH_ADVANCED_DOCS=true ;;
        --with-legacy-agents) WITH_LEGACY_AGENTS=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: Unknown option: $arg" >&2; usage >&2; exit 1 ;;
    esac
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

    # Preserve the template file mode while still replacing the destination
    # directory entry atomically below.
    if ! cp -p "$source_file" "$temporary_file"; then
        rm -f "$temporary_file"
        return 1
    fi

    # Replacing the directory entry instead of copying over it prevents a
    # forced install from modifying another path that shares a hard link.
    mv -f "$temporary_file" "$destination_file"
    echo "INSTALLED: $relative_path"
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

    for relative_path in "AGENTS.md" "CLAUDE.md" "template-manifest.json" "tools/validate-task-evidence.py" "tools/validate-docs.py"; do
        check_destination_path "$relative_path" || failed=true
    done
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
copy_file "$SRC_DIR/CLAUDE.md" "CLAUDE.md"

# Record the template version and managed paths for later audits/upgrades.
copy_file "$SRC_DIR/template-manifest.json" "template-manifest.json"

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
echo "2. Confirm your AI tool reads AGENTS.md (or CLAUDE.md when using Claude Code) before implementation work."
echo "----------------------------------------"
