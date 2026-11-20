#!/bin/bash

set -euo pipefail
exec < /dev/null

TEMPLATE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
source "$TEMPLATE_DIR/template-paths.sh"
TEST_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ai-template-test.XXXXXX")"

cleanup() {
    chmod -R u+w "$TEST_DIR" 2>/dev/null || true
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

file_mode() {
    local file="$1"

    case "$(uname -s)" in
        Darwin) stat -f '%Lp' "$file" ;;
        *) stat -c '%a' "$file" ;;
    esac
}

core_doc_count=0
while IFS= read -r source_file; do
    relative_path="${source_file#"$TEMPLATE_DIR/"}"
    is_optional=false
    for optional_doc in "${OPTIONAL_ADVANCED_DOCS[@]}"; do
        [ "$relative_path" = "$optional_doc" ] && is_optional=true
    done
    [ "$is_optional" = true ] || core_doc_count=$((core_doc_count + 1))
done < <(find "$TEMPLATE_DIR/docs" -path "$TEMPLATE_DIR/docs/internal" -prune -o -type f ! -name '.DS_Store' -print)
expected_file_count=$((44 + core_doc_count))
no_skills_expected_count=$((17 + core_doc_count))

e2e_core_and_migplan() {
    # 1. Default install count (44 + core_doc_count), .gitignore bootstrap, preservation, and --force parity
    local target="$TEST_DIR/target"
    mkdir -p "$target"

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
    for gi_entry in ".ai-template-backup.*/" "plans/" ".DS_Store" "__pycache__/"; do
        assert_file_contains "$target/.gitignore" "$gi_entry"
    done
    [ -f "$target/tools/_sdd_core.py" ] || fail "default install did not copy tools/_sdd_core.py"
    [ -f "$target/tools/docs_validation.py" ] || fail "default install did not copy tools/docs_validation.py"
    [ -f "$target/tools/validate-docs.py" ] || fail "default install did not copy tools/validate-docs.py"
    [ -f "$target/tools/stamp-spec.py" ] || fail "default install did not copy tools/stamp-spec.py"
    [ -f "$target/tools/record-evidence.py" ] || fail "default install did not copy tools/record-evidence.py"
    [ -d "$target/task-evidence" ] || fail "default install did not create task-evidence/"
    [ ! -e "$target/docs/internal" ] || fail "default install copied source-only internal docs"
    [ ! -e "$target/.agents/AGENTS.md" ] || fail "default install copied optional nested AGENTS.md"
    python3 -B "$target/tools/validate-docs.py" >/dev/null || fail "downstream docs validator failed after default install"
    python3 -B "$target/tools/validate-task-evidence.py" >/dev/null || fail "downstream task-evidence validator failed after default install"

    (
        cd "$target"
        bash "$TEMPLATE_DIR/setup.sh" --force
    ) > "$TEST_DIR/force-install.txt"
    assert_file_contains "$target/AGENTS.md" "AI Agent Workspace Rules"
    [ "$(file_mode "$target/AGENTS.md")" = "$(file_mode "$TEMPLATE_DIR/AGENTS.md")" ] || fail "installer changed AGENTS.md mode"
    [ "$(file_mode "$target/docs/current/Vault Index MOC.md")" = "$(file_mode "$TEMPLATE_DIR/docs/current/Vault Index MOC.md")" ] || fail "installer changed docs mode"

    python3 -B - "$TEMPLATE_DIR" "$target" <<'PY'
import json
import sys
from pathlib import Path

template_root = Path(sys.argv[1])
target_root = Path(sys.argv[2])
profile = json.loads((template_root / "template-manifest.json").read_text(encoding="utf-8"))["profiles"]["core"]
source_overrides = {
    ".cursor/rules/agents.mdc": "adapters/cursor-agents.mdc",
    ".github/copilot-instructions.md": "adapters/copilot-instructions.md",
}
for prefix in (".claude", ".agents", ".qwen"):
    for slug in ("sdd-docs", "sdd-specify", "sdd-clarify", "sdd-plan", "sdd-tasks", "sdd-analyze", "sdd-implement", "sdd-fix", "sdd-review"):
        source_overrides[f"{prefix}/skills/{slug}/SKILL.md"] = f"skills/{slug}/SKILL.md"
expected: set[str] = set()
for relative in profile:
    source = template_root / source_overrides.get(relative, relative)
    if source.is_file():
        expected.add(relative)
    elif source.is_dir():
        expected.update(path.relative_to(template_root).as_posix() for path in source.rglob("*") if path.is_file())
    else:
        raise SystemExit(f"FAIL: manifest core path is missing from template: {relative}")
expected.add(".gitignore")
installed = {path.relative_to(target_root).as_posix() for path in target_root.rglob("*") if path.is_file()}
if expected != installed:
    raise SystemExit(f"FAIL: manifest core mismatch; missing={sorted(expected - installed)}, unexpected={sorted(installed - expected)}")
PY

    # 3. --migration-plan my..plan.json + $'bad\nplan.json' rejection
    if (
        cd "$target"
        bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan $'bad\nplan.json'
    ) > "$TEST_DIR/bad-migplan.txt" 2>&1; then
        fail "--migration-plan accepted newline-containing filename"
    fi
    assert_file_contains "$TEST_DIR/bad-migplan.txt" "safe relative output path"
    (
        cd "$target"
        bash "$TEMPLATE_DIR/setup.sh" --dry-run --update --migration-plan my..plan.json >/dev/null
    )
    python3 -B -m json.tool "$target/my..plan.json" >/dev/null || fail "my..plan.json invalid JSON"
    rm -f "$target/my..plan.json"
}

