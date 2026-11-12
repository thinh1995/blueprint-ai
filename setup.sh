#!/bin/bash

# Setup script for AI Agent Obsidian Template
set -euo pipefail

FORCE=false
DRY_RUN=false
WITH_ADVANCED_DOCS=false
WITH_LEGACY_AGENTS=false
UPDATE=false
DOCTOR=false
MIGRATION_PLAN=""
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
NEW_FEATURE_MANAGED=true
EXPORT_TASKS_MANAGED=true
PRESET_NAME=""
PRESET_OPTION_PROVIDED=false
WITH_SKILLS=true
WITHOUT_SKILLS_PROVIDED=false
SDD_SKILL_SLUGS=(
    "sdd-docs"
    "sdd-specify"
    "sdd-clarify"
    "sdd-plan"
    "sdd-tasks"
    "sdd-analyze"
    "sdd-implement"
)
SCHEDULED_SKILL_PATHS=()
SKIPPED_USER_SKILL_PATHS=()
PRESERVED_OPTOUT_SKILL_PATHS=()
MANAGED_SKILL_PATHS=""
GENERATED_MANIFEST=""
ACTIVE_TEMP_FILES=()
BACKUP_DIR=""
PLAN_EVENTS_FILE=""
INSTALLED_COUNT=0
SKIPPED_COUNT=0
PLANNED_COUNT=0
PATH_BLOCKED=false
BLOCKED_COUNT=0
BLOCKED_PATHS=()

usage() {
    cat <<'EOF'
Usage: setup.sh [--dry-run] [--force] [--update] [--doctor] [--migration-plan PATH] [--interactive] [--with-advanced-docs] [--with-legacy-agents] [--without-skills] [--models LIST] [--preset NAME]

Installs the AI agent rules and Obsidian starter vault into the current directory.

  --dry-run  Show which files would be installed or skipped; make no changes.
  --force    Replace existing template-owned files. Without this flag, existing
             files are preserved. Symlinks are never overwritten.
  --update   Upgrade a project with a template-owned manifest. Existing managed
             files are backed up, then replaced by this template version.
  --doctor   Read-only readiness check for Bash/Python, installed runtime
             adapters, manifest ownership, managed tools, SDD skills, Markdown
             links, and Spec-Driven Development readiness.
  --migration-plan PATH  With --dry-run --update, write a Markdown (.md) or JSON
             report describing planned replacements, preserved/manual items, and
             backup/rollback guidance. Refuses to overwrite an existing file.
  --with-advanced-docs  Install API, backend, infrastructure, and user-manual
                        starter notes.
  --with-legacy-agents  Install .agents/AGENTS.md for tools that require it.
  --without-skills  Skip installing SDD slash-command skills (.claude/skills,
                    .agents/skills, .qwen/skills) and record skills_enabled: false
                    in template-manifest.json.
  --interactive  Show the model-selection menu even when stdin is not a TTY.
  --models LIST  Comma-separated runtime adapters: claude,antigravity,qwen,gemma,
                 or all. In an interactive terminal, omit this option to choose.
  --preset NAME  Set default feature preset (general, web-api, cli-tool, ai-agent,
                 or an existing docs/templates/presets/<name> directory).
EOF
}

