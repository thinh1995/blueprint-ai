#!/bin/bash
# Setup script for AI Agent Obsidian Template
set -euo pipefail

FORCE=false; DRY_RUN=false; WITH_ADVANCED_DOCS=false; WITH_LEGACY_AGENTS=false
UPDATE=false; DOCTOR=false; STRICT_DOCTOR=false; FORCE_INTERACTIVE=false
MODELS_OPTION_PROVIDED=false; SET_MODELS_PROVIDED=false; PRESET_OPTION_PROVIDED=false
WITH_SKILLS=true; WITHOUT_SKILLS_PROVIDED=false; MANIFEST_UPDATE_ALLOWED=true
VALIDATOR_BUNDLE_MANAGED=true; NEW_FEATURE_MANAGED=true; EXPORT_TASKS_MANAGED=true
MIGRATION_PLAN=""; SELECTED_MODELS=""; MANIFEST_BASE=""; REQUESTED_MODELS=""
UPDATE_MANAGED_ADAPTER_MODELS=""; PRESET_NAME=""
GENERATED_MANIFEST=""; BACKUP_DIR=""; PLAN_EVENTS_FILE=""
INSTALLED_COUNT=0; SKIPPED_COUNT=0; PLANNED_COUNT=0; PRUNED_COUNT=0
PATH_BLOCKED=false; BLOCKED_COUNT=0
STANDARD_DEFAULT_MODELS="claude,antigravity,qwen,opencode,codex,cursor,copilot"
ALL_MODELS="claude,antigravity,qwen,opencode,codex,cursor,copilot,gemma"
ADAPTER_MAPPINGS=(
    "claude|CLAUDE.md|CLAUDE.md"
    "antigravity|GEMINI.md|GEMINI.md"
    "qwen|QWEN.md|QWEN.md"
    "cursor|.cursor/rules/agents.mdc|adapters/cursor-agents.mdc"
    "copilot|.github/copilot-instructions.md|adapters/copilot-instructions.md"
)
SCHEDULED_SKILL_PATHS=(); SKIPPED_USER_SKILL_PATHS=(); PRESERVED_OPTOUT_SKILL_PATHS=()
PRUNE_FILE_PATHS=(); WARN_MODIFIED_ORPHAN_PATHS=(); ACTIVE_TEMP_FILES=(); BLOCKED_PATHS=()

usage() {
    cat <<'EOF'
Usage: setup.sh [--dry-run] [--force] [--update] [--doctor [--strict]] [--migration-plan PATH] [--interactive] [--with-advanced-docs] [--with-legacy-agents] [--without-skills] [--models LIST | --set-models LIST] [--preset NAME]

Installs the AI agent rules and Obsidian starter vault into the current directory.

  --dry-run              Preview planned installs, prunes, or skips; make no changes.
  --force                Replace existing files (symlinks are never overwritten).
  --update               Back up and replace template-managed files using template-manifest.json.
  --doctor [--strict]    Read-only check for Bash/Python, adapters, manifest, tools, skills, and specs.
  --migration-plan PATH  With --dry-run --update, write a .md or .json migration report.
  --with-advanced-docs   Install API, backend, infrastructure, and user-manual notes.
  --with-legacy-agents   Install .agents/AGENTS.md for tools that require it.
  --without-skills       Skip SDD skills (.claude/.agents/.qwen) and record skills_enabled: false.
  --interactive          Prompt for runtime selection even when stdin is not a TTY.
  --models LIST          Additive runtimes: claude,antigravity,qwen,opencode,codex,cursor,copilot,gemma,all.
  --set-models LIST      Authoritative runtime set; backs up & prunes deselected managed adapters/skills.
  --preset NAME          Default feature preset (general, web-api, cli-tool, ai-agent, or custom slug).
EOF
}