e2e_without_skills() {
    # 2. --without-skills (17 + core_doc_count) + 27-skill incremental re-enable
    local without_skills_target="$TEST_DIR/without-skills-target"
    mkdir -p "$without_skills_target"
    (
        cd "$without_skills_target"
        bash "$TEMPLATE_DIR/setup.sh" --dry-run --without-skills
    ) > "$TEST_DIR/without-skills-dry-run.txt"
    assert_file_contains "$TEST_DIR/without-skills-dry-run.txt" "Dry run complete: $no_skills_expected_count file(s) would be installed"

    (
        cd "$without_skills_target"
        bash "$TEMPLATE_DIR/setup.sh" --models antigravity,qwen --without-skills >/dev/null
        bash "$TEMPLATE_DIR/setup.sh" --models claude >/dev/null
    )
    for prefix in ".claude" ".agents" ".qwen"; do
        [ -f "$without_skills_target/$prefix/skills/sdd-docs/SKILL.md" ] || fail "incremental re-enable missing $prefix/skills/sdd-docs/SKILL.md"
    done
    [ "$(find "$without_skills_target/.claude/skills" "$without_skills_target/.agents/skills" "$without_skills_target/.qwen/skills" -name 'SKILL.md' | wc -l | tr -d ' ')" -eq 27 ] || fail "expected 27 skills after re-enable"
}

e2e_interactive() {
    # 4. Interactive pipe menu + invalid trailing delimiter guard
    local interactive_bad="$TEST_DIR/interactive-bad"
    local interactive_ok="$TEST_DIR/interactive-ok"
    mkdir -p "$interactive_bad" "$interactive_ok"
    if (
        cd "$interactive_bad"
        printf '1,\n' | bash "$TEMPLATE_DIR/setup.sh" --interactive
    ) > "$TEST_DIR/interactive-bad.txt" 2>&1; then
        fail "interactive setup accepted trailing delimiter"
    fi
    assert_file_contains "$TEST_DIR/interactive-bad.txt" "without empty values"

    (
        cd "$interactive_ok"
        printf '2,8\n' | bash "$TEMPLATE_DIR/setup.sh" --interactive --without-skills >/dev/null
    )
    python3 -B -c 'import json, pathlib, sys; m = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")); assert m["requested_models"] == ["antigravity", "gemma"] and m["managed_adapter_models"] == ["antigravity"]' "$interactive_ok/template-manifest.json"
}