run_doctor() {
    local doctor_status=0
    local runtime
    local command_name
    local tool_path
    local tool_state
    local validator_module_dir=""
    local validator_check_allowed=false

    echo "AI template doctor: $DEST_DIR"
    if [ -n "${BASH_VERSION:-}" ]; then
        echo "PASS Bash: $BASH_VERSION"
    else
        echo "FAIL Bash: setup.sh must be run by Bash. Remediation: run 'bash /path/to/setup.sh --doctor'." >&2
        doctor_status=1
    fi
    if command -v python3 >/dev/null 2>&1; then
        echo "PASS Python: $(python3 --version 2>&1)"
    else
        echo "FAIL Python: Python 3 is unavailable. Remediation: install Python 3 and rerun --doctor." >&2
        return 1
    fi
    if [ ! -f "$DEST_DIR/AGENTS.md" ] || [ -L "$DEST_DIR/AGENTS.md" ]; then
        echo "FAIL policy: a regular AGENTS.md is required. Remediation: restore the canonical policy with setup.sh --update before enabling an agent runtime." >&2
        doctor_status=1
    else
        echo "PASS policy: AGENTS.md is a regular canonical policy file"
    fi
    if [ "$DEST_DIR" = "$SRC_DIR" ]; then
        if [ ! -f "$SRC_DIR/template-manifest.json" ] || [ -L "$SRC_DIR/template-manifest.json" ]; then
            echo "FAIL manifest: a regular source template-manifest.json is required. Remediation: restore template-manifest.json from Git." >&2
            doctor_status=1
        elif ! ( source "$SRC_DIR/template-paths.sh" ) >/dev/null 2>&1; then
            echo "FAIL manifest: invalid source template-manifest.json. Remediation: inspect template-manifest.json and template-paths.sh." >&2
            doctor_status=1
        else
            local src_version
            src_version="$(python3 -B -c 'import json, sys; print(json.load(open(sys.argv[1])).get("version", "unknown"))' "$SRC_DIR/template-manifest.json")"
            echo "PASS manifest: template-owned (source template); version=$src_version"
        fi

        local static_adapter
        local adapters_ok=true
        for static_adapter in "CLAUDE.md" "GEMINI.md" "QWEN.md" "docs/templates/1. Agent System Prompt Template.md"; do
            if [ ! -f "$SRC_DIR/$static_adapter" ] || [ -L "$SRC_DIR/$static_adapter" ]; then
                echo "FAIL adapter: missing regular $static_adapter. Remediation: restore $static_adapter from Git." >&2
                doctor_status=1
                adapters_ok=false
            elif ! grep -Fq "AGENTS.md" "$SRC_DIR/$static_adapter"; then
                echo "FAIL adapter: $static_adapter does not delegate to AGENTS.md. Remediation: restore $static_adapter from Git." >&2
                doctor_status=1
                adapters_ok=false
            fi
        done
        if [ "$adapters_ok" = true ]; then
            echo "PASS adapters: static runtime adapters and system-prompt template delegate to AGENTS.md"
        fi

        local src_tool
        local src_tools_ok=true
        for src_tool in \
            "tests/validate-task-evidence.py" \
            "tests/docs_validation.py" \
            "tests/validate-project-docs.py" \
            "tests/new-feature.py" \
            "tests/export-tasks.py"; do
            if [ ! -f "$SRC_DIR/$src_tool" ] || [ -L "$SRC_DIR/$src_tool" ]; then
                echo "FAIL tools: missing or symlinked source tool $src_tool. Remediation: restore $src_tool from Git." >&2
                doctor_status=1
                src_tools_ok=false
            fi
        done
        if [ "$src_tools_ok" = true ]; then
            echo "PASS tools: source SDD and validation scripts verified in tests/"
            validator_module_dir="$SRC_DIR/tests"
            validator_check_allowed=true
        fi

        local skill_diag
        if skill_diag="$(python3 -B - "$SRC_DIR" <<'PY'
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
slugs = (
    "sdd-docs",
    "sdd-specify",
    "sdd-clarify",
    "sdd-plan",
    "sdd-tasks",
    "sdd-analyze",
    "sdd-implement",
)
skills_dir = root / "skills"
if skills_dir.is_symlink() or not skills_dir.is_dir():
    print("missing or symlinked skills/ directory")
    raise SystemExit(1)
for slug in slugs:
    sdir = skills_dir / slug
    smd = sdir / "SKILL.md"
    if sdir.is_symlink() or not sdir.is_dir() or smd.is_symlink() or not smd.is_file():
        print(f"missing or symlinked skills/{slug}/SKILL.md")
        raise SystemExit(1)
    text = smd.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.+)$", text, flags=re.S)
    if not m:
        print(f"skills/{slug}/SKILL.md is missing valid YAML frontmatter")
        raise SystemExit(1)
    fm_text, body = m.group(1), m.group(2)
    if not re.search(rf"^name:\s*['\"]?{re.escape(slug)}['\"]?\s*$", fm_text, flags=re.M) or not re.search(r"^description:\s*\S+", fm_text, flags=re.M):
        print(f"skills/{slug}/SKILL.md is missing name/description frontmatter")
        raise SystemExit(1)
    if "AGENTS.md" not in body:
        print(f"skills/{slug}/SKILL.md does not delegate to AGENTS.md")
        raise SystemExit(1)
PY
        )"; then
            echo "PASS skills: 7 canonical SDD skills verified"
        else
            echo "FAIL skills: $skill_diag. Remediation: restore canonical skills/sdd-*/SKILL.md from Git." >&2
            doctor_status=1
        fi
    else
        if [ ! -f "$DEST_DIR/template-manifest.json" ] || [ -L "$DEST_DIR/template-manifest.json" ]; then
            echo "FAIL manifest: a regular template-manifest.json is required. Remediation: run a normal setup, or restore the managed manifest before --update." >&2
            doctor_status=1
        else
            local manifest_output
            if ! manifest_output="$(python3 -B - "$DEST_DIR" <<'PY'
import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads((root / "template-manifest.json").read_text(encoding="utf-8"))
if manifest.get("template") != "ai-agent-obsidian-project-template":
    raise ValueError("manifest is not owned by ai-agent-obsidian-project-template")
def safe_path(path):
    return isinstance(path, str) and path and not path.startswith("/") and "\n" not in path and "\r" not in path and all(part not in {"", ".", ".."} for part in path.split("/"))
if not isinstance(manifest.get("managed_paths"), list) or not all(safe_path(path) for path in manifest["managed_paths"]):
    raise ValueError("manifest has unsafe managed_paths")
profiles = manifest.get("profiles")
if not isinstance(profiles, dict) or any(not isinstance(paths, list) or not all(safe_path(path) for path in paths) for paths in profiles.values()):
    raise ValueError("manifest has unsafe profile paths")
known = {"claude", "antigravity", "qwen", "gemma", "gemini"}
models = manifest.get("requested_models", manifest.get("selected_models"))
if not isinstance(models, list) or any(model not in known for model in models):
    raise ValueError("manifest has no valid selected runtime list")
managed = manifest.get("managed_adapter_models", [])
if not isinstance(managed, list) or any(model not in known for model in managed):
    raise ValueError("manifest has invalid managed_adapter_models")
managed_profiles = manifest.get("managed_profiles", ["core"])
if not isinstance(managed_profiles, list) or any(profile not in {"core", "--with-advanced-docs", "--with-legacy-agents"} for profile in managed_profiles):
    raise ValueError("manifest has invalid managed_profiles")