run_doctor() {
    local doctor_status=0 src_version
    local strict_arg=()
    [ "$STRICT_DOCTOR" = true ] && strict_arg=(--strict)

    echo "AI template doctor: $DEST_DIR"
    if [ -n "${BASH_VERSION:-}" ]; then echo "PASS Bash: $BASH_VERSION"
    else echo "FAIL Bash: setup.sh must be run by Bash. Remediation: run 'bash /path/to/setup.sh --doctor'." >&2; doctor_status=1; fi
    command -v python3 >/dev/null 2>&1 || { echo "FAIL Python: Python 3 is unavailable. Remediation: install Python 3 and rerun --doctor." >&2; return 1; }
    echo "PASS Python: $(python3 --version 2>&1)"
    if [ ! -f "$DEST_DIR/AGENTS.md" ] || [ -L "$DEST_DIR/AGENTS.md" ]; then
        echo "FAIL policy: a regular AGENTS.md is required. Remediation: restore the canonical policy with setup.sh --update before enabling an agent runtime." >&2
        doctor_status=1
    else
        echo "PASS policy: AGENTS.md is a regular canonical policy file"
    fi

    if [ "$DEST_DIR" = "$SRC_DIR" ]; then
        if [ ! -f "$SRC_DIR/template-manifest.json" ] || [ -L "$SRC_DIR/template-manifest.json" ]; then
            echo "FAIL manifest: a regular source template-manifest.json is required. Remediation: restore template-manifest.json from Git." >&2; doctor_status=1
        elif ! ( source "$SRC_DIR/template-paths.sh" ) >/dev/null 2>&1; then
            echo "FAIL manifest: invalid source template-manifest.json. Remediation: inspect template-manifest.json and template-paths.sh." >&2; doctor_status=1
        else
            src_version="$(python3 -B "$SRC_DIR/lib/installer_lib.py" source-version "$SRC_DIR")"
            echo "PASS manifest: template-owned (source template); version=$src_version"
        fi
        python3 -B "$SRC_DIR/lib/installer_lib.py" doctor-source "$SRC_DIR" || doctor_status=1
    elif [ ! -f "$DEST_DIR/template-manifest.json" ] || [ -L "$DEST_DIR/template-manifest.json" ]; then
        echo "FAIL manifest: a regular template-manifest.json is required. Remediation: run a normal setup, or restore the managed manifest before --update." >&2; doctor_status=1
    else
        python3 -B "$SRC_DIR/lib/installer_lib.py" doctor-manifest "$DEST_DIR" "${strict_arg[@]+"${strict_arg[@]}"}" || doctor_status=1
    fi

    python3 -B "$SRC_DIR/lib/installer_lib.py" doctor-links "$DEST_DIR" || {
        echo "Remediation: repair the reported Markdown link(s), or rerun setup.sh --update for template-managed documentation." >&2; doctor_status=1
    }
    python3 -B "$SRC_DIR/lib/installer_lib.py" doctor-spec-readiness "$DEST_DIR" "$SRC_DIR" "${strict_arg[@]+"${strict_arg[@]}"}" || {
        echo "FAIL spec readiness: semantic documentation validation failed. Remediation: resolve [NEEDS CLARIFICATION] markers, open checkboxes, approval frontmatter, or AC traceability mismatches, then rerun 'python3 tools/validate-docs.py'." >&2; doctor_status=1
    }
    if [ "$doctor_status" -eq 0 ]; then echo "Doctor result: READY"; else echo "Doctor result: NOT READY" >&2; fi
    return "$doctor_status"
}

validate_models() {
    local model seen_models="," flag_label="--models"
    [ "$SET_MODELS_PROVIDED" = true ] && flag_label="--set-models"
    [ -n "$SELECTED_MODELS" ] || { echo "Error: $flag_label requires at least one model." >&2; return 1; }
    [ "$SELECTED_MODELS" = "all" ] && { SELECTED_MODELS="$ALL_MODELS"; return 0; }
    case "$SELECTED_MODELS" in ,*|*,|*,,*) echo "Error: $flag_label must be a comma-separated list without empty values." >&2; return 1 ;; esac
    IFS=',' read -r -a SELECTED_MODEL_LIST <<< "$SELECTED_MODELS"
    for model in "${SELECTED_MODEL_LIST[@]}"; do
        case "$model" in
            claude|antigravity|qwen|opencode|codex|cursor|copilot|gemma) ;;
            *) echo "Error: Unknown model '$model'. Use claude, antigravity, qwen, opencode, codex, cursor, copilot, gemma, or all." >&2; return 1 ;;
        esac
        [[ "$seen_models" == *",$model,"* ]] && { echo "Error: Model '$model' was selected more than once." >&2; return 1; }
        seen_models+="$model,"
    done
}

select_models_interactively() {
    local selection seen_numbers=","
    local -a menu_runtimes=(claude antigravity qwen opencode codex cursor copilot gemma)
    if [ "$MODELS_OPTION_PROVIDED" = true ] || [ "$SET_MODELS_PROVIDED" = true ]; then
        validate_models; return
    fi
    if [ -t 0 ] || [ "$FORCE_INTERACTIVE" = true ]; then
        printf '%s\n' \
            "Select model runtimes/guidance to configure (comma-separated; blank = standard 1..7):" \
            "  [1] Claude Code" "  [2] Antigravity CLI" "  [3] Qwen Code" "  [4] OpenCode" \
            "  [5] OpenAI Codex CLI" "  [6] Cursor" "  [7] GitHub Copilot" \
            "  [8] Gemma / custom API harness (manual wiring)"
        printf "Selection [1,2,3,4,5,6,7]: "
        read -r selection
        case "$selection" in
            ""|1,2,3,4,5,6,7) SELECTED_MODELS="$STANDARD_DEFAULT_MODELS" ;;
            all|1,2,3,4,5,6,7,8) SELECTED_MODELS="$ALL_MODELS" ;;
            ,*|*,|*,,*) echo "Error: Selection must be a comma-separated list without empty values." >&2; return 1 ;;
            *)
                SELECTED_MODELS=""
                IFS=',' read -r -a selected_numbers <<< "$selection"
                for selection in "${selected_numbers[@]}"; do
                    case "$selection" in
                        [1-8]) SELECTED_MODELS+="${SELECTED_MODELS:+,}${menu_runtimes[$((selection - 1))]}" ;;
                        *) echo "Error: Selection must use 1..8 or all." >&2; return 1 ;;
                    esac
                    [[ "$seen_numbers" == *",$selection,"* ]] && { echo "Error: Model selection '$selection' was selected more than once." >&2; return 1; }
                    seen_numbers+="$selection,"
                done ;;
        esac
    else
        SELECTED_MODELS="$STANDARD_DEFAULT_MODELS"
    fi
    validate_models
}

model_selected() { [[ ",$SELECTED_MODELS," == *",$1,"* ]]; }

adapter_selected_for_copy() {
    model_selected "$1" || return 1
    [ "$UPDATE" = false ] && return 0
    [[ ",$UPDATE_MANAGED_ADAPTER_MODELS," == *",$1,"* ]]
}