e2e_symlink_ro_preset() {
    # 5. Symlinked setup.sh CLI + mock runtime binaries + --doctor E2E
    mkdir -p "$TEST_DIR/bin"
    ln -s "$TEMPLATE_DIR/setup.sh" "$TEST_DIR/bin/ai-setup"
    for cli in claude agy qwen opencode codex cursor-agent copilot; do
        printf '#!/bin/bash\nexit 0\n' > "$TEST_DIR/bin/$cli"
        chmod +x "$TEST_DIR/bin/$cli"
    done
    local sym_cli_target="$TEST_DIR/sym-cli-target"
    mkdir -p "$sym_cli_target"
    (
        cd "$sym_cli_target"
        bash "$TEST_DIR/bin/ai-setup" --models claude >/dev/null
        PATH="$TEST_DIR/bin:$PATH" bash "$TEST_DIR/bin/ai-setup" --doctor
    ) > "$TEST_DIR/sym-cli-doctor.txt"
    assert_file_contains "$TEST_DIR/sym-cli-doctor.txt" "Doctor result: READY"

    # 6. 0444 read-only source manifest + custom $SRC_DIR preset
    local ro_template="$TEST_DIR/ro-template"
    local corp_target="$TEST_DIR/corp-target"
    mkdir -p "$ro_template/lib" "$ro_template/task-evidence" "$ro_template/docs" "$corp_target"
    for tpl_f in setup.sh template-paths.sh AGENTS.md CLAUDE.md GEMINI.md QWEN.md template-manifest.json; do
        cp "$TEMPLATE_DIR/$tpl_f" "$ro_template/$tpl_f"
    done
    cp "$TEMPLATE_DIR/lib/installer_lib.py" "$ro_template/lib/installer_lib.py"
    cp -R "$TEMPLATE_DIR/tools" "$ro_template/tools"
    cp -R "$TEMPLATE_DIR/adapters" "$ro_template/adapters"
    cp -R "$TEMPLATE_DIR/skills" "$ro_template/skills"
    cp -R "$TEMPLATE_DIR/docs/current" "$ro_template/docs/current"
    cp -R "$TEMPLATE_DIR/docs/templates" "$ro_template/docs/templates"
    touch "$ro_template/task-evidence/.gitkeep"
    mkdir -p "$ro_template/docs/templates/presets/corp-api"
    printf '# Corp API — [Feature name]\n' > "$ro_template/docs/templates/presets/corp-api/README.md"
    chmod 0444 "$ro_template/template-manifest.json"
    chmod -R a-w "$ro_template"
    (
        cd "$corp_target"
        bash "$ro_template/setup.sh" --models claude --without-skills --preset corp-api >/dev/null
        PATH="$TEST_DIR/bin:$PATH" bash "$ro_template/setup.sh" --doctor
    ) > "$TEST_DIR/corp-doctor.txt"
    chmod -R u+w "$ro_template"
    [ "$(file_mode "$corp_target/template-manifest.json")" = "644" ] || fail "expected 0644 destination manifest from 0444 source"
    [ -d "$corp_target/docs/templates/presets/corp-api" ] || fail "custom \$SRC_DIR preset directory was not installed"
    assert_file_contains "$TEST_DIR/corp-doctor.txt" "PASS preset: custom default_preset 'corp-api' verified"
}

e2e_preflight_conflicts() {
    # 7. Symlink / path-conflict preflight block + dry-run blocked symlink + hardlink replacement
    local ancestor_target="$TEST_DIR/ancestor-target"
    local outside_docs="$TEST_DIR/outside-docs"
    mkdir -p "$ancestor_target" "$outside_docs"
    ln -s "$outside_docs" "$ancestor_target/docs"
    if (
        cd "$ancestor_target"
        bash "$TEMPLATE_DIR/setup.sh"
    ) > "$TEST_DIR/ancestor-symlink.txt" 2>&1; then
        fail "accepted symlinked parent directory"
    fi
    assert_file_contains "$TEST_DIR/ancestor-symlink.txt" "Refusing to write through symlink"
    [ ! -e "$ancestor_target/AGENTS.md" ] || fail "preflight wrote before rejecting parent symlink"

    local collision_target="$TEST_DIR/collision-target"
    mkdir -p "$collision_target/docs"
    printf 'file\n' > "$collision_target/docs/templates"
    if (
        cd "$collision_target"
        bash "$TEMPLATE_DIR/setup.sh"
    ) > "$TEST_DIR/collision.txt" 2>&1; then
        fail "accepted file where directory is required"
    fi
    assert_file_contains "$TEST_DIR/collision.txt" "Expected directory but found file"

    local dry_blocked="$TEST_DIR/dry-blocked"
    mkdir -p "$dry_blocked"
    ln -s /private/tmp/external-rules "$dry_blocked/AGENTS.md"
    (
        cd "$dry_blocked"
        bash "$TEMPLATE_DIR/setup.sh" --dry-run --force
    ) > "$TEST_DIR/dry-blocked.txt"
    [ "$(grep -Fc 'BLOCKED (symlink): AGENTS.md' "$TEST_DIR/dry-blocked.txt")" -eq 1 ] || fail "expected single BLOCKED symlink line"

    local hardlink_target="$TEST_DIR/hardlink-target"
    local outside_file="$TEST_DIR/outside-rules"
    mkdir -p "$hardlink_target"
    printf 'outside untouched\n' > "$outside_file"
    ln "$outside_file" "$hardlink_target/AGENTS.md"
    (
        cd "$hardlink_target"
        bash "$TEMPLATE_DIR/setup.sh" --force --without-skills >/dev/null
    )
    assert_file_contains "$outside_file" "outside untouched"
}