if "default_preset" in manifest and manifest["default_preset"] is not None:
    preset = manifest["default_preset"]
    if not isinstance(preset, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", preset):
        raise ValueError("manifest has invalid default_preset")
if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
    raise ValueError("manifest has invalid skills_enabled")
skills_enabled = manifest.get("skills_enabled", True)
print("PASS manifest: template-owned; version=" + str(manifest.get("version", "unknown")))
if "default_preset" in manifest and manifest["default_preset"] is not None:
    preset = manifest["default_preset"]
    if preset not in {"general", "web-api", "cli-tool", "ai-agent"}:
        cur = root
        preset_ok = True
        for part in ("docs", "templates", "presets", preset):
            cur = cur / part
            if cur.is_symlink() or not cur.is_dir():
                preset_ok = False
                break
        if preset_ok:
            print("PASS preset: custom default_preset '" + preset + "' verified")
        else:
            print("PRESET_FAIL|" + preset)
    else:
        print("PASS preset: built-in default_preset '" + preset + "' verified")
for model in models:
    print("RUNTIME|" + model + "|" + ("managed" if model in managed else "unmanaged"))
managed_set = set(manifest["managed_paths"])
for tool_rel in (
    "tools/validate-task-evidence.py",
    "tools/docs_validation.py",
    "tools/validate-docs.py",
    "tools/new-feature.py",
    "tools/export-tasks.py",
):
    print("TOOL|" + tool_rel + "|" + ("managed" if tool_rel in managed_set else "unmanaged"))
def valid_skill_file(rel: str) -> bool:
    cur = root
    parts = rel.split("/")
    for part in parts[:-1]:
        cur = cur / part
        if cur.is_symlink() or not cur.is_dir():
            return False
    target = cur / parts[-1]
    if target.is_symlink() or not target.is_file():
        return False
    try:
        text = target.read_text(encoding="utf-8", errors="replace").replace("\r\n", "\n")
    except OSError:
        return False
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.+)$", text, flags=re.S)
    if not m:
        return False
    fm_text, body = m.group(1), m.group(2)
    return bool(
        re.search(r"^name:\s*\S+", fm_text, flags=re.M)
        and re.search(r"^description:\s*\S+", fm_text, flags=re.M)
        and "AGENTS.md" in body
    )
skill_paths = [
    path for path in manifest["managed_paths"]
    if re.fullmatch(r"\.(claude|agents|qwen)/skills/[^/]+/SKILL\.md", path)
]
if not skills_enabled and not skill_paths:
    print("SKILLS_DISABLED")
else:
    for sp in skill_paths:
        print(("SKILL_OK|" if valid_skill_file(sp) else "SKILL_FAIL|") + sp)
    if not skill_paths:
        capable = [m for m in models if m in {"claude", "antigravity", "gemini", "qwen"}]
        if not capable:
            print("SKILLS_NONE_FOR_RUNTIME")
        else:
            print("SKILLS_UNMANAGED")
PY
)"; then
                echo "FAIL manifest: invalid template-owned manifest. Remediation: inspect template-manifest.json; do not run --update until it is repaired." >&2
                doctor_status=1
            else
                local tools_ok=true
                local skills_ok=true
                local managed_skill_count=0
                local skill_path
                while IFS= read -r line; do
                    case "$line" in
                        PRESET_FAIL\|*)
                            local bad_preset="${line#PRESET_FAIL|}"
                            echo "FAIL preset: custom default_preset '$bad_preset' is missing or symlinked at docs/templates/presets/$bad_preset. Remediation: create a regular directory at docs/templates/presets/$bad_preset or run setup.sh --update --preset general." >&2
                            doctor_status=1
                            ;;
                        RUNTIME\|*)
                            IFS='|' read -r _ runtime managed_state <<< "$line"
                            case "$runtime" in
                                claude) command_name="claude"; adapter="CLAUDE.md" ;;
                                antigravity|gemini) command_name="agy"; adapter="GEMINI.md" ;;
                                qwen) command_name="qwen"; adapter="QWEN.md" ;;
                                gemma) command_name=""; adapter="" ;;
                                *) echo "FAIL runtime: unknown selected runtime '$runtime'. Remediation: repair the manifest." >&2; doctor_status=1; continue ;;
                            esac
                            if [ "$runtime" = gemma ]; then
                                if [ ! -f "$DEST_DIR/docs/templates/1. Agent System Prompt Template.md" ] || [ -L "$DEST_DIR/docs/templates/1. Agent System Prompt Template.md" ]; then
                                    echo "FAIL runtime gemma: the required system-prompt template is missing. Remediation: restore docs/templates/1. Agent System Prompt Template.md with setup.sh --update." >&2
                                else
                                    echo "FAIL runtime gemma: host-level system-prompt injection cannot be verified from this repository. Remediation: verify the host injects docs/templates/1. Agent System Prompt Template.md before enabling write tools." >&2
                                fi
                                doctor_status=1
                                continue
                            fi
                            if [ "$managed_state" != managed ]; then
                                echo "WARN runtime $runtime: adapter is user-owned or not managed; preserving it while checking its minimum contract."
                            fi
                            if [ ! -f "$DEST_DIR/$adapter" ] || [ -L "$DEST_DIR/$adapter" ]; then
                                echo "FAIL runtime $runtime: missing regular $adapter. Remediation: restore the managed adapter with setup.sh --update or add a regular user-owned adapter that delegates to AGENTS.md." >&2
                                doctor_status=1
                            elif ! grep -Fq "AGENTS.md" "$DEST_DIR/$adapter"; then
                                echo "FAIL runtime $runtime: $adapter does not delegate to AGENTS.md. Remediation: restore the managed adapter or review the custom adapter." >&2
                                doctor_status=1
                            elif ! command -v "$command_name" >/dev/null 2>&1; then
                                echo "FAIL runtime $runtime: command '$command_name' is unavailable. Remediation: install/enable that runtime or remove it from the selected runtime configuration." >&2
                                doctor_status=1
                            else
                                echo "PASS runtime $runtime: $adapter and '$command_name' are available"
                            fi
                            ;;
                        TOOL\|*)
                            IFS='|' read -r _ tool_path tool_state <<< "$line"
                            if [ "$tool_state" = managed ]; then
                                if [ ! -f "$DEST_DIR/$tool_path" ] || [ -L "$DEST_DIR/$tool_path" ]; then
                                    echo "FAIL tools: missing or symlinked managed tool $tool_path. Remediation: restore managed tools with setup.sh --update." >&2
                                    doctor_status=1
                                    tools_ok=false
                                fi
                            else
                                echo "WARN tools: $tool_path is user-owned or unmanaged; preserving without managed integrity check."
                            fi
                            ;;
                        SKILLS_DISABLED)
                            echo "INFO skills: disabled via --without-skills"
                            ;;
                        SKILLS_NONE_FOR_RUNTIME)
                            echo "INFO skills: no repository skill directories apply to selected runtime(s)"
                            ;;
                        SKILLS_UNMANAGED)
                            echo "WARN skills: no managed SDD skills recorded in manifest; run setup.sh --update to install /sdd-* skills or --without-skills to opt out."
                            ;;
                        SKILL_OK\|*)
                            managed_skill_count=$((managed_skill_count + 1))
                            ;;
                        SKILL_FAIL\|*)
                            skill_path="${line#SKILL_FAIL|}"
                            managed_skill_count=$((managed_skill_count + 1))
                            echo "FAIL skills: missing, symlinked, or corrupted managed skill $skill_path. Remediation: restore managed skills with setup.sh --update." >&2
                            doctor_status=1
                            skills_ok=false
                            ;;
                        *) echo "$line" ;;
                    esac
                done <<< "$manifest_output"
                if [ "$tools_ok" = true ]; then
                    echo "PASS tools: managed downstream tools verified"
                fi
                if [ "$managed_skill_count" -gt 0 ] && [ "$skills_ok" = true ]; then
                    echo "PASS skills: $managed_skill_count managed downstream SDD skill(s) verified"
                fi
                if [ -f "$DEST_DIR/tools/docs_validation.py" ] && [ ! -L "$DEST_DIR/tools/docs_validation.py" ]; then
                    if grep -Fq "TOOL|tools/docs_validation.py|managed" <<< "$manifest_output"; then
                        validator_module_dir="$DEST_DIR/tools"
                        validator_check_allowed=true
                    else
                        echo "WARN spec readiness: tools/docs_validation.py is user-owned; skipping managed semantic spec checks."
                    fi
                fi
            fi
        fi
    fi
    if python3 -B - "$DEST_DIR" <<'PY'