require_opt_val() {
    [ -n "${2:-}" ] || { echo "Error: $1" >&2; exit 1; }
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --dry-run) DRY_RUN=true ;;
        --force) FORCE=true ;;
        --interactive) FORCE_INTERACTIVE=true ;;
        --update) UPDATE=true ;;
        --doctor) DOCTOR=true ;;
        --strict) STRICT_DOCTOR=true ;;
        --with-advanced-docs) WITH_ADVANCED_DOCS=true ;;
        --with-legacy-agents) WITH_LEGACY_AGENTS=true ;;
        --without-skills) WITH_SKILLS=false; WITHOUT_SKILLS_PROVIDED=true ;;
        --migration-plan) shift; [ "$#" -gt 0 ] || { echo "Error: --migration-plan requires a relative output path." >&2; exit 1; }; MIGRATION_PLAN="$1" ;;
        --migration-plan=*) MIGRATION_PLAN="${1#--migration-plan=}"; require_opt_val "--migration-plan requires a relative output path." "$MIGRATION_PLAN" ;;
        --models|--models=*)
            [ "$MODELS_OPTION_PROVIDED" = false ] || { echo "Error: --models can only be provided once." >&2; exit 1; }
            [ "$SET_MODELS_PROVIDED" = false ] || { echo "Error: --models and --set-models cannot be combined." >&2; exit 1; }
            if [ "$1" = "--models" ]; then shift; [ "$#" -gt 0 ] || { echo "Error: --models requires a value." >&2; exit 1; }; SELECTED_MODELS="$1"
            else SELECTED_MODELS="${1#--models=}"; require_opt_val "--models requires a value." "$SELECTED_MODELS"; fi
            MODELS_OPTION_PROVIDED=true ;;
        --set-models|--set-models=*)
            [ "$SET_MODELS_PROVIDED" = false ] || { echo "Error: --set-models can only be provided once." >&2; exit 1; }
            [ "$MODELS_OPTION_PROVIDED" = false ] || { echo "Error: --models and --set-models cannot be combined." >&2; exit 1; }
            if [ "$1" = "--set-models" ]; then shift; [ "$#" -gt 0 ] || { echo "Error: --set-models requires a value." >&2; exit 1; }; SELECTED_MODELS="$1"
            else SELECTED_MODELS="${1#--set-models=}"; require_opt_val "--set-models requires a value." "$SELECTED_MODELS"; fi
            SET_MODELS_PROVIDED=true ;;
        --preset|--preset=*)
            [ "$PRESET_OPTION_PROVIDED" = false ] || { echo "Error: --preset can only be provided once." >&2; exit 1; }
            if [ "$1" = "--preset" ]; then shift; [ "$#" -gt 0 ] && [ -n "$1" ] || { echo "Error: --preset requires a preset name." >&2; exit 1; }; PRESET_NAME="$1"
            else PRESET_NAME="${1#--preset=}"; require_opt_val "--preset requires a preset name." "$PRESET_NAME"; fi
            PRESET_OPTION_PROVIDED=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
    shift
done

[ "$STRICT_DOCTOR" = true ] && [ "$DOCTOR" = false ] && { echo "Error: --strict can only be used with --doctor." >&2; exit 1; }
if [ "$DOCTOR" = true ] && { [ "$UPDATE" = true ] || [ "$DRY_RUN" = true ] || [ "$FORCE" = true ] || [ -n "$MIGRATION_PLAN" ] || [ "$PRESET_OPTION_PROVIDED" = true ] || [ "$WITHOUT_SKILLS_PROVIDED" = true ] || [ "$MODELS_OPTION_PROVIDED" = true ] || [ "$SET_MODELS_PROVIDED" = true ]; }; then
    echo "Error: --doctor cannot be combined with install or update flags." >&2
    exit 1
fi

SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
DEST_DIR="$(pwd -P)"