e2e_v071_update_and_doctor() {
    # 8. v0.7.1 -> v0.7.2 E2E --update backup & CREATED_FILES.txt (CI-safe SHA fallback)
    local v071_commit
    v071_commit="$(git -C "$TEMPLATE_DIR" rev-parse --verify 'v0.7.1^{commit}' 2>/dev/null || git -C "$TEMPLATE_DIR" rev-parse --verify 'dd017be73cf5f8fba87fd7b72eb44c3451295168^{commit}')"
    local v071_src="$TEST_DIR/v071-src"
    local v071_up_target="$TEST_DIR/v071-up-target"
    mkdir -p "$v071_src" "$v071_up_target"
    git -C "$TEMPLATE_DIR" archive "$v071_commit" | tar -x -C "$v071_src"
    (
        cd "$v071_up_target"
        bash "$v071_src/setup.sh" --models claude --without-skills >/dev/null
    )
    printf 'custom v071 rules\n' > "$v071_up_target/AGENTS.md"
    (
        cd "$v071_up_target"
        bash "$TEMPLATE_DIR/setup.sh" --update --without-skills
    ) > "$TEST_DIR/v071-update.txt"
    local v071_backup
    v071_backup="$(find "$v071_up_target" -maxdepth 1 -type d -name '.ai-template-backup.*' -print -quit)"
    [ -n "$v071_backup" ] || fail "v0.7.1 -> v0.7.2 update did not create backup directory"
    assert_file_contains "$v071_backup/AGENTS.md" "custom v071 rules"
    assert_file_contains "$v071_backup/RECOVERY.md" "Template update recovery"
    assert_file_contains "$v071_backup/CREATED_FILES.txt" "tools/_sdd_core.py"
    [ -f "$v071_up_target/tools/_sdd_core.py" ] || fail "v0.7.1 -> v0.7.2 update did not install tools/_sdd_core.py"

    # 9. Source-template --doctor E2E + Mermaid missing Puppeteer config guard
    (
        cd "$TEMPLATE_DIR"
        bash "$TEMPLATE_DIR/setup.sh" --doctor
    ) > "$TEST_DIR/doctor-source.txt"
    assert_file_contains "$TEST_DIR/doctor-source.txt" "PASS skills: 9 canonical SDD skills verified"
    assert_file_contains "$TEST_DIR/doctor-source.txt" "Doctor result: READY"

    if MMDC_BIN=true MMDC_PUPPETEER_CONFIG=tests/missing-puppeteer-config.json bash "$TEMPLATE_DIR/tests/render-mermaid.sh" > "$TEST_DIR/missing-pup.txt" 2>&1; then
        fail "render-mermaid.sh accepted missing Puppeteer config"
    fi
    assert_file_contains "$TEST_DIR/missing-pup.txt" "Missing Puppeteer config"
}

e2e_pids=""
for e2e_fn in \
    e2e_core_and_migplan \
    e2e_without_skills \
    e2e_interactive \
    e2e_symlink_ro_preset \
    e2e_preflight_conflicts \
    e2e_v071_update_and_doctor; do
    ( "$e2e_fn" ) &
    e2e_pids="$e2e_pids $!"
done

for pid in $e2e_pids; do
    wait "$pid"
done

# 10. Fast in-process + cached-archive unittest suite
(
    cd "$TEMPLATE_DIR"
    python3 -B -W error::ResourceWarning -m unittest tests.test_installer
)

echo "PASS: setup installer regression tests"