import re
import sys
from pathlib import Path
from urllib.parse import unquote

def strip_code(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out = []
    in_fence = False
    fence_char = ""
    fence_len = 0
    for line in lines:
        m = re.match(r"^[ \t]*(`{3,}|~{3,})([^\n]*)$", line)
        if not in_fence:
            if m:
                marker, info = m.group(1), m.group(2)
                if not (marker[0] == "`" and "`" in info):
                    in_fence = True
                    fence_char = marker[0]
                    fence_len = len(marker)
                    out.append("\n")
                    continue
            out.append(line)
        else:
            close_m = re.match(r"^[ \t]*(" + re.escape(fence_char) + r"{" + str(fence_len) + r",})[ \t]*\r?\n?$", line)
            if close_m:
                in_fence = False
            out.append("\n")
    joined = "".join(out)
    return re.sub(r"(`+)([^\n]*?)\1", "", joined)

root = Path(sys.argv[1]).resolve()
missing = []
for note in root.rglob("*.md"):
    if ".git" in note.parts:
        continue
    cleaned = strip_code(note.read_text(encoding="utf-8", errors="replace"))
    for target in re.findall(r"(?<!!)(?:!?)\[[^]]*\]\(([^)]+)\)", cleaned):
        target = target.split("#", 1)[0].strip().strip("<>")
        if not target or "://" in target or target.startswith(("mailto:", "file:")):
            continue
        candidate = (note.parent / unquote(target)).resolve()
        if not candidate.is_relative_to(root) or not candidate.exists():
            missing.append(f"{note.relative_to(root)} -> {target}")
if missing:
    print("FAIL docs links: " + "; ".join(missing[:10]), file=sys.stderr)
    raise SystemExit(1)
print("PASS docs links: local Markdown targets resolve")
PY
    then
        :
    else
        echo "Remediation: repair the reported Markdown link(s), or rerun setup.sh --update for template-managed documentation." >&2
        doctor_status=1
    fi
    if [ "$validator_check_allowed" = true ] && [ -d "$DEST_DIR/docs/current" ]; then
        if python3 -B - "$DEST_DIR" "$validator_module_dir" <<'PY'
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root = Path(sys.argv[1]).resolve()
sys.path.insert(0, sys.argv[2])

from docs_validation import (
    validate_clarify_gate,
    validate_feature_specs,
    validate_links,
    validate_mermaid,
)

docs_root = root / "docs"
current_root = docs_root / "current"
files = sorted(current_root.rglob("*.md"))
if files:
    validate_links(root, docs_root, files)
    validate_mermaid(root, files)
    validate_clarify_gate(root, files)
    warnings = validate_feature_specs(root, current_root / "05 - Product Features", require_tasks=False)
    for warning in warnings:
        print(f"WARN spec readiness: {warning}")
print("PASS spec readiness: Clarify gate, Mermaid structure, and cross-spec traceability verified")
PY
        then
            :
        else
            echo "FAIL spec readiness: semantic documentation validation failed. Remediation: resolve [NEEDS CLARIFICATION] markers, open checkboxes, approval frontmatter, or AC traceability mismatches, then rerun 'python3 tools/validate-docs.py'." >&2
            doctor_status=1
        fi
    fi
    if [ "$doctor_status" -eq 0 ]; then
        echo "Doctor result: READY"
    else
        echo "Doctor result: NOT READY" >&2
    fi
    return "$doctor_status"
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
        --doctor) DOCTOR=true ;;
        --migration-plan)
            shift
            [ "$#" -gt 0 ] || { echo "Error: --migration-plan requires a relative output path." >&2; exit 1; }
            MIGRATION_PLAN="$1"
            ;;
        --migration-plan=*)
            MIGRATION_PLAN="${1#--migration-plan=}"
            [ -n "$MIGRATION_PLAN" ] || { echo "Error: --migration-plan requires a relative output path." >&2; exit 1; }
            ;;
        --with-advanced-docs) WITH_ADVANCED_DOCS=true ;;
        --with-legacy-agents) WITH_LEGACY_AGENTS=true ;;
        --without-skills)
            WITH_SKILLS=false
            WITHOUT_SKILLS_PROVIDED=true
            ;;
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
        --preset)
            [ "$PRESET_OPTION_PROVIDED" = false ] || { echo "Error: --preset can only be provided once." >&2; exit 1; }
            shift
            [ "$#" -gt 0 ] && [ -n "$1" ] || { echo "Error: --preset requires a preset name." >&2; exit 1; }
            PRESET_OPTION_PROVIDED=true
            PRESET_NAME="$1"
            ;;
        --preset=*)
            [ "$PRESET_OPTION_PROVIDED" = false ] || { echo "Error: --preset can only be provided once." >&2; exit 1; }
            PRESET_OPTION_PROVIDED=true
            PRESET_NAME="${1#--preset=}"
            [ -n "$PRESET_NAME" ] || { echo "Error: --preset requires a preset name." >&2; exit 1; }
            ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: Unknown option: $1" >&2; usage >&2; exit 1 ;;
    esac
    shift