if [[ "$SRC_DIR" == "$DEST_DIR" || "$DEST_DIR" == "$SRC_DIR"/* ]]; then
    if [ "$DOCTOR" = true ] && [ "$DEST_DIR" = "$SRC_DIR" ]; then
        run_doctor; exit $?
    fi
    echo "Error: Target directory must not be the template directory or a subdirectory of it."
    echo "Usage: /path/to/ai-project-template/setup.sh"
    exit 1
fi
[[ "$SRC_DIR" == "$DEST_DIR"/* ]] && echo "Note: Template folder is inside the target project; existing target files will still be preserved by default."
command -v python3 >/dev/null 2>&1 || { echo "Error: Python 3 is required to validate and generate the template manifest." >&2; exit 1; }

if [ "$DOCTOR" = true ]; then
    run_doctor; exit $?
fi

if [ -n "$MIGRATION_PLAN" ]; then
    [ "$UPDATE" = true ] && [ "$DRY_RUN" = true ] || { echo "Error: --migration-plan requires --dry-run --update." >&2; exit 1; }
    case "$MIGRATION_PLAN" in
        /*|*".."*|*"$'\n'"*|*"$'\r'"*) echo "Error: --migration-plan must be a safe relative output path." >&2; exit 1 ;;
    esac
    if [ -e "$DEST_DIR/$MIGRATION_PLAN" ] || [ -L "$DEST_DIR/$MIGRATION_PLAN" ]; then
        echo "Error: Refusing to overwrite existing migration plan: $MIGRATION_PLAN" >&2
        exit 1
    fi
fi

source "$SRC_DIR/template-paths.sh" || { echo "Error: Cannot safely load template profile paths." >&2; exit 1; }

select_update_models() {
    local existing_manifest="$DEST_DIR/template-manifest.json"
    local update_metadata inferred_models prior_advanced prior_legacy prior_skills set_models_arg=""
    if [ "$MODELS_OPTION_PROVIDED" = true ]; then
        echo "Error: --update derives runtime adapters from the installed manifest; use --update --set-models <list> to reconfigure runtimes or a normal install to add one." >&2
        exit 1
    fi
    if [ "$SET_MODELS_PROVIDED" = true ]; then
        validate_models
        set_models_arg="$SELECTED_MODELS"
    fi
    if [ ! -f "$existing_manifest" ] || [ -L "$existing_manifest" ]; then
        echo "Error: --update requires a regular, template-owned template-manifest.json. Use a normal install for a new project." >&2
        exit 1
    fi
    if ! update_metadata="$(python3 -B "$SRC_DIR/lib/installer_lib.py" select-update-models "$SRC_DIR" "$DEST_DIR" "$set_models_arg" 2>/dev/null)"; then
        echo "Error: --update requires a valid template-owned template-manifest.json." >&2
        exit 1
    fi
    IFS='|' read -r inferred_models prior_advanced prior_legacy UPDATE_MANAGED_ADAPTER_MODELS prior_skills <<< "$update_metadata"
    SELECTED_MODELS="$inferred_models"
    [ "$prior_advanced" = true ] && WITH_ADVANCED_DOCS=true
    [ "$prior_legacy" = true ] && WITH_LEGACY_AGENTS=true
    [ "$WITHOUT_SKILLS_PROVIDED" = false ] && WITH_SKILLS="$prior_skills"
    validate_models
}

validate_preset_option() {
    local current_path="$DEST_DIR" part
    [ "$PRESET_OPTION_PROVIDED" = true ] || return 0
    [[ "$PRESET_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]] || { echo "Error: Invalid --preset '$PRESET_NAME'. Expected lowercase kebab-case slug." >&2; exit 1; }
    case "$PRESET_NAME" in general|web-api|cli-tool|ai-agent) return 0 ;; esac
    for part in "docs" "templates" "presets" "$PRESET_NAME"; do
        current_path="$current_path/$part"
        if [ -L "$current_path" ] || [ ! -d "$current_path" ]; then
            echo "Error: Custom preset '$PRESET_NAME' requires an existing non-symlink directory at docs/templates/presets/$PRESET_NAME." >&2
            exit 1
        fi
    done
}

if [ "$UPDATE" = true ]; then select_update_models; else select_models_interactively; fi
validate_preset_option

cleanup_temporary_files() {
    local temporary_file
    [ -n "$GENERATED_MANIFEST" ] && [ -e "$GENERATED_MANIFEST" ] && rm -f "$GENERATED_MANIFEST"
    for temporary_file in "${ACTIVE_TEMP_FILES[@]-}"; do
        [ -e "$temporary_file" ] && rm -f "$temporary_file"
    done
    [ -n "$PLAN_EVENTS_FILE" ] && [ -e "$PLAN_EVENTS_FILE" ] && rm -f "$PLAN_EVENTS_FILE"
    return 0
}
trap cleanup_temporary_files EXIT
trap 'cleanup_temporary_files; exit 130' INT TERM

plan_record() {
    [ -n "$MIGRATION_PLAN" ] || return 0
    printf '%s\t%s\t%s\n' "$1" "$2" "$3" >> "$PLAN_EVENTS_FILE"
}

write_migration_plan() {
    [ -n "$MIGRATION_PLAN" ] || return 0
    python3 -B "$SRC_DIR/lib/installer_lib.py" write-migration-plan "$PLAN_EVENTS_FILE" "$DEST_DIR/$MIGRATION_PLAN" "$DEST_DIR"
    echo "Migration plan: $MIGRATION_PLAN"
}

[ -n "$MIGRATION_PLAN" ] && PLAN_EVENTS_FILE="$(mktemp "${TMPDIR:-/tmp}/ai-template-plan.XXXXXX")"

prepare_manifest_models() {
    local existing_manifest="$DEST_DIR/template-manifest.json"
    REQUESTED_MODELS="$SELECTED_MODELS"
    MANIFEST_BASE="$SRC_DIR/template-manifest.json"
    MANIFEST_UPDATE_ALLOWED=true
    [ ! -e "$existing_manifest" ] && [ ! -L "$existing_manifest" ] && return 0
    if [ -L "$existing_manifest" ]; then
        MANIFEST_UPDATE_ALLOWED=false
        return 0
    fi
    if ! REQUESTED_MODELS="$(python3 -B "$SRC_DIR/lib/installer_lib.py" prepare-manifest-models "$DEST_DIR" "$SELECTED_MODELS" "$SET_MODELS_PROVIDED")"; then
        echo "Error: Cannot safely update template-manifest.json selection; use a valid template-owned manifest." >&2
        return 1
    fi
    if [ "$REQUESTED_MODELS" = "UNMANAGED" ]; then
        MANIFEST_UPDATE_ALLOWED=false
        REQUESTED_MODELS="$SELECTED_MODELS"
        return 0
    fi
    MANIFEST_BASE="$existing_manifest"
}

ensure_backup_dir() {
    [ -n "$BACKUP_DIR" ] && return 0
    BACKUP_DIR="$(mktemp -d "$DEST_DIR/.ai-template-backup.XXXXXX")"
    printf '%s\n' \
        '# Template update recovery' '' \
        'This update replaces files one at a time. If it is interrupted or fails, the project can contain a mix of versions.' '' \
        'The backup tree mirrors the project root. To restore one replaced file, run from the project root:' '' \
        '```bash' 'cp -Pp ".ai-template-backup.XXXXXX/path/to/file" "path/to/file"' '```' '' \
        'Replace `.ai-template-backup.XXXXXX` and `path/to/file` with the reported backup directory and desired path. Newly created files are listed in `CREATED_FILES.txt`.' \
        > "$BACKUP_DIR/RECOVERY.md"
    echo "BACKUP: $BACKUP_DIR"
}

backup_existing_file() {
    local relative_path="$1" force_backup="${2:-false}" destination_file="$DEST_DIR/$1" backup_file
    [ "$UPDATE" = true ] || [ "$force_backup" = true ] || return 0
    [ -e "$destination_file" ] && [ ! -L "$destination_file" ] || return 0
    ensure_backup_dir
    backup_file="$BACKUP_DIR/$relative_path"
    mkdir -p "$(dirname "$backup_file")"
    cp -Pp "$destination_file" "$backup_file"
}

record_created_file() {
    [ "$UPDATE" = true ] || return 0
    ensure_backup_dir
    printf '%s\n' "$1" >> "$BACKUP_DIR/CREATED_FILES.txt"
}

copy_file() {
    local source_file="$1" relative_path="$2" destination_file="$DEST_DIR/$2" destination_dir temporary_file
    check_destination_path "$relative_path"
    [ "$DRY_RUN" = true ] && [ "$PATH_BLOCKED" = true ] && return 0

    if [ -L "$destination_file" ] && { [ "$FORCE" = true ] || [ "$UPDATE" = true ]; }; then
        echo "Error: Refusing to overwrite symlink: $relative_path" >&2
        return 1
    fi
    if { [ -e "$destination_file" ] || [ -L "$destination_file" ]; } && [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
        echo "SKIP (exists): $relative_path"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return 0
    fi
    if [ "$DRY_RUN" = true ]; then
        if [ -e "$destination_file" ] || [ -L "$destination_file" ]; then
            echo "UPDATE (backup): $relative_path"
            plan_record "replace" "$relative_path" "managed file will be backed up and replaced"
        else
            echo "INSTALL: $relative_path"
            plan_record "install" "$relative_path" "new template-managed file"
        fi
        PLANNED_COUNT=$((PLANNED_COUNT + 1))
        return 0
    fi

    if [ -e "$destination_file" ]; then
        backup_existing_file "$relative_path"
    else
        record_created_file "$relative_path"
    fi

    destination_dir="$(dirname "$destination_file")"
    mkdir -p "$destination_dir"
    temporary_file="$(mktemp "$destination_dir/.ai-template.XXXXXX")"
    ACTIVE_TEMP_FILES+=("$temporary_file")
    if ! cp -Pp "$source_file" "$temporary_file"; then
        rm -f "$temporary_file"
        return 1
    fi
    mv -f "$temporary_file" "$destination_file"
    ACTIVE_TEMP_FILES=("${ACTIVE_TEMP_FILES[@]:0:${#ACTIVE_TEMP_FILES[@]}-1}")
    echo "INSTALLED: $relative_path"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
}

prune_empty_dirs() {
    local rel_dir="$1"
    while [ -n "$rel_dir" ] && [ "$rel_dir" != "." ]; do
        case "$rel_dir" in
            .claude|.claude/*|.agents|.agents/*|.qwen|.qwen/*|.cursor|.cursor/*|.github)
                rmdir "$DEST_DIR/$rel_dir" 2>/dev/null || break ;;
            *) break ;;
        esac
        rel_dir="$(dirname "$rel_dir")"
    done
}

prune_deselected_files() {
    local rel
    if [ "${#WARN_MODIFIED_ORPHAN_PATHS[@]}" -gt 0 ]; then
        for rel in "${WARN_MODIFIED_ORPHAN_PATHS[@]}"; do
            echo "WARN: preserving user-modified deselected file: $rel"
            plan_record "preserve" "$rel" "user-modified deselected file preserved on disk"
            SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        done
    fi
    if [ "${#PRUNE_FILE_PATHS[@]}" -gt 0 ]; then
        for rel in "${PRUNE_FILE_PATHS[@]}"; do
            if [ "$DRY_RUN" = true ]; then
                echo "PRUNE (backup): $rel"
                plan_record "migrate" "$rel" "deselected template-managed file will be backed up and removed"
                PLANNED_COUNT=$((PLANNED_COUNT + 1))
                continue
            fi
            backup_existing_file "$rel" true
            rm -f "$DEST_DIR/$rel"
            prune_empty_dirs "$(dirname "$rel")"
            echo "PRUNED (deselected): $rel"
            PRUNED_COUNT=$((PRUNED_COUNT + 1))
        done
    fi
}

copy_selected_manifest() {
    local skipped_skills_arg=""
    if [ "${#SKIPPED_USER_SKILL_PATHS[@]}" -gt 0 ]; then
        local IFS='|'; skipped_skills_arg="${SKIPPED_USER_SKILL_PATHS[*]}"
    fi
    if [ "$MANIFEST_UPDATE_ALLOWED" = false ]; then
        echo "SKIP (unmanaged manifest): template-manifest.json"
        plan_record "manual" "template-manifest.json" "unmanaged manifest must be reviewed manually"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return 0
    fi
    if [ "$DRY_RUN" = true ]; then
        if [ -e "$DEST_DIR/template-manifest.json" ] || [ -L "$DEST_DIR/template-manifest.json" ]; then
            if [ "$UPDATE" = true ]; then
                echo "UPDATE (backup): template-manifest.json"
                plan_record "replace" "template-manifest.json" "managed manifest will be backed up and regenerated"
            else
                echo "UPDATE: template-manifest.json"
            fi
        else
            echo "INSTALL: template-manifest.json"
            plan_record "install" "template-manifest.json" "new template-managed manifest"
        fi
        PLANNED_COUNT=$((PLANNED_COUNT + 1))
        return 0
    fi

    GENERATED_MANIFEST="$(mktemp "$DEST_DIR/.ai-template-manifest.XXXXXX")"
    cp -Pp "$SRC_DIR/template-manifest.json" "$GENERATED_MANIFEST" || return 1
    python3 -B "$SRC_DIR/lib/installer_lib.py" write-manifest \
        "$SRC_DIR" "$DEST_DIR" "$MANIFEST_BASE" "$GENERATED_MANIFEST" \
        "$REQUESTED_MODELS" "$WITH_ADVANCED_DOCS" "$WITH_LEGACY_AGENTS" \
        "$VALIDATOR_BUNDLE_MANAGED" "$NEW_FEATURE_MANAGED" "$EXPORT_TASKS_MANAGED" \
        "$PRESET_OPTION_PROVIDED" "$PRESET_NAME" "$WITH_SKILLS" "$skipped_skills_arg" || return 1

    backup_existing_file "template-manifest.json"
    [ -L "$DEST_DIR/template-manifest.json" ] && { echo "Error: Refusing to overwrite symlink: template-manifest.json" >&2; return 1; }
    mv -f "$GENERATED_MANIFEST" "$DEST_DIR/template-manifest.json"
    GENERATED_MANIFEST=""
    echo "INSTALLED: template-manifest.json"
    INSTALLED_COUNT=$((INSTALLED_COUNT + 1))
}

should_include_doc() {
    local relative_path="$1" profile_path
    for profile_path in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
        if [ "$relative_path" = "$profile_path" ] || [[ "$relative_path" == "$profile_path/"* ]]; then
            [ "$WITH_ADVANCED_DOCS" = true ]; return
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

report_blocked_path() {
    local reason="$1" relative_path="$2" blocked_path
    for blocked_path in "${BLOCKED_PATHS[@]-}"; do
        [ "$blocked_path" = "$relative_path" ] && return 0
    done
    echo "BLOCKED ($reason): $relative_path"
    plan_record "blocked" "$relative_path" "$reason; resolve this path before a real update"
    BLOCKED_PATHS+=("$relative_path")
    BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
}

find_template_docs() {
    find "$SRC_DIR/docs" -path "$SRC_DIR/docs/internal" -prune -o -type f ! -name '.DS_Store' -print0
}

migrate_renamed_template_files() {
    local mapping old_relative_path new_relative_path expected_sha256 old_path
    [ "$UPDATE" = true ] || return 0
    for mapping in \
        "docs/templates/agent-system-prompt-template.md|docs/templates/1. Agent System Prompt Template.md|aa6e9c623f27ad7c77d0b9b053a9c885c837942175fdd88d8ee4c9257b7c5a6e" \
        "docs/templates/documentation-subagent-contract.md|docs/templates/2. Documentation Subagent Contract.md|57d3c4b586c86429bc852db1c35c40e13f8a6fd2ca4f33dd6225d20411b76430" \
        "docs/templates/task-evidence-template.md|docs/templates/3. Task Evidence Template.md|9dda6623fddc2eeb07c70e756c29e7ce2a8b26765722260625e34a573bce23a1" \
        "docs/templates/runtime-delegation-evidence-template.md|docs/templates/4. Runtime Delegation Evidence Template.md|3d8960ff20f3b27c7311e61942552112aadf5ebdc25910b11bc92927af6f62e4,6fb83edc810b6e2bc70a089e84277f8b35966598e9ed986ab00d012332e01b25"; do
        IFS='|' read -r old_relative_path new_relative_path expected_sha256 <<< "$mapping"
        old_path="$DEST_DIR/$old_relative_path"
        [ -e "$old_path" ] || [ -L "$old_path" ] || continue
        python3 -B "$SRC_DIR/lib/installer_lib.py" check-legacy-rename "$DEST_DIR" "$old_relative_path" || continue
        if [ -L "$old_path" ]; then
            echo "SKIP (symlink legacy template): $old_relative_path"
            plan_record "preserve" "$old_relative_path" "legacy template is a symlink; resolve manually"
            continue
        fi
        if [ ! -f "$old_path" ]; then
            echo "SKIP (non-file legacy template): $old_relative_path"
            plan_record "manual" "$old_relative_path" "legacy template is not a regular file"
            continue
        fi
        if ! python3 -B "$SRC_DIR/lib/installer_lib.py" verify-sha256 "$DEST_DIR" "$old_relative_path" "$expected_sha256"; then
            echo "SKIP (user-modified legacy template): $old_relative_path"
            plan_record "preserve" "$old_relative_path" "user-modified legacy template"
            continue
        fi
        if [ "$DRY_RUN" = true ]; then
            echo "MIGRATE (remove renamed template): $old_relative_path -> $new_relative_path"
            plan_record "migrate" "$old_relative_path" "remove unchanged legacy name after $new_relative_path is installed"
            PLANNED_COUNT=$((PLANNED_COUNT + 1))
            continue
        fi
        backup_existing_file "$old_relative_path"
        rm -f "$old_path"
        echo "MIGRATED (renamed template): $old_relative_path -> $new_relative_path"
    done
}

check_destination_path() {
    local relative_path="$1" path_part current_path="$DEST_DIR" path_index IFS='/'
    local -a path_parts
    PATH_BLOCKED=false
    read -r -a path_parts <<< "$relative_path"
    for path_index in "${!path_parts[@]}"; do
        path_part="${path_parts[$path_index]}"
        current_path="$current_path/$path_part"
        if [ -L "$current_path" ]; then
            if [ "$path_index" -eq "$((${#path_parts[@]} - 1))" ] && [ "$FORCE" = false ] && [ "$UPDATE" = false ]; then
                continue
            fi
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "symlink" "$relative_path"; PATH_BLOCKED=true; return 0
            fi
            echo "Error: Refusing to write through symlink: $relative_path" >&2; return 1
        fi
        if [ "$path_index" -eq "$((${#path_parts[@]} - 1))" ] && [ -e "$current_path" ] && [ -d "$current_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "path conflict" "$relative_path"; PATH_BLOCKED=true; return 0
            fi
            echo "Error: Expected file but found directory in template path: $relative_path" >&2; return 1
        fi
        if [ "$path_index" -lt "$((${#path_parts[@]} - 1))" ] && [ -e "$current_path" ] && [ ! -d "$current_path" ]; then
            if [ "$DRY_RUN" = true ]; then
                report_blocked_path "path conflict" "$relative_path"; PATH_BLOCKED=true; return 0
            fi
            echo "Error: Expected directory but found file in template path: $relative_path" >&2; return 1
        fi
    done
}

prepare_ownership() {
    local ownership_lines line kind val
    SCHEDULED_SKILL_PATHS=(); SKIPPED_USER_SKILL_PATHS=(); PRESERVED_OPTOUT_SKILL_PATHS=()
    PRUNE_FILE_PATHS=(); WARN_MODIFIED_ORPHAN_PATHS=()
    ownership_lines="$(python3 -B "$SRC_DIR/lib/installer_lib.py" prepare-ownership \
        "$SRC_DIR" "$DEST_DIR" "$SELECTED_MODELS" "$WITH_SKILLS" "$FORCE" "$UPDATE" "$SET_MODELS_PROVIDED")"
    while IFS= read -r line; do
        [ -n "$line" ] || continue
        IFS='|' read -r kind val <<< "$line"
        case "$kind" in
            VALIDATOR_BUNDLE) VALIDATOR_BUNDLE_MANAGED="$val" ;;
            NEW_FEATURE) NEW_FEATURE_MANAGED="$val" ;;
            EXPORT_TASKS) EXPORT_TASKS_MANAGED="$val" ;;
            SCHEDULE_SKILL) SCHEDULED_SKILL_PATHS+=("$val") ;;
            USER_SKILL) SKIPPED_USER_SKILL_PATHS+=("$val") ;;
            OPTOUT_SKILL) PRESERVED_OPTOUT_SKILL_PATHS+=("$val") ;;
            PRUNE_FILE) PRUNE_FILE_PATHS+=("$val") ;;
            WARN_MODIFIED_ORPHAN) WARN_MODIFIED_ORPHAN_PATHS+=("$val") ;;
        esac
    done <<< "$ownership_lines"
}

preflight_destinations() {
    local source_file relative_path mapping model adapter_dest adapter_src failed=false
    prepare_manifest_models || failed=true
    prepare_ownership
    for relative_path in "AGENTS.md" "template-manifest.json" "tools/validate-task-evidence.py" "task-evidence/.gitkeep"; do
        check_destination_path "$relative_path" || failed=true
    done
    [ "$VALIDATOR_BUNDLE_MANAGED" = true ] && { check_destination_path "tools/docs_validation.py" || failed=true; check_destination_path "tools/validate-docs.py" || failed=true; }
    [ "$NEW_FEATURE_MANAGED" = true ] && { check_destination_path "tools/new-feature.py" || failed=true; }
    [ "$EXPORT_TASKS_MANAGED" = true ] && { check_destination_path "tools/export-tasks.py" || failed=true; }
    for mapping in "${ADAPTER_MAPPINGS[@]}"; do
        IFS='|' read -r model adapter_dest adapter_src <<< "$mapping"
        adapter_selected_for_copy "$model" && { check_destination_path "$adapter_dest" || failed=true; }
    done
    for relative_path in ${SCHEDULED_SKILL_PATHS[@]+"${SCHEDULED_SKILL_PATHS[@]}"}; do
        check_destination_path "$relative_path" || failed=true
    done
    if [ "$WITH_LEGACY_AGENTS" = true ]; then
        for relative_path in ${OPTIONAL_LEGACY_PATHS[@]+"${OPTIONAL_LEGACY_PATHS[@]}"}; do
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
[ "$UPDATE" = true ] && echo "Update mode: existing managed files will be backed up then replaced."
if [ "$DRY_RUN" = true ]; then
    if [ -n "$MIGRATION_PLAN" ]; then
        echo "Dry run only — no template-managed files will be changed; the requested migration plan will be written: $MIGRATION_PLAN"
    else
        echo "Dry run only — no files will be changed."
    fi
fi

preflight_destinations
copy_file "$SRC_DIR/AGENTS.md" "AGENTS.md"

for mapping in "${ADAPTER_MAPPINGS[@]}"; do
    IFS='|' read -r model adapter_dest adapter_src <<< "$mapping"
    if adapter_selected_for_copy "$model"; then
        copy_file "$SRC_DIR/$adapter_src" "$adapter_dest"
    elif [ "$UPDATE" = true ] && model_selected "$model"; then
        echo "SKIP (user-owned adapter): $adapter_dest"
        plan_record "preserve" "$adapter_dest" "user-owned or unmanaged runtime adapter"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
done

copy_managed_sdd_tool() {
    if [ "$1" = true ]; then
        copy_file "$SRC_DIR/tools/$2" "tools/$2"
    else
        echo "SKIP (user-owned tool): tools/$2"
        plan_record "manual" "tools/$2" "user-owned SDD tool will be preserved"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    fi
}

copy_file "$SRC_DIR/tools/validate-task-evidence.py" "tools/validate-task-evidence.py"
copy_file "$SRC_DIR/task-evidence/.gitkeep" "task-evidence/.gitkeep"
if [ "$VALIDATOR_BUNDLE_MANAGED" = true ]; then
    copy_file "$SRC_DIR/tools/docs_validation.py" "tools/docs_validation.py"
    copy_file "$SRC_DIR/tools/validate-docs.py" "tools/validate-docs.py"
else
    echo "SKIP (validator bundle conflict): tools/docs_validation.py, tools/validate-docs.py"
    plan_record "manual" "tools/docs_validation.py" "user-owned validator bundle will be preserved"
    plan_record "manual" "tools/validate-docs.py" "user-owned validator bundle will be preserved"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 2))
fi
copy_managed_sdd_tool "$NEW_FEATURE_MANAGED" "new-feature.py"
copy_managed_sdd_tool "$EXPORT_TASKS_MANAGED" "export-tasks.py"

if [ "$WITH_LEGACY_AGENTS" = true ]; then
    for relative_path in ${OPTIONAL_LEGACY_PATHS[@]+"${OPTIONAL_LEGACY_PATHS[@]}"}; do
        copy_file "$SRC_DIR/AGENTS.md" "$relative_path"
    done
fi
for relative_path in ${SCHEDULED_SKILL_PATHS[@]+"${SCHEDULED_SKILL_PATHS[@]}"}; do
    skill_slug="${relative_path#*/skills/}"; skill_slug="${skill_slug%/SKILL.md}"
    copy_file "$SRC_DIR/skills/$skill_slug/SKILL.md" "$relative_path"
done
for relative_path in ${SKIPPED_USER_SKILL_PATHS[@]+"${SKIPPED_USER_SKILL_PATHS[@]}"}; do
    echo "SKIP (user-owned skill): $relative_path"
    plan_record "manual" "$relative_path" "user-owned skill will be preserved"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
done
for relative_path in ${PRESERVED_OPTOUT_SKILL_PATHS[@]+"${PRESERVED_OPTOUT_SKILL_PATHS[@]}"}; do
    echo "SKIP (skills disabled): $relative_path"
    plan_record "preserve" "$relative_path" "existing skill file preserved on disk (--without-skills)"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
done

prune_deselected_files

while IFS= read -r -d '' source_file; do
    relative_path="${source_file#"$SRC_DIR/"}"
    should_include_doc "$relative_path" || continue
    copy_file "$source_file" "$relative_path"
done < <(find_template_docs)

migrate_renamed_template_files
copy_selected_manifest
write_migration_plan

echo "----------------------------------------"
if [ "$DRY_RUN" = true ]; then
    echo "Dry run complete: $PLANNED_COUNT file(s) would be installed; $SKIPPED_COUNT existing file(s) would be preserved; $BLOCKED_COUNT path(s) are blocked."
elif [ "$INSTALLED_COUNT" -eq 0 ] && [ "$PRUNED_COUNT" -eq 0 ]; then
    echo "No files installed: $SKIPPED_COUNT existing file(s) were preserved. Use --force only if you intend to replace them."
else
    echo "✅ Setup complete: installed $INSTALLED_COUNT file(s); preserved $SKIPPED_COUNT existing file(s)."
fi
echo ""
echo "Next steps:"
echo "1. Open this project folder in Obsidian as a Vault."
echo "2. Confirm your selected runtime loads its project instructions; Gemma/custom API harnesses must inject docs/templates/1. Agent System Prompt Template.md."
next_step_num=3
if [ "$WITH_SKILLS" = true ] && [ "$SELECTED_MODELS" != "gemma" ]; then
    echo "$next_step_num. Type /sdd-docs to initialize project docs, /sdd-specify [--mini] <feature-slug> to start a feature, or /sdd-fix <bug> for a fast-track fix."
    next_step_num=$((next_step_num + 1))
fi
if model_selected gemma; then
    echo "$next_step_num. Gemma/custom API selected: no repository filename is auto-loaded. Configure the host to inject docs/templates/1. Agent System Prompt Template.md before enabling write tools."
fi
echo "----------------------------------------"