done

if [ "$DOCTOR" = true ] && { [ "$UPDATE" = true ] || [ "$DRY_RUN" = true ] || [ -n "$MIGRATION_PLAN" ] || [ "$PRESET_OPTION_PROVIDED" = true ] || [ "$WITHOUT_SKILLS_PROVIDED" = true ]; }; then
    echo "Error: --doctor cannot be combined with --update, --dry-run, --migration-plan, --preset, or --without-skills." >&2
    exit 1
fi

# Set the source directory (where this script is located)
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"

# Target directory is the current directory where the script is executed
DEST_DIR="$(pwd -P)"

if [[ "$SRC_DIR" == "$DEST_DIR" || "$DEST_DIR" == "$SRC_DIR"/* ]]; then
    if [ "$DOCTOR" = true ] && [ "$DEST_DIR" = "$SRC_DIR" ]; then
        run_doctor
        exit $?
    fi
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

if [ "$DOCTOR" = true ]; then
    run_doctor
    exit $?
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
    local prior_skills

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
if "default_preset" in manifest and manifest["default_preset"] is not None:
    import re
    if not isinstance(manifest["default_preset"], str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["default_preset"]):
        raise ValueError("manifest has invalid default_preset")
if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
    raise ValueError("manifest has invalid skills_enabled")
skills_enabled = manifest.get("skills_enabled", True)
print("|".join([",".join(models or known), str("--with-advanced-docs" in managed_profiles).lower(), str("--with-legacy-agents" in managed_profiles).lower(), ",".join(managed), ",".join(managed_profiles), str(skills_enabled).lower()]))
PY
    )"; then
        echo "Error: --update requires a valid template-owned template-manifest.json." >&2
        exit 1
    fi
    IFS='|' read -r inferred_models prior_advanced prior_legacy UPDATE_MANAGED_ADAPTER_MODELS MANAGED_PROFILES prior_skills <<< "$update_metadata"
    SELECTED_MODELS="$inferred_models"
    [ "$prior_advanced" = true ] && WITH_ADVANCED_DOCS=true
    [ "$prior_legacy" = true ] && WITH_LEGACY_AGENTS=true
    if [ "$WITHOUT_SKILLS_PROVIDED" = false ]; then
        WITH_SKILLS="$prior_skills"
    fi
    validate_models
}

validate_preset_option() {
    local current_path
    local part

    [ "$PRESET_OPTION_PROVIDED" = true ] || return 0
    if [[ ! "$PRESET_NAME" =~ ^[a-z0-9]+(-[a-z0-9]+)*$ ]]; then
        echo "Error: Invalid --preset '$PRESET_NAME'. Expected lowercase kebab-case slug." >&2
        exit 1
    fi
    case "$PRESET_NAME" in
        general|web-api|cli-tool|ai-agent) return 0 ;;
    esac
    current_path="$DEST_DIR"
    for part in "docs" "templates" "presets" "$PRESET_NAME"; do
        current_path="$current_path/$part"
        if [ -L "$current_path" ] || [ ! -d "$current_path" ]; then
            echo "Error: Custom preset '$PRESET_NAME' requires an existing non-symlink directory at docs/templates/presets/$PRESET_NAME." >&2
            exit 1
        fi
    done
}

if [ "$UPDATE" = true ]; then
    select_update_models
else
    select_models_interactively
fi
validate_preset_option

cleanup_temporary_files() {
    local temporary_file

    if [ -n "$GENERATED_MANIFEST" ] && [ -e "$GENERATED_MANIFEST" ]; then
        rm -f "$GENERATED_MANIFEST"
    fi
    for temporary_file in "${ACTIVE_TEMP_FILES[@]-}"; do
        [ -e "$temporary_file" ] && rm -f "$temporary_file"
    done
    if [ -n "$PLAN_EVENTS_FILE" ] && [ -e "$PLAN_EVENTS_FILE" ]; then
        rm -f "$PLAN_EVENTS_FILE"
    fi
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
    python3 - "$PLAN_EVENTS_FILE" "$DEST_DIR/$MIGRATION_PLAN" "$DEST_DIR" <<'PY'
import json
import sys
from collections import defaultdict
from pathlib import Path

events_path, output_path, destination = map(Path, sys.argv[1:])
destination = destination.resolve()
if not output_path.resolve().is_relative_to(destination):
    raise ValueError("migration plan output escapes the destination root")
relative_parent = output_path.parent.relative_to(destination)
current = destination
for part in relative_parent.parts:
    current /= part
    if current.is_symlink():
        raise ValueError("migration plan parent must not be a symlink")
groups = defaultdict(list)
for line in events_path.read_text(encoding="utf-8").splitlines():
    kind, path, detail = line.split("\t", 2)
    groups[kind].append({"path": path, "detail": detail})
payload = {
    "schema_version": 1,
    "mode": "dry-run-update",
    "destination": str(destination),
    "backup_directory_pattern": str(destination / ".ai-template-backup.XXXXXX"),
    "rollback": "After a real update, copy the desired file from the reported backup directory; see RECOVERY.md in that directory.",
    "will_replace": groups["replace"],
    "will_install": groups["install"],
    "will_preserve": groups["preserve"],
    "manual_action": groups["manual"],
    "blocked": groups["blocked"],
    "migrations": groups["migrate"],
}
output_path.parent.mkdir(parents=True, exist_ok=True)
if output_path.suffix.lower() == ".json":
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
else:
    lines = [
        "# AI Template Migration Plan", "", "- Mode: `--dry-run --update`", f"- Destination: `{destination}`",
        f"- Planned backup directory: `{payload['backup_directory_pattern']}`", "- Rollback: after a real update, use `RECOVERY.md` in the reported backup directory to restore individual files.", "",
    ]
    for title, key in [("Will replace", "will_replace"), ("Will install", "will_install"), ("Will preserve", "will_preserve"), ("Manual action", "manual_action"), ("Blocked", "blocked"), ("Migrations", "migrations")]:
        lines.extend([f"## {title}", ""])
        entries = payload[key]
        lines.extend([f"- `{entry['path']}` — {entry['detail']}" for entry in entries] or ["- None."])
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
PY
    echo "Migration plan: $MIGRATION_PLAN"
}

if [ -n "$MIGRATION_PLAN" ]; then
    PLAN_EVENTS_FILE="$(mktemp "${TMPDIR:-/tmp}/ai-template-plan.XXXXXX")"
fi

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
if "default_preset" in manifest and manifest["default_preset"] is not None:
    import re
    if not isinstance(manifest["default_preset"], str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["default_preset"]):
        raise ValueError("existing manifest has invalid default_preset")
if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
    raise ValueError("existing manifest has invalid skills_enabled")

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
            plan_record "replace" "$relative_path" "managed file will be backed up and replaced"
        else
            echo "INSTALL: $relative_path"
            plan_record "install" "$relative_path" "new template-managed file"
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

collect_managed_skill_paths() {
    local mapping
    local model
    local prefix
    local slug
    local rel
    local skipped_rel
    local is_skipped_user

    MANAGED_SKILL_PATHS=""
    [ "$WITH_SKILLS" = true ] || return 0

    for mapping in "claude:.claude" "antigravity:.agents" "qwen:.qwen"; do
        model="${mapping%%:*}"
        prefix="${mapping#*:}"
        [[ ",$REQUESTED_MODELS," == *",$model,"* ]] || continue
        for slug in "${SDD_SKILL_SLUGS[@]}"; do
            rel="$prefix/skills/$slug/SKILL.md"
            is_skipped_user=false
            if [ "${#SKIPPED_USER_SKILL_PATHS[@]}" -gt 0 ]; then
                for skipped_rel in "${SKIPPED_USER_SKILL_PATHS[@]}"; do
                    if [ "$skipped_rel" = "$rel" ]; then
                        is_skipped_user=true
                        break
                    fi
                done
            fi
            [ "$is_skipped_user" = false ] || continue
            if [ -f "$DEST_DIR/$rel" ] && [ ! -L "$DEST_DIR/$rel" ] && cmp -s "$SRC_DIR/skills/$slug/SKILL.md" "$DEST_DIR/$rel"; then
                MANAGED_SKILL_PATHS+="${MANAGED_SKILL_PATHS:+|}$rel"
            fi
        done
    done
}

copy_selected_manifest() {
    if [ "$MANIFEST_UPDATE_ALLOWED" = false ]; then
        echo "SKIP (unmanaged manifest): template-manifest.json"
        plan_record "manual" "template-manifest.json" "unmanaged manifest must be reviewed manually"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
        return
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
        return
    fi

    collect_managed_adapter_models
    collect_managed_skill_paths
    GENERATED_MANIFEST="$(mktemp "$DEST_DIR/.ai-template-manifest.XXXXXX")"
    if ! cp -p "$SRC_DIR/template-manifest.json" "$GENERATED_MANIFEST"; then
        return 1
    fi
    if ! python3 - "$SRC_DIR/template-manifest.json" "$MANIFEST_BASE" "$GENERATED_MANIFEST" "$REQUESTED_MODELS" "$MANAGED_ADAPTER_MODELS" "$WITH_ADVANCED_DOCS" "$WITH_LEGACY_AGENTS" "$VALIDATOR_BUNDLE_MANAGED" "$NEW_FEATURE_MANAGED" "$EXPORT_TASKS_MANAGED" "$PRESET_OPTION_PROVIDED" "$PRESET_NAME" "$WITH_SKILLS" "$MANAGED_SKILL_PATHS" <<'PY'
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
new_feature_managed = sys.argv[9] == "true"
export_tasks_managed = sys.argv[10] == "true"
preset_provided = sys.argv[11] == "true"
preset_name = sys.argv[12]
with_skills = sys.argv[13] == "true"
managed_skill_list = [path for path in sys.argv[14].split("|") if path]
managed_skill_set = set(managed_skill_list)
adapter_models = {
    "CLAUDE.md": "claude",
    "GEMINI.md": "antigravity",
    "QWEN.md": "qwen",
}
all_skill_paths = {
    f"{prefix}/skills/{slug}/SKILL.md"
    for prefix in (".claude", ".agents", ".qwen")
    for slug in (
        "sdd-docs",
        "sdd-specify",
        "sdd-clarify",
        "sdd-plan",
        "sdd-tasks",
        "sdd-analyze",
        "sdd-implement",
    )
}

data = json.loads(template_source.read_text())
existing = json.loads(existing_source.read_text())
installer_keys = {"template", "version", "skills_enabled", "managed_paths", "profiles", "requested_models", "selected_models", "managed_adapter_models"}
for key, value in existing.items():
    if key not in installer_keys:
        data[key] = value
data["skills_enabled"] = with_skills
if preset_provided:
    data["default_preset"] = preset_name

existing_profiles = existing.get("profiles", {})
for name, profile in existing_profiles.items():
    if name not in {"core", "--with-advanced-docs", "--with-legacy-agents"}:
        data["profiles"][name] = profile
for path in existing_profiles.get("core", []):
    if path not in data["profiles"]["core"] and path not in adapter_models and path not in all_skill_paths:
        data["profiles"]["core"].append(path)
for path in existing.get("managed_paths", []):
    if path not in data["managed_paths"] and path not in adapter_models and path not in all_skill_paths:
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
def keep_core_path(path: str) -> bool:
    return (path not in adapter_models or adapter_models[path] in managed) and (
        path not in all_skill_paths or (with_skills and path in managed_skill_set)
    )
data["managed_paths"] = [path for path in data["managed_paths"] if keep_core_path(path)]
data["profiles"]["core"] = [path for path in data["profiles"]["core"] if keep_core_path(path)]
for adapter, model in adapter_models.items():
    if model in managed:
        if adapter not in data["managed_paths"]:
            data["managed_paths"].append(adapter)
        if adapter not in data["profiles"]["core"]:
            data["profiles"]["core"].append(adapter)
if with_skills:
    for skill_path in managed_skill_list:
        if skill_path not in data["managed_paths"]:
            data["managed_paths"].append(skill_path)
        if skill_path not in data["profiles"]["core"]:
            data["profiles"]["core"].append(skill_path)
validator_paths = {"tools/docs_validation.py", "tools/validate-docs.py"}
if not validator_bundle_managed:
    data["managed_paths"] = [path for path in data["managed_paths"] if path not in validator_paths]
    data["profiles"]["core"] = [path for path in data["profiles"]["core"] if path not in validator_paths]
if not new_feature_managed:
    data["managed_paths"] = [path for path in data["managed_paths"] if path != "tools/new-feature.py"]
    data["profiles"]["core"] = [path for path in data["profiles"]["core"] if path != "tools/new-feature.py"]
if not export_tasks_managed:
    data["managed_paths"] = [path for path in data["managed_paths"] if path != "tools/export-tasks.py"]
    data["profiles"]["core"] = [path for path in data["profiles"]["core"] if path != "tools/export-tasks.py"]
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
    plan_record "blocked" "$relative_path" "$reason; resolve this path before a real update"
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
            plan_record "preserve" "$old_relative_path" "legacy template is a symlink; resolve manually"
            continue
        fi
        if [ ! -f "$old_path" ]; then
            echo "SKIP (non-file legacy template): $old_relative_path"
            plan_record "manual" "$old_relative_path" "legacy template is not a regular file"
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

prepare_sdd_tools() {
    local ownership_pair

    NEW_FEATURE_MANAGED=true
    EXPORT_TASKS_MANAGED=true
    [ "$FORCE" = true ] && return 0

    ownership_pair="$(python3 -B - "$DEST_DIR" "$UPDATE" <<'PY'
import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
is_update = sys.argv[2] == "true"
manifest_path = dest / "template-manifest.json"
template_owned = False
managed: set[str] = set()
core: set[str] = set()
if manifest_path.is_file() and not manifest_path.is_symlink():
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(manifest, dict) and manifest.get("template") == "ai-agent-obsidian-project-template":
            template_owned = True
            managed = set(manifest.get("managed_paths", []))
            core = set(manifest.get("profiles", {}).get("core", []))
    except (OSError, ValueError, TypeError):
        template_owned = False

results = []
for rel in ("tools/new-feature.py", "tools/export-tasks.py"):
    target = dest / rel
    exists_or_link = target.exists() or target.is_symlink()
    if template_owned and rel in managed and rel in core:
        if is_update or not target.is_symlink():
            results.append("true")
        else:
            results.append("false")
    elif not exists_or_link:
        results.append("true")
    else:
        results.append("false")
print("|".join(results))
PY
    )"
    IFS='|' read -r NEW_FEATURE_MANAGED EXPORT_TASKS_MANAGED <<< "$ownership_pair"
}

prepare_sdd_skills() {
    local status_lines
    local line
    local action
    local rel

    SCHEDULED_SKILL_PATHS=()
    SKIPPED_USER_SKILL_PATHS=()
    PRESERVED_OPTOUT_SKILL_PATHS=()

    status_lines="$(python3 -B - "$DEST_DIR" "$SELECTED_MODELS" "$WITH_SKILLS" "$FORCE" "$UPDATE" <<'PY'
import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
selected = [m for m in sys.argv[2].split(",") if m]
with_skills = sys.argv[3] == "true"
force = sys.argv[4] == "true"
is_update = sys.argv[5] == "true"

runtime_prefixes = {
    "claude": ".claude",
    "antigravity": ".agents",
    "qwen": ".qwen",
}
slugs = (
    "sdd-docs",
    "sdd-specify",
    "sdd-clarify",
    "sdd-plan",
    "sdd-tasks",
    "sdd-analyze",
    "sdd-implement",
)

prior_managed: set[str] = set()
prior_core: set[str] = set()
manifest_path = dest / "template-manifest.json"
if manifest_path.is_file() and not manifest_path.is_symlink():
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if isinstance(manifest, dict) and manifest.get("template") == "ai-agent-obsidian-project-template":
            prior_managed = set(manifest.get("managed_paths", []))
            prior_core = set(manifest.get("profiles", {}).get("core", []))
    except (OSError, ValueError, TypeError):
        pass

for model in ("claude", "antigravity", "qwen"):
    if model not in selected:
        continue
    prefix = runtime_prefixes[model]
    for slug in slugs:
        rel = f"{prefix}/skills/{slug}/SKILL.md"
        target = dest / rel
        exists_or_link = target.exists() or target.is_symlink()
        if not with_skills:
            if is_update and exists_or_link:
                print(f"OPTOUT|{rel}")
            continue
        if force or not is_update or not exists_or_link or (rel in prior_managed and rel in prior_core):
            print(f"SCHEDULE|{rel}")
        else:
            print(f"USER_OWNED|{rel}")
PY
    )"

    while IFS= read -r line; do
        [ -n "$line" ] || continue
        IFS='|' read -r action rel <<< "$line"
        case "$action" in
            SCHEDULE) SCHEDULED_SKILL_PATHS+=("$rel") ;;
            USER_OWNED) SKIPPED_USER_SKILL_PATHS+=("$rel") ;;
            OPTOUT) PRESERVED_OPTOUT_SKILL_PATHS+=("$rel") ;;
        esac
    done <<< "$status_lines"
}

preflight_destinations() {
    local source_file
    local relative_path
    local failed=false

    prepare_manifest_models || failed=true
    prepare_validator_bundle
    prepare_sdd_tools
    prepare_sdd_skills

    for relative_path in "AGENTS.md" "template-manifest.json" "tools/validate-task-evidence.py" "task-evidence/.gitkeep"; do
        check_destination_path "$relative_path" || failed=true
    done
    if [ "$VALIDATOR_BUNDLE_MANAGED" = true ]; then
        for relative_path in "tools/docs_validation.py" "tools/validate-docs.py"; do
            check_destination_path "$relative_path" || failed=true
        done
    fi
    if [ "$NEW_FEATURE_MANAGED" = true ]; then
        check_destination_path "tools/new-feature.py" || failed=true
    fi
    if [ "$EXPORT_TASKS_MANAGED" = true ]; then
        check_destination_path "tools/export-tasks.py" || failed=true
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
    if [ "${#SCHEDULED_SKILL_PATHS[@]}" -gt 0 ]; then
        for relative_path in "${SCHEDULED_SKILL_PATHS[@]}"; do
            check_destination_path "$relative_path" || failed=true
        done
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
    if [ -n "$MIGRATION_PLAN" ]; then
        echo "Dry run only — no template-managed files will be changed; the requested migration plan will be written: $MIGRATION_PLAN"
    else
        echo "Dry run only — no files will be changed."
    fi
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
    plan_record "manual" "tools/docs_validation.py" "user-owned validator bundle will be preserved"
    plan_record "manual" "tools/validate-docs.py" "user-owned validator bundle will be preserved"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 2))
fi
if [ "$NEW_FEATURE_MANAGED" = true ]; then
    copy_file "$SRC_DIR/tests/new-feature.py" "tools/new-feature.py"
else
    echo "SKIP (user-owned tool): tools/new-feature.py"
    plan_record "manual" "tools/new-feature.py" "user-owned SDD tool will be preserved"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
fi
if [ "$EXPORT_TASKS_MANAGED" = true ]; then
    copy_file "$SRC_DIR/tests/export-tasks.py" "tools/export-tasks.py"
else
    echo "SKIP (user-owned tool): tools/export-tasks.py"
    plan_record "manual" "tools/export-tasks.py" "user-owned SDD tool will be preserved"
    SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
fi

if [ "$WITH_LEGACY_AGENTS" = true ]; then
    for relative_path in "${OPTIONAL_LEGACY_PATHS[@]}"; do
        copy_file "$SRC_DIR/AGENTS.md" "$relative_path"
    done
fi

if [ "${#SCHEDULED_SKILL_PATHS[@]}" -gt 0 ]; then
    for relative_path in "${SCHEDULED_SKILL_PATHS[@]}"; do
        skill_slug="${relative_path#*/skills/}"
        skill_slug="${skill_slug%/SKILL.md}"
        copy_file "$SRC_DIR/skills/$skill_slug/SKILL.md" "$relative_path"
    done
fi
if [ "${#SKIPPED_USER_SKILL_PATHS[@]}" -gt 0 ]; then
    for relative_path in "${SKIPPED_USER_SKILL_PATHS[@]}"; do
        echo "SKIP (user-owned skill): $relative_path"
        plan_record "manual" "$relative_path" "user-owned skill will be preserved"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    done
fi
if [ "${#PRESERVED_OPTOUT_SKILL_PATHS[@]}" -gt 0 ]; then
    for relative_path in "${PRESERVED_OPTOUT_SKILL_PATHS[@]}"; do
        echo "SKIP (skills disabled): $relative_path"
        plan_record "preserve" "$relative_path" "existing skill file preserved on disk (--without-skills)"
        SKIPPED_COUNT=$((SKIPPED_COUNT + 1))
    done
fi

if [ "$UPDATE" = true ]; then
    for mapping in "claude:CLAUDE.md" "antigravity:GEMINI.md" "qwen:QWEN.md"; do
        model="${mapping%%:*}"
        adapter="${mapping#*:}"
        if model_selected "$model" && ! adapter_selected_for_copy "$model"; then
            plan_record "preserve" "$adapter" "user-owned or unmanaged runtime adapter"
        fi
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

write_migration_plan

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
next_step_num=3
if [ "$WITH_SKILLS" = true ] && { model_selected claude || model_selected antigravity || model_selected qwen; }; then
    echo "$next_step_num. In Claude Code, Antigravity CLI, or Qwen Code chat, type /sdd-docs to initialize project docs or /sdd-specify <feature-slug> to start a feature."
    next_step_num=$((next_step_num + 1))
fi
if model_selected gemma; then
    echo "$next_step_num. Gemma/custom API selected: no repository filename is auto-loaded. Configure the host to inject docs/templates/1. Agent System Prompt Template.md before enabling write tools."
fi
echo "----------------------------------------"
