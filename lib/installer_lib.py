#!/usr/bin/env python3
"""Installer, manifest, ownership, and doctor engine for ai-project-template."""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import inspect
import json
import os
import re
import shutil
import stat
import subprocess
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import unquote

TEMPLATE_ID = "ai-agent-obsidian-project-template"
REQUIRED_PROFILES = ("core", "--with-advanced-docs", "--with-legacy-agents")
BUILTIN_PRESETS = {"general", "web-api", "cli-tool", "ai-agent"}
KEBAB_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

SDD_SKILL_SLUGS = (
    "sdd-docs",
    "sdd-specify",
    "sdd-clarify",
    "sdd-plan",
    "sdd-tasks",
    "sdd-analyze",
    "sdd-implement",
    "sdd-fix",
)
SKILL_TREES = (".claude", ".agents", ".qwen")

CANONICAL_RUNTIMES = (
    "claude",
    "antigravity",
    "qwen",
    "opencode",
    "codex",
    "cursor",
    "copilot",
    "gemma",
)
DEFAULT_RUNTIMES = (
    "claude",
    "antigravity",
    "qwen",
    "opencode",
    "codex",
    "cursor",
    "copilot",
)
KNOWN_MANIFEST_RUNTIMES = set(CANONICAL_RUNTIMES) | {"gemini"}

RUNTIME_REGISTRY: dict[str, dict[str, object]] = {
    "claude": {
        "adapter": "CLAUDE.md",
        "source_adapter": "CLAUDE.md",
        "cli": ["claude"],
        "skill_tree": ".claude",
    },
    "antigravity": {
        "adapter": "GEMINI.md",
        "source_adapter": "GEMINI.md",
        "cli": ["agy", "antigravity"],
        "skill_tree": ".agents",
    },
    "qwen": {
        "adapter": "QWEN.md",
        "source_adapter": "QWEN.md",
        "cli": ["qwen"],
        "skill_tree": ".qwen",
    },
    "opencode": {
        "adapter": None,
        "source_adapter": None,
        "cli": ["opencode"],
        "skill_tree": ".agents",
    },
    "codex": {
        "adapter": None,
        "source_adapter": None,
        "cli": ["codex"],
        "skill_tree": ".agents",
    },
    "cursor": {
        "adapter": ".cursor/rules/agents.mdc",
        "source_adapter": "adapters/cursor-agents.mdc",
        "cli": ["cursor-agent", "cursor"],
        "skill_tree": ".agents",
    },
    "copilot": {
        "adapter": ".github/copilot-instructions.md",
        "source_adapter": "adapters/copilot-instructions.md",
        "cli": ["copilot"],
        "skill_tree": ".agents",
    },
    "gemma": {
        "adapter": None,
        "source_adapter": None,
        "cli": [],
        "skill_tree": None,
    },
}

ADAPTER_TO_RUNTIME: dict[str, str] = {
    str(cfg["adapter"]): runtime
    for runtime, cfg in RUNTIME_REGISTRY.items()
    if cfg["adapter"] is not None
}

ALL_SKILL_PATHS: set[str] = {
    f"{prefix}/skills/{slug}/SKILL.md"
    for prefix in SKILL_TREES
    for slug in SDD_SKILL_SLUGS
}

SOURCE_OVERRIDES: dict[str, str] = {
    ".agents/AGENTS.md": "AGENTS.md",
    ".cursor/rules/agents.mdc": "adapters/cursor-agents.mdc",
    ".github/copilot-instructions.md": "adapters/copilot-instructions.md",
    **{
        f"{prefix}/skills/{slug}/SKILL.md": f"skills/{slug}/SKILL.md"
        for prefix in SKILL_TREES
        for slug in SDD_SKILL_SLUGS
    },
}

PRIOR_TEMPLATE_SHA256S: dict[str, set[str]] = {
    "CLAUDE.md": {"dd1f9d23798a7fa56c485f79a88673b92afe19e8b8550a8119cd79499028641a"},
    "GEMINI.md": {"7277122704187512c0cec801eeb99c4f92668a04e63a36c77fd680d5f0acb45b"},
    "QWEN.md": {"b799d01b4909119a3da308a805cb158a05aee07fa61d3d0a1a35940e50683d51"},
    "skills/sdd-docs/SKILL.md": {
        "4ff7e524649180e017f0069acd525506619310619744f72e3dc92c57dd569afb",
        "c7fcdd2670ea4fde6656fa1e337beeec0311a7bc307ed0e3222ecbdeeb64a7c6",
    },
    "skills/sdd-specify/SKILL.md": {"3595f0930d4864be24271edfb0c3a084898726d22d76950751d034940abeb034"},
    "skills/sdd-clarify/SKILL.md": {"e4ac7aa24dbfa92ba40214cac370879aff2f5404784cca71367011110878a2ab"},
    "skills/sdd-plan/SKILL.md": {"1ac4e8e54d29a9448f23b2892836a7b4a339a865e65e787456b556c60880824a"},
    "skills/sdd-tasks/SKILL.md": {"e5a3c2a081f52ab63333fa511de50759bd21968ea841d81963ef162d649da1ef"},
    "skills/sdd-analyze/SKILL.md": {"39cf981dc3547d01c2c4ced0c0c7fce839369a7b932c57fc92df41a586676306"},
    "skills/sdd-implement/SKILL.md": {
        "9d8b5b678fb4e55e1c5f2062080dbe2b21e47e54992c07d97d3b7a84ad14a2ac",
        "c093e6656692fa32ad8f9bfabef0e172cde369e3aa4f81beb204effa873f16cb",
    },
    "skills/sdd-fix/SKILL.md": {
        "ab237567af83c3ab2783921561928614605a9618a8111714a2ce1861ecdb4535",
    },
}

DOCTOR_LINK_SKIP_DIRS = {
    ".git",
    "plans",
    "node_modules",
    ".venv",
    "venv",
    "vendor",
    "dist",
    "build",
    ".next",
    "target",
    ".obsidian",
    "__pycache__",
    ".pytest_cache",
    ".tox",
    "coverage",
}


def validate_rel_path(value: object, context: str = "path") -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} contains an empty or non-string path")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError(f"{context} contains a control character")
    pure = PurePosixPath(value)
    if pure.is_absolute() or value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/")):
        raise ValueError(f"{context} contains an unsafe path: {value}")
    return value


def is_safe_rel_path(value: object) -> bool:
    try:
        validate_rel_path(value)
        return True
    except ValueError:
        return False


def has_symlink_component(base: Path, rel_path: str) -> bool:
    current = base
    for part in PurePosixPath(rel_path).parts:
        current = current / part
        if current.is_symlink():
            return True
    return False


def read_regular_bytes_nofollow(base: Path, rel_path: str) -> bytes:
    if has_symlink_component(base, rel_path):
        raise ValueError(f"refusing symlink path: {rel_path}")
    target = base / rel_path
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(str(target), flags)
    except OSError as exc:
        raise ValueError(f"cannot open regular file {rel_path}: {exc}") from exc
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            raise ValueError(f"not a regular file: {rel_path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def read_regular_text_nofollow(base: Path, rel_path: str, *, errors: str = "strict") -> str:
    return read_regular_bytes_nofollow(base, rel_path).decode("utf-8", errors=errors)


def sha256_nofollow(base: Path, rel_path: str) -> str | None:
    try:
        return hashlib.sha256(read_regular_bytes_nofollow(base, rel_path)).hexdigest()
    except ValueError:
        return None


def normalize_runtime(name: str) -> str:
    return "antigravity" if name == "gemini" else name


def dedup_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item and item not in seen:
            seen.add(item)
            out.append(item)
    return out


def active_skill_trees_for_models(models: list[str]) -> list[str]:
    trees: list[str] = []
    for raw_model in models:
        model = normalize_runtime(raw_model)
        cfg = RUNTIME_REGISTRY.get(model)
        if not cfg:
            continue
        tree = cfg.get("skill_tree")
        if isinstance(tree, str) and tree not in trees:
            trees.append(tree)
    return trees


def load_created_files_records(dest_dir: Path) -> set[str]:
    recorded: set[str] = set()
    try:
        entries = sorted(dest_dir.iterdir())
    except OSError:
        return recorded
    for entry in entries:
        if not entry.name.startswith(".ai-template-backup.") or entry.is_symlink() or not entry.is_dir():
            continue
        try:
            text = read_regular_text_nofollow(entry, "CREATED_FILES.txt", errors="replace")
        except ValueError:
            continue
        for raw_line in text.splitlines():
            candidate = raw_line.strip()
            if is_safe_rel_path(candidate):
                recorded.add(candidate)
    return recorded


def is_template_unchanged(src_dir: Path, dest_dir: Path, rel_path: str) -> bool:
    dest_hash = sha256_nofollow(dest_dir, rel_path)
    if dest_hash is None:
        return False
    src_rel = SOURCE_OVERRIDES.get(rel_path, rel_path)
    src_hash = sha256_nofollow(src_dir, src_rel)
    if src_hash is not None and dest_hash == src_hash:
        return True
    return dest_hash in PRIOR_TEMPLATE_SHA256S.get(src_rel, set())


def is_canonical_or_recorded_recovery(
    src_dir: Path,
    dest_dir: Path,
    rel_path: str,
    created_records: set[str],
) -> bool:
    if rel_path in created_records and not has_symlink_component(dest_dir, rel_path):
        target = dest_dir / rel_path
        if target.is_file() and not target.is_symlink():
            return True
    return is_template_unchanged(src_dir, dest_dir, rel_path)


# ---------------------------------------------------------------------------
# Subcommand: validate-source-manifest & load-profile-paths & source-version
# ---------------------------------------------------------------------------


def cmd_validate_source_manifest(args: list[str]) -> int:
    root = Path(args[0]).resolve()
    manifest = json.loads(read_regular_text_nofollow(root, "template-manifest.json"))
    if manifest.get("template") != TEMPLATE_ID:
        raise ValueError(f"manifest is not owned by {TEMPLATE_ID}")
    version = manifest.get("version")
    if not isinstance(version, str) or not SEMVER_RE.fullmatch(version):
        raise ValueError("manifest version must be semantic version text")
    profiles = manifest.get("profiles")
    required = set(REQUIRED_PROFILES)
    if not isinstance(profiles, dict) or not required.issubset(profiles):
        raise ValueError("manifest must define core, --with-advanced-docs, and --with-legacy-agents profiles")
    if "default_preset" in manifest and manifest["default_preset"] is not None:
        preset = manifest["default_preset"]
        if not isinstance(preset, str) or not KEBAB_SLUG_RE.fullmatch(preset):
            raise ValueError("manifest default_preset must be a lowercase kebab-case slug")
    if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
        raise ValueError("manifest skills_enabled must be a boolean")

    all_paths: dict[str, str] = {}
    for name in REQUIRED_PROFILES:
        entries = profiles[name]
        if not isinstance(entries, list):
            raise ValueError(f"{name} must be a list")
        for raw_entry in entries:
            entry = validate_rel_path(raw_entry, name)
            if entry in all_paths:
                raise ValueError(f"manifest profile path is duplicated: {entry}")
            for existing, existing_profile in all_paths.items():
                if entry.startswith(existing + "/") or existing.startswith(entry + "/"):
                    raise ValueError(
                        f"manifest profile paths overlap: {existing_profile}:{existing} and {name}:{entry}"
                    )
            all_paths[entry] = name
            src_rel = SOURCE_OVERRIDES.get(entry, entry)
            source = root / src_rel
            if has_symlink_component(root, src_rel) or not source.exists() or source.is_symlink():
                raise ValueError(f"manifest path is missing or unsafe in template: {entry}")

    managed_paths = manifest.get("managed_paths")
    if not isinstance(managed_paths, list):
        raise ValueError("managed_paths must be a list")
    managed_set: set[str] = set()
    for raw_entry in managed_paths:
        entry = validate_rel_path(raw_entry, "managed_paths")
        if entry in managed_set:
            raise ValueError(f"managed_paths contains a duplicate: {entry}")
        managed_set.add(entry)
        src_rel = SOURCE_OVERRIDES.get(entry, entry)
        source = root / src_rel
        if has_symlink_component(root, src_rel) or not source.exists() or source.is_symlink():
            raise ValueError(f"managed path is missing or unsafe in template: {entry}")

    managed_profiles = manifest.get("managed_profiles")
    if not isinstance(managed_profiles, list) or any(p not in required for p in managed_profiles):
        raise ValueError("managed_profiles must contain only known profile names")

    def covers(entry: str, path: str) -> bool:
        return path == entry or path.startswith(entry + "/")

    core = profiles["core"]
    advanced = profiles["--with-advanced-docs"]
    docs_dir = root / "docs"
    if docs_dir.is_symlink() or not docs_dir.is_dir():
        raise ValueError("missing or symlinked docs/ directory")
    for source in docs_dir.rglob("*"):
        rel_to_docs = source.relative_to(docs_dir)
        if "internal" in rel_to_docs.parts or source.name == ".DS_Store":
            continue
        rel_posix = source.relative_to(root).as_posix()
        if has_symlink_component(root, rel_posix) or source.is_symlink():
            raise ValueError(f"unsafe symlink inside template docs: {rel_posix}")
        if not source.is_file():
            continue
        if not any(covers(entry, rel_posix) for entry in [*core, *advanced]):
            raise ValueError(f"template documentation is not declared by a profile: {rel_posix}")
    return 0


def cmd_load_profile_paths(args: list[str]) -> int:
    manifest_path = Path(args[0])
    profile_name = args[1]
    data = json.loads(read_regular_text_nofollow(manifest_path.parent, manifest_path.name))
    entries = data["profiles"][profile_name]
    if entries:
        print("\n".join(entries))
    return 0


def cmd_source_version(args: list[str]) -> int:
    root = Path(args[0]).resolve()
    data = json.loads(read_regular_text_nofollow(root, "template-manifest.json"))
    print(str(data.get("version", "unknown")))
    return 0


# ---------------------------------------------------------------------------
# Skill & Cursor MDC validation helpers
# ---------------------------------------------------------------------------


def verify_skill_markdown(text: str, expected_slug: str | None = None, *, require_disable_flag: bool = True) -> str | None:
    normalized = text.replace("\r\n", "\n")
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n(.+)$", normalized, flags=re.S)
    if not m:
        return "missing valid YAML frontmatter"
    fm_text, body = m.group(1), m.group(2)
    if expected_slug is not None:
        if not re.search(rf"^name:\s*['\"]?{re.escape(expected_slug)}['\"]?\s*$", fm_text, flags=re.M):
            return "missing or mismatched name frontmatter"
    elif not re.search(r"^name:\s*\S+", fm_text, flags=re.M):
        return "missing name frontmatter"
    if not re.search(r"^description:\s*\S+", fm_text, flags=re.M):
        return "missing description frontmatter"
    if require_disable_flag and not re.search(r"^disable-model-invocation:\s*true\s*$", fm_text, flags=re.M):
        return "missing 'disable-model-invocation: true' in frontmatter"
    if "AGENTS.md" not in body:
        return "does not delegate to AGENTS.md"
    return None


def has_cursor_always_apply(text: str) -> bool:
    normalized = text.replace("\r\n", "\n")
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", normalized, flags=re.S)
    if not m:
        return False
    return bool(re.search(r"^alwaysApply:\s*true\s*$", m.group(1), flags=re.M))


# ---------------------------------------------------------------------------
# Subcommand: doctor-source, doctor-manifest, doctor-links, doctor-spec-readiness
# ---------------------------------------------------------------------------


def cmd_doctor_source(args: list[str]) -> int:
    src_dir = Path(args[0]).resolve()
    status = 0

    static_adapters = (
        "CLAUDE.md",
        "GEMINI.md",
        "QWEN.md",
        "adapters/cursor-agents.mdc",
        "adapters/copilot-instructions.md",
        "docs/templates/1. Agent System Prompt Template.md",
    )
    adapters_ok = True
    for rel in static_adapters:
        try:
            raw_bytes = read_regular_bytes_nofollow(src_dir, rel)
            text = raw_bytes.decode("utf-8", errors="replace")
        except ValueError:
            print(
                f"FAIL adapter: missing regular {rel}. Remediation: restore {rel} from Git.",
                file=sys.stderr,
            )
            status = 1
            adapters_ok = False
            continue
        if "AGENTS.md" not in text:
            print(
                f"FAIL adapter: {rel} does not delegate to AGENTS.md. Remediation: restore {rel} from Git.",
                file=sys.stderr,
            )
            status = 1
            adapters_ok = False
        elif rel == "adapters/cursor-agents.mdc":
            if len(raw_bytes) > 450 or not has_cursor_always_apply(text):
                print(
                    "FAIL adapter: adapters/cursor-agents.mdc must declare 'alwaysApply: true' and stay <= 450 bytes. Remediation: restore adapters/cursor-agents.mdc from Git.",
                    file=sys.stderr,
                )
                status = 1
                adapters_ok = False
    if adapters_ok:
        print("PASS adapters: static runtime adapters and system-prompt template delegate to AGENTS.md")

    source_tools = (
        "lib/installer_lib.py",
        "tools/validate-task-evidence.py",
        "tools/docs_validation.py",
        "tools/validate-docs.py",
        "tools/new-feature.py",
        "tools/export-tasks.py",
    )
    tools_ok = True
    for rel in source_tools:
        try:
            read_regular_bytes_nofollow(src_dir, rel)
        except ValueError:
            print(
                f"FAIL tools: missing or symlinked source tool {rel}. Remediation: restore {rel} from Git.",
                file=sys.stderr,
            )
            status = 1
            tools_ok = False
    if tools_ok:
        print("PASS tools: source SDD and validation scripts verified in tools/ and lib/")

    skills_dir = src_dir / "skills"
    skill_err: str | None = None
    if skills_dir.is_symlink() or not skills_dir.is_dir():
        skill_err = "missing or symlinked skills/ directory"
    else:
        for slug in SDD_SKILL_SLUGS:
            rel = f"skills/{slug}/SKILL.md"
            try:
                raw_bytes = read_regular_bytes_nofollow(src_dir, rel)
            except ValueError:
                skill_err = f"missing or symlinked {rel}"
                break
            if len(raw_bytes) > 4096:
                skill_err = f"{rel} exceeds 4096 bytes ({len(raw_bytes)} B)"
                break
            err = verify_skill_markdown(raw_bytes.decode("utf-8", errors="replace"), expected_slug=slug)
            if err:
                skill_err = f"{rel} {err}"
                break
    if skill_err is None:
        print(f"PASS skills: {len(SDD_SKILL_SLUGS)} canonical SDD skills verified")
    else:
        print(
            f"FAIL skills: {skill_err}. Remediation: restore canonical skills/sdd-*/SKILL.md from Git.",
            file=sys.stderr,
        )
        status = 1

    return status


def load_validated_downstream_manifest(dest_dir: Path) -> dict[str, object]:
    manifest = json.loads(read_regular_text_nofollow(dest_dir, "template-manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("template") != TEMPLATE_ID:
        raise ValueError(f"manifest is not owned by {TEMPLATE_ID}")
    managed_paths = manifest.get("managed_paths")
    if not isinstance(managed_paths, list) or not all(is_safe_rel_path(p) for p in managed_paths):
        raise ValueError("manifest has unsafe managed_paths")
    profiles = manifest.get("profiles")
    if not isinstance(profiles, dict) or any(
        not isinstance(paths, list) or not all(is_safe_rel_path(p) for p in paths)
        for paths in profiles.values()
    ):
        raise ValueError("manifest has unsafe profile paths")
    models = manifest.get("requested_models", manifest.get("selected_models"))
    if not isinstance(models, list) or any(
        not isinstance(m, str) or m not in KNOWN_MANIFEST_RUNTIMES for m in models
    ):
        raise ValueError("manifest has no valid selected runtime list")
    managed_adapters = manifest.get("managed_adapter_models", [])
    if not isinstance(managed_adapters, list) or any(
        not isinstance(m, str) or m not in KNOWN_MANIFEST_RUNTIMES for m in managed_adapters
    ):
        raise ValueError("manifest has invalid managed_adapter_models")
    managed_profiles = manifest.get("managed_profiles", ["core"])
    if not isinstance(managed_profiles, list) or any(p not in REQUIRED_PROFILES for p in managed_profiles):
        raise ValueError("manifest has invalid managed_profiles")
    if "default_preset" in manifest and manifest["default_preset"] is not None:
        preset = manifest["default_preset"]
        if not isinstance(preset, str) or not KEBAB_SLUG_RE.fullmatch(preset):
            raise ValueError("manifest has invalid default_preset")
    if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
        raise ValueError("manifest has invalid skills_enabled")
    return manifest


def _find_cli_binary(candidates: list[str]) -> str | None:
    for name in candidates:
        if shutil.which(name) is not None:
            return name
    return None


def _check_backup_dirs_gitignored(dest_dir: Path) -> None:
    try:
        backups = sorted(
            entry.name
            for entry in dest_dir.iterdir()
            if entry.name.startswith(".ai-template-backup.") and (entry.is_dir() or entry.is_symlink())
        )
    except OSError:
        return
    if not backups:
        return
    git_dir = dest_dir / ".git"
    gitignore_covers = False
    try:
        gi_text = read_regular_text_nofollow(dest_dir, ".gitignore", errors="replace")
        gitignore_covers = ".ai-template-backup" in gi_text
    except ValueError:
        pass

    for bname in backups:
        ignored = gitignore_covers
        if not ignored and git_dir.exists():
            try:
                res = subprocess.run(
                    ["git", "-C", str(dest_dir), "check-ignore", "-q", bname],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                ignored = res.returncode == 0
            except OSError:
                ignored = gitignore_covers
        if not ignored:
            print(
                f"WARN backup: local backup directory {bname} is present and not git-ignored; add '.ai-template-backup.*/' to .gitignore or remove it after verifying the update."
            )


def cmd_doctor_manifest(args: list[str]) -> int:
    dest_dir = Path(args[0]).resolve()
    strict = "--strict" in args[1:]
    try:
        manifest = load_validated_downstream_manifest(dest_dir)
    except Exception:
        print(
            "FAIL manifest: invalid template-owned manifest. Remediation: inspect template-manifest.json; do not run --update until it is repaired.",
            file=sys.stderr,
        )
        return 1

    status = 0
    print(f"PASS manifest: template-owned; version={manifest.get('version', 'unknown')}")

    preset = manifest.get("default_preset")
    if isinstance(preset, str):
        if preset in BUILTIN_PRESETS:
            print(f"PASS preset: built-in default_preset '{preset}' verified")
        else:
            rel_preset = f"docs/templates/presets/{preset}"
            preset_dir = dest_dir / rel_preset
            if has_symlink_component(dest_dir, rel_preset) or not preset_dir.is_dir() or preset_dir.is_symlink():
                print(
                    f"FAIL preset: custom default_preset '{preset}' is missing or symlinked at {rel_preset}. Remediation: create a regular directory at {rel_preset} or run setup.sh --update --preset general.",
                    file=sys.stderr,
                )
                status = 1
            else:
                print(f"PASS preset: custom default_preset '{preset}' verified")

    raw_models = [str(m) for m in manifest.get("requested_models", manifest.get("selected_models", []))]
    raw_managed = {normalize_runtime(str(m)) for m in manifest.get("managed_adapter_models", [])}

    for raw_runtime in raw_models:
        canon = normalize_runtime(raw_runtime)
        cfg = RUNTIME_REGISTRY.get(canon)
        if cfg is None:
            print(
                f"FAIL runtime: unknown selected runtime '{raw_runtime}'. Remediation: repair the manifest.",
                file=sys.stderr,
            )
            status = 1
            continue

        if canon == "gemma":
            sys_prompt_rel = "docs/templates/1. Agent System Prompt Template.md"
            try:
                read_regular_bytes_nofollow(dest_dir, sys_prompt_rel)
                print(
                    "FAIL runtime gemma: host-level system-prompt injection cannot be verified from this repository. Remediation: verify the host injects docs/templates/1. Agent System Prompt Template.md before enabling write tools.",
                    file=sys.stderr,
                )
            except ValueError:
                print(
                    "FAIL runtime gemma: the required system-prompt template is missing. Remediation: restore docs/templates/1. Agent System Prompt Template.md with setup.sh --update.",
                    file=sys.stderr,
                )
            status = 1
            continue

        adapter = cfg["adapter"]
        cli_candidates = [str(c) for c in cfg["cli"]]  # type: ignore[union-attr]

        if adapter is None:
            if canon == "codex":
                override_path = dest_dir / "AGENTS.override.md"
                if override_path.exists() or override_path.is_symlink():
                    if strict:
                        print(
                            "FAIL runtime codex: unmanaged AGENTS.override.md exists alongside canonical AGENTS.md. Remediation: remove AGENTS.override.md or merge approved rules into AGENTS.md.",
                            file=sys.stderr,
                        )
                        status = 1
                        continue
                    print(
                        "WARN runtime codex: unmanaged AGENTS.override.md exists alongside AGENTS.md; review it so it does not override AGENTS.md."
                    )
            found_cli = _find_cli_binary(cli_candidates)
            if found_cli is not None:
                print(f"PASS runtime {raw_runtime}: AGENTS.md and '{found_cli}' are available")
            elif strict:
                print(
                    f"FAIL runtime {raw_runtime}: command '{cli_candidates[0]}' is unavailable. Remediation: install/enable that runtime or remove it from the selected runtime configuration.",
                    file=sys.stderr,
                )
                status = 1
            else:
                print(
                    f"WARN runtime {raw_runtime}: command '{cli_candidates[0]}' is unavailable locally; AGENTS.md is ready when installed."
                )
            continue

        adapter_rel = str(adapter)
        is_managed = canon in raw_managed
        if not is_managed:
            print(
                f"WARN runtime {raw_runtime}: adapter is user-owned or not managed; preserving it while checking its minimum contract."
            )
        try:
            adapter_text = read_regular_text_nofollow(dest_dir, adapter_rel, errors="replace")
        except ValueError:
            print(
                f"FAIL runtime {raw_runtime}: missing regular {adapter_rel}. Remediation: restore the managed adapter with setup.sh --update or add a regular user-owned adapter that delegates to AGENTS.md.",
                file=sys.stderr,
            )
            status = 1
            continue

        adapter_contract_ok = True
        if "AGENTS.md" not in adapter_text:
            if is_managed or strict:
                print(
                    f"FAIL runtime {raw_runtime}: {adapter_rel} does not delegate to AGENTS.md. Remediation: restore the managed adapter or reference AGENTS.md in {adapter_rel}.",
                    file=sys.stderr,
                )
                status = 1
                adapter_contract_ok = False
            else:
                print(
                    f"WARN runtime {raw_runtime}: user-owned {adapter_rel} does not reference AGENTS.md; add an AGENTS.md reference for strict compliance."
                )
        elif is_managed and canon == "cursor" and not has_cursor_always_apply(adapter_text):
            print(
                "FAIL runtime cursor: .cursor/rules/agents.mdc is missing 'alwaysApply: true' in frontmatter. Remediation: restore the managed adapter with setup.sh --update.",
                file=sys.stderr,
            )
            status = 1
            adapter_contract_ok = False

        if not adapter_contract_ok:
            continue

        found_cli = _find_cli_binary(cli_candidates)
        if found_cli is not None:
            print(f"PASS runtime {raw_runtime}: {adapter_rel} and '{found_cli}' are available")
        elif strict:
            print(
                f"FAIL runtime {raw_runtime}: command '{cli_candidates[0]}' is unavailable. Remediation: install/enable that runtime or remove it from the selected runtime configuration.",
                file=sys.stderr,
            )
            status = 1
        else:
            print(
                f"WARN runtime {raw_runtime}: command '{cli_candidates[0]}' is unavailable locally; {adapter_rel} is ready when installed."
            )

    managed_set = set(str(p) for p in manifest["managed_paths"])  # type: ignore[union-attr]
    tools_ok = True
    for tool_rel in (
        "tools/validate-task-evidence.py",
        "tools/docs_validation.py",
        "tools/validate-docs.py",
        "tools/new-feature.py",
        "tools/export-tasks.py",
    ):
        if tool_rel in managed_set:
            try:
                read_regular_bytes_nofollow(dest_dir, tool_rel)
            except ValueError:
                print(
                    f"FAIL tools: missing or symlinked managed tool {tool_rel}. Remediation: restore managed tools with setup.sh --update.",
                    file=sys.stderr,
                )
                status = 1
                tools_ok = False
        else:
            print(f"WARN tools: {tool_rel} is user-owned or unmanaged; preserving without managed integrity check.")
    if tools_ok:
        print("PASS tools: managed downstream tools verified")

    skills_enabled = bool(manifest.get("skills_enabled", True))
    skill_paths = [
        str(path)
        for path in manifest["managed_paths"]  # type: ignore[union-attr]
        if re.fullmatch(r"\.(claude|agents|qwen)/skills/[^/]+/SKILL\.md", str(path))
    ]
    active_trees = active_skill_trees_for_models(raw_models)

    if not skills_enabled and not skill_paths:
        print("INFO skills: disabled via --without-skills")
    else:
        skills_ok = True
        for sp in skill_paths:
            try:
                s_bytes = read_regular_bytes_nofollow(dest_dir, sp)
                s_err = verify_skill_markdown(
                    s_bytes.decode("utf-8", errors="replace"),
                    require_disable_flag=True,
                )
            except ValueError:
                s_err = "missing or symlinked"
            if s_err is not None:
                print(
                    f"FAIL skills: missing, symlinked, or corrupted managed skill {sp}. Remediation: restore managed skills with setup.sh --update.",
                    file=sys.stderr,
                )
                status = 1
                skills_ok = False
        if skill_paths and skills_ok:
            print(f"PASS skills: {len(skill_paths)} managed downstream SDD skill(s) verified")
        elif not skill_paths:
            if not active_trees:
                print("INFO skills: no repository skill directories apply to selected runtime(s)")
            else:
                print(
                    "WARN skills: no managed SDD skills recorded in manifest; run setup.sh --update to install /sdd-* skills or --without-skills to opt out."
                )

    for tree in active_trees:
        skills_root = dest_dir / tree / "skills"
        if skills_root.is_symlink() or not skills_root.is_dir():
            continue
        for child in sorted(skills_root.iterdir()):
            cand = child / "SKILL.md"
            rel_cand = f"{tree}/skills/{child.name}/SKILL.md"
            if rel_cand not in managed_set and (cand.exists() or cand.is_symlink()):
                print(f"WARN skills: unmanaged skill {rel_cand} preserved alongside template skills.")

    _check_backup_dirs_gitignored(dest_dir)

    helper_rel = "tools/docs_validation.py"
    if helper_rel not in managed_set and (dest_dir / helper_rel).exists() and not (dest_dir / helper_rel).is_symlink():
        print("WARN spec readiness: tools/docs_validation.py is user-owned; skipping managed semantic spec checks.")

    return status


def _strip_markdown_code(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
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
            close_m = re.match(
                r"^[ \t]*(" + re.escape(fence_char) + r"{" + str(fence_len) + r",})[ \t]*\r?\n?$",
                line,
            )
            if close_m:
                in_fence = False
            out.append("\n")
    joined = "".join(out)
    return re.sub(r"(`+)([^\n]*?)\1", "", joined)


def _should_skip_doctor_link_part(part: str) -> bool:
    return part in DOCTOR_LINK_SKIP_DIRS or part.startswith(".ai-template-backup.")


def cmd_doctor_links(args: list[str]) -> int:
    root = Path(args[0]).resolve()
    missing: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = [
            d
            for d in sorted(dirnames)
            if not _should_skip_doctor_link_part(d) and not (Path(dirpath) / d).is_symlink()
        ]
        for fname in sorted(filenames):
            if not fname.endswith(".md"):
                continue
            note = Path(dirpath) / fname
            if note.is_symlink():
                continue
            rel_note = note.relative_to(root).as_posix()
            try:
                raw_text = read_regular_text_nofollow(root, rel_note, errors="replace")
            except ValueError:
                continue
            cleaned = _strip_markdown_code(raw_text)
            for target in re.findall(r"(?<!!)(?:!?)\[[^]]*\]\(([^)]+)\)", cleaned):
                stripped_target = target.strip()
                if stripped_target.startswith("<") and ">" in stripped_target:
                    raw_target = stripped_target[1 : stripped_target.index(">")].split("#", 1)[0].strip()
                else:
                    no_title = re.sub(r"""[ \t]+(?:"[^"]*"|'[^']*')$""", "", stripped_target)
                    raw_target = no_title.split("#", 1)[0].strip().strip("<>")
                if not raw_target:
                    continue
                unquoted_once = unquote(raw_target).strip()
                unquoted_twice = unquote(unquoted_once).strip()
                forbidden_schemes = ("file:", "javascript:", "data:", "vbscript:", "obsidian:")
                if any(
                    cand.lower().startswith(forbidden_schemes)
                    for cand in (raw_target, unquoted_once, unquoted_twice)
                ):
                    missing.append(f"{rel_note} -> {raw_target}")
                    continue
                if unquoted_once.lower().startswith(("http://", "https://", "mailto:", "tel:")):
                    continue
                candidate = (note.parent / unquoted_once).resolve()
                if not candidate.is_relative_to(root) or not candidate.exists():
                    missing.append(f"{rel_note} -> {raw_target}")
    if missing:
        print("FAIL docs links: " + "; ".join(missing[:10]), file=sys.stderr)
        return 1
    print("PASS docs links: local Markdown targets resolve")
    return 0


def cmd_doctor_spec_readiness(args: list[str]) -> int:
    dest_dir = Path(args[0]).resolve()
    src_dir = Path(args[1]).resolve()
    strict = "--strict" in args[2:]

    validator_dir: Path | None = None
    if dest_dir == src_dir:
        try:
            read_regular_bytes_nofollow(src_dir, "tools/docs_validation.py")
            validator_dir = src_dir / "tools"
        except ValueError:
            return 0
    else:
        try:
            manifest = load_validated_downstream_manifest(dest_dir)
            managed_set = set(str(p) for p in manifest["managed_paths"])  # type: ignore[union-attr]
            if "tools/docs_validation.py" in managed_set:
                read_regular_bytes_nofollow(dest_dir, "tools/docs_validation.py")
                validator_dir = dest_dir / "tools"
        except Exception:
            return 0

    current_root = dest_dir / "docs/current"
    if validator_dir is None or current_root.is_symlink() or not current_root.is_dir():
        return 0

    sys.path.insert(0, str(validator_dir))
    from docs_validation import (  # type: ignore[import-not-found]
        validate_clarify_gate,
        validate_feature_specs,
        validate_links,
        validate_mermaid,
    )

    docs_root = dest_dir / "docs"
    files = sorted(p for p in current_root.rglob("*.md") if not p.is_symlink())
    if files:
        validate_links(dest_dir, docs_root, files)
        validate_mermaid(dest_dir, files)
        clarify_kwargs = {"strict": strict} if "strict" in inspect.signature(validate_clarify_gate).parameters else {}
        cw = validate_clarify_gate(dest_dir, files, **clarify_kwargs) or []
        spec_kwargs = {"strict": strict} if "strict" in inspect.signature(validate_feature_specs).parameters else {}
        fw = validate_feature_specs(
            dest_dir,
            current_root / "05 - Product Features",
            require_tasks=False,
            **spec_kwargs,
        )
        for warning in [*cw, *fw]:
            print(f"WARN spec readiness: {warning}")
    print("PASS spec readiness: Clarify gate, Mermaid structure, and cross-spec traceability verified")
    return 0


# ---------------------------------------------------------------------------
# Subcommand: select-update-models, prepare-manifest-models, prepare-ownership
# ---------------------------------------------------------------------------


def _infer_models_from_legacy_manifest(manifest: dict[str, object]) -> list[str]:
    models = manifest.get("requested_models", manifest.get("selected_models"))
    if models is None:
        core_paths = manifest.get("profiles", {}).get("core", [])  # type: ignore[union-attr]
        models = [ADAPTER_TO_RUNTIME[p] for p in core_paths if p in ADAPTER_TO_RUNTIME]
    if not isinstance(models, list) or any(
        not isinstance(m, str) or m not in KNOWN_MANIFEST_RUNTIMES for m in models
    ):
        raise ValueError("manifest has invalid runtime selection")
    return dedup_preserve_order([normalize_runtime(m) for m in models])


def _infer_managed_adapters_from_manifest(manifest: dict[str, object]) -> list[str]:
    managed = manifest.get("managed_adapter_models")
    if managed is None:
        managed_paths = manifest.get("managed_paths", [])
        managed = [ADAPTER_TO_RUNTIME[p] for p in managed_paths if p in ADAPTER_TO_RUNTIME]  # type: ignore[union-attr]
    if not isinstance(managed, list) or any(
        not isinstance(m, str) or m not in KNOWN_MANIFEST_RUNTIMES for m in managed
    ):
        raise ValueError("manifest has invalid managed_adapter_models")
    return dedup_preserve_order([normalize_runtime(m) for m in managed])


def cmd_select_update_models(args: list[str]) -> int:
    src_dir = Path(args[0]).resolve()
    dest_dir = Path(args[1]).resolve()
    set_models_csv = args[2] if len(args) > 2 else ""

    manifest = load_validated_downstream_manifest(dest_dir)
    prior_models = _infer_models_from_legacy_manifest(manifest)
    prior_managed_adapters = _infer_managed_adapters_from_manifest(manifest)
    managed_profiles = manifest.get("managed_profiles")
    if managed_profiles is None:
        managed_profiles = ["core"]
    elif not isinstance(managed_profiles, list) or any(p not in REQUIRED_PROFILES for p in managed_profiles):
        raise ValueError("manifest has invalid managed_profiles")

    skills_enabled = bool(manifest.get("skills_enabled", True))
    created_records = load_created_files_records(dest_dir)

    if set_models_csv:
        requested_models = dedup_preserve_order([m for m in set_models_csv.split(",") if m])
        update_managed_adapters: list[str] = []
        for model in requested_models:
            adapter = RUNTIME_REGISTRY[model]["adapter"]
            if adapter is None:
                continue
            adapter_rel = str(adapter)
            target = dest_dir / adapter_rel
            if model in prior_managed_adapters:
                update_managed_adapters.append(model)
            elif not target.exists() and not target.is_symlink():
                update_managed_adapters.append(model)
            elif is_canonical_or_recorded_recovery(src_dir, dest_dir, adapter_rel, created_records):
                update_managed_adapters.append(model)
        models_out = requested_models
    else:
        models_out = prior_models or list(DEFAULT_RUNTIMES)
        update_managed_adapters = [
            m for m in models_out if RUNTIME_REGISTRY[m]["adapter"] is not None and m in prior_managed_adapters
        ]

    print(
        "|".join(
            [
                ",".join(models_out),
                str("--with-advanced-docs" in managed_profiles).lower(),
                str("--with-legacy-agents" in managed_profiles).lower(),
                ",".join(update_managed_adapters),
                str(skills_enabled).lower(),
            ]
        )
    )
    return 0


def cmd_prepare_manifest_models(args: list[str]) -> int:
    dest_dir = Path(args[0]).resolve()
    selected_csv = args[1]
    set_models_flag = args[2] == "true"

    manifest = json.loads(read_regular_text_nofollow(dest_dir, "template-manifest.json"))
    if not isinstance(manifest, dict) or manifest.get("template") != TEMPLATE_ID:
        print("UNMANAGED")
        return 0

    managed_paths = manifest.get("managed_paths")
    if not isinstance(managed_paths, list) or not all(isinstance(p, str) for p in managed_paths):
        raise ValueError("existing manifest has invalid managed_paths")
    profiles = manifest.get("profiles")
    if (
        not isinstance(profiles, dict)
        or not isinstance(profiles.get("core"), list)
        or not all(isinstance(p, str) for p in profiles["core"])
    ):
        raise ValueError("existing manifest has invalid profiles.core")
    if not all(is_safe_rel_path(p) for p in managed_paths):
        raise ValueError("existing manifest has unsafe managed_paths")
    if any(not isinstance(paths, list) or not all(is_safe_rel_path(p) for p in paths) for paths in profiles.values()):
        raise ValueError("existing manifest has unsafe profile paths")
    if "default_preset" in manifest and manifest["default_preset"] is not None:
        preset = manifest["default_preset"]
        if not isinstance(preset, str) or not KEBAB_SLUG_RE.fullmatch(preset):
            raise ValueError("existing manifest has invalid default_preset")
    if "skills_enabled" in manifest and not isinstance(manifest["skills_enabled"], bool):
        raise ValueError("existing manifest has invalid skills_enabled")

    existing = _infer_models_from_legacy_manifest(manifest)
    requested = dedup_preserve_order([m for m in selected_csv.split(",") if m])
    if set_models_flag:
        combined = [m for m in CANONICAL_RUNTIMES if m in requested]
    else:
        combined = [m for m in CANONICAL_RUNTIMES if m in existing or m in requested]
    print(",".join(combined))
    return 0


def cmd_prepare_ownership(args: list[str]) -> int:
    src_dir = Path(args[0]).resolve()
    dest_dir = Path(args[1]).resolve()
    selected = dedup_preserve_order([m for m in args[2].split(",") if m])
    with_skills = args[3] == "true"
    force = args[4] == "true"
    is_update = args[5] == "true"
    set_models_flag = args[6] == "true"

    template_owned = False
    prior_managed: set[str] = set()
    prior_core: set[str] = set()
    prior_managed_adapters: set[str] = set()

    try:
        manifest = json.loads(read_regular_text_nofollow(dest_dir, "template-manifest.json"))
        if isinstance(manifest, dict) and manifest.get("template") == TEMPLATE_ID:
            template_owned = True
            prior_managed = {str(p) for p in manifest.get("managed_paths", []) if isinstance(p, str)}
            prior_core = {
                str(p)
                for p in manifest.get("profiles", {}).get("core", [])
                if isinstance(p, str)
            }
            try:
                prior_managed_adapters = set(_infer_managed_adapters_from_manifest(manifest))
            except ValueError:
                prior_managed_adapters = set()
    except Exception:
        template_owned = False

    created_records = load_created_files_records(dest_dir) if template_owned else set()

    # 1. Validator bundle ownership
    helper = "tools/docs_validation.py"
    validator = "tools/validate-docs.py"
    helper_target = dest_dir / helper
    validator_target = dest_dir / validator
    helper_exists = helper_target.exists() or helper_target.is_symlink()
    validator_exists = validator_target.exists() or validator_target.is_symlink()

    if force:
        vb_managed = True
    elif is_update:
        if {helper, validator}.issubset(prior_managed) and {helper, validator}.issubset(prior_core):
            vb_managed = True
        elif not helper_exists and validator in prior_managed and validator in prior_core:
            vb_managed = True
        elif not helper_exists and not validator_exists:
            vb_managed = True
        elif template_owned and all(
            not (dest_dir / p).exists()
            and not (dest_dir / p).is_symlink()
            or is_canonical_or_recorded_recovery(src_dir, dest_dir, p, created_records)
            for p in (helper, validator)
        ):
            vb_managed = True
        else:
            vb_managed = False
    else:
        if template_owned and {helper, validator}.issubset(prior_managed) and {helper, validator}.issubset(prior_core):
            vb_managed = not has_symlink_component(dest_dir, helper) and not has_symlink_component(dest_dir, validator)
        else:
            vb_managed = not helper_exists and not validator_exists
    print(f"VALIDATOR_BUNDLE|{'true' if vb_managed else 'false'}")

    # 2. SDD tools ownership
    for key_name, rel in (("NEW_FEATURE", "tools/new-feature.py"), ("EXPORT_TASKS", "tools/export-tasks.py")):
        target = dest_dir / rel
        exists_or_link = target.exists() or target.is_symlink()
        if force:
            tool_managed = True
        elif template_owned and rel in prior_managed and rel in prior_core:
            tool_managed = is_update or not has_symlink_component(dest_dir, rel)
        elif not exists_or_link:
            tool_managed = True
        elif template_owned and is_canonical_or_recorded_recovery(src_dir, dest_dir, rel, created_records):
            tool_managed = True
        else:
            tool_managed = False
        print(f"{key_name}|{'true' if tool_managed else 'false'}")

    # 3. Deduplicated SDD skills ownership
    active_trees = active_skill_trees_for_models(selected)
    for prefix in active_trees:
        for slug in SDD_SKILL_SLUGS:
            rel = f"{prefix}/skills/{slug}/SKILL.md"
            target = dest_dir / rel
            exists_or_link = target.exists() or target.is_symlink()
            if not with_skills:
                if is_update and exists_or_link:
                    print(f"OPTOUT_SKILL|{rel}")
                continue
            if (
                force
                or not is_update
                or not exists_or_link
                or (rel in prior_managed and rel in prior_core)
                or (template_owned and is_canonical_or_recorded_recovery(src_dir, dest_dir, rel, created_records))
            ):
                print(f"SCHEDULE_SKILL|{rel}")
            else:
                print(f"USER_SKILL|{rel}")

    # 4. Orphan pruning when --set-models deselects previously managed adapters or skill trees
    if set_models_flag and template_owned:
        def _emit_orphan_action(rel_path: str) -> None:
            target = dest_dir / rel_path
            if not target.exists() and not target.is_symlink():
                return
            if has_symlink_component(dest_dir, rel_path) or target.is_symlink():
                print(f"WARN_MODIFIED_ORPHAN|{rel_path}")
            elif force or is_template_unchanged(src_dir, dest_dir, rel_path):
                print(f"PRUNE_FILE|{rel_path}")
            else:
                print(f"WARN_MODIFIED_ORPHAN|{rel_path}")

        for adapter_rel, runtime in ADAPTER_TO_RUNTIME.items():
            if runtime in selected:
                continue
            was_managed = (
                runtime in prior_managed_adapters
                or adapter_rel in prior_managed
                or is_canonical_or_recorded_recovery(src_dir, dest_dir, adapter_rel, created_records)
            )
            if was_managed:
                _emit_orphan_action(adapter_rel)

        for prefix in SKILL_TREES:
            if prefix in active_trees:
                continue
            for slug in SDD_SKILL_SLUGS:
                rel = f"{prefix}/skills/{slug}/SKILL.md"
                was_managed = rel in prior_managed or is_canonical_or_recorded_recovery(
                    src_dir, dest_dir, rel, created_records
                )
                if was_managed:
                    _emit_orphan_action(rel)

    return 0


# ---------------------------------------------------------------------------
# Subcommand: write-manifest, write-migration-plan, legacy rename helpers
# ---------------------------------------------------------------------------


def cmd_write_manifest(args: list[str]) -> int:
    src_dir = Path(args[0]).resolve()
    dest_dir = Path(args[1]).resolve()
    existing_source = Path(args[2]).resolve()
    destination = Path(args[3]).resolve()
    requested = dedup_preserve_order([m for m in args[4].split(",") if m])
    with_advanced = args[5] == "true"
    with_legacy = args[6] == "true"
    validator_bundle_managed = args[7] == "true"
    new_feature_managed = args[8] == "true"
    export_tasks_managed = args[9] == "true"
    preset_provided = args[10] == "true"
    preset_name = args[11]
    with_skills = args[12] == "true"
    skipped_user_skills = {p for p in args[13].split("|") if p}

    # Determine managed_adapter_models strictly among requested adapter-backed runtimes
    managed_adapters: list[str] = []
    for model in requested:
        cfg = RUNTIME_REGISTRY[model]
        adapter = cfg["adapter"]
        src_adapter = cfg["source_adapter"]
        if adapter is None or src_adapter is None:
            continue
        dest_hash = sha256_nofollow(dest_dir, str(adapter))
        src_hash = sha256_nofollow(src_dir, str(src_adapter))
        if dest_hash is not None and src_hash is not None and dest_hash == src_hash:
            managed_adapters.append(model)

    # Determine managed_skill_list across deduplicated active skill trees
    managed_skill_list: list[str] = []
    if with_skills:
        for tree in active_skill_trees_for_models(requested):
            for slug in SDD_SKILL_SLUGS:
                rel = f"{tree}/skills/{slug}/SKILL.md"
                if rel in skipped_user_skills:
                    continue
                dest_hash = sha256_nofollow(dest_dir, rel)
                src_hash = sha256_nofollow(src_dir, f"skills/{slug}/SKILL.md")
                if dest_hash is not None and src_hash is not None and dest_hash == src_hash:
                    managed_skill_list.append(rel)
    managed_skill_set = set(managed_skill_list)

    data = json.loads(read_regular_text_nofollow(src_dir, "template-manifest.json"))
    existing = json.loads(read_regular_text_nofollow(existing_source.parent, existing_source.name))

    installer_keys = {
        "template",
        "version",
        "skills_enabled",
        "managed_paths",
        "profiles",
        "requested_models",
        "selected_models",
        "managed_adapter_models",
    }
    for key, value in existing.items():
        if key not in installer_keys:
            data[key] = value
    data["skills_enabled"] = with_skills
    if preset_provided:
        data["default_preset"] = preset_name

    existing_profiles = existing.get("profiles", {})
    for name, profile in existing_profiles.items():
        if name not in REQUIRED_PROFILES:
            data["profiles"][name] = profile
    for path in existing_profiles.get("core", []):
        if path not in data["profiles"]["core"] and path not in ADAPTER_TO_RUNTIME and path not in ALL_SKILL_PATHS:
            data["profiles"]["core"].append(path)
    for path in existing.get("managed_paths", []):
        if path not in data["managed_paths"] and path not in ADAPTER_TO_RUNTIME and path not in ALL_SKILL_PATHS:
            data["managed_paths"].append(path)

    data["requested_models"] = requested
    data["selected_models"] = requested
    data["managed_adapter_models"] = managed_adapters

    managed_profiles = existing.get("managed_profiles", ["core"])
    if not isinstance(managed_profiles, list) or any(p not in REQUIRED_PROFILES for p in managed_profiles):
        raise ValueError("existing manifest has invalid managed_profiles")
    mp_set = set(managed_profiles)
    mp_set.add("core")
    if with_advanced:
        mp_set.add("--with-advanced-docs")
    if with_legacy:
        mp_set.add("--with-legacy-agents")
    data["managed_profiles"] = [p for p in REQUIRED_PROFILES if p in mp_set]

    def keep_core_path(path: str) -> bool:
        return (path not in ADAPTER_TO_RUNTIME or ADAPTER_TO_RUNTIME[path] in managed_adapters) and (
            path not in ALL_SKILL_PATHS or (with_skills and path in managed_skill_set)
        )

    data["managed_paths"] = [p for p in data["managed_paths"] if keep_core_path(p)]
    data["profiles"]["core"] = [p for p in data["profiles"]["core"] if keep_core_path(p)]

    for adapter, model in ADAPTER_TO_RUNTIME.items():
        if model in managed_adapters:
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
        data["managed_paths"] = [p for p in data["managed_paths"] if p not in validator_paths]
        data["profiles"]["core"] = [p for p in data["profiles"]["core"] if p not in validator_paths]
    if not new_feature_managed:
        data["managed_paths"] = [p for p in data["managed_paths"] if p != "tools/new-feature.py"]
        data["profiles"]["core"] = [p for p in data["profiles"]["core"] if p != "tools/new-feature.py"]
    if not export_tasks_managed:
        data["managed_paths"] = [p for p in data["managed_paths"] if p != "tools/export-tasks.py"]
        data["profiles"]["core"] = [p for p in data["profiles"]["core"] if p != "tools/export-tasks.py"]

    destination.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return 0


def cmd_write_migration_plan(args: list[str]) -> int:
    events_path, output_path, destination = map(Path, args[:3])
    destination = destination.resolve()
    if not output_path.resolve().is_relative_to(destination):
        raise ValueError("migration plan output escapes the destination root")
    relative_parent = output_path.resolve().parent.relative_to(destination)
    current = destination
    for part in relative_parent.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("migration plan parent must not be a symlink")
    if output_path.is_symlink():
        raise ValueError("migration plan output must not be a symlink")

    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    if events_path.exists():
        for line in events_path.read_text(encoding="utf-8").splitlines():
            if not line:
                continue
            kind, path, detail = line.split("\t", 2)
            groups[kind].append({"path": path, "detail": detail})

    payload = {
        "schema_version": 1,
        "mode": "dry-run-update",
        "destination": str(destination),
        "backup_directory_pattern": str(destination / ".ai-template-backup.XXXXXX"),
        "rollback": "After a real update, copy the desired file from the reported backup directory; see RECOVERY.md and CREATED_FILES.txt in that directory.",
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
            "# AI Template Migration Plan",
            "",
            "- Mode: `--dry-run --update`",
            f"- Destination: `{destination}`",
            f"- Planned backup directory: `{payload['backup_directory_pattern']}`",
            "- Rollback: after a real update, use `RECOVERY.md` (and `CREATED_FILES.txt`) in the reported backup directory to restore or clean up files.",
            "",
        ]
        for title, key in [
            ("Will replace", "will_replace"),
            ("Will install", "will_install"),
            ("Will preserve", "will_preserve"),
            ("Manual action", "manual_action"),
            ("Blocked", "blocked"),
            ("Migrations", "migrations"),
        ]:
            lines.extend([f"## {title}", ""])
            entries = payload[key]
            lines.extend([f"- `{entry['path']}` — {entry['detail']}" for entry in entries] or ["- None."])
            lines.append("")
        output_path.write_text("\n".join(lines), encoding="utf-8")
    return 0


def cmd_check_legacy_rename(args: list[str]) -> int:
    dest_dir = Path(args[0]).resolve()
    legacy_path = args[1]
    try:
        manifest = json.loads(read_regular_text_nofollow(dest_dir, "template-manifest.json"))
        version = manifest.get("version")
        paths = [*manifest.get("managed_paths", []), *manifest.get("profiles", {}).get("core", [])]
    except Exception:
        return 1
    affected_versions = {"0.4.0", "0.4.1", "0.4.2"}
    is_managed = any(isinstance(p, str) and (p == legacy_path or legacy_path.startswith(p + "/")) for p in paths)
    return 0 if version in affected_versions and is_managed else 1


def cmd_verify_sha256(args: list[str]) -> int:
    dest_dir = Path(args[0]).resolve()
    rel_path = args[1]
    expected = set(args[2].split(","))
    digest = sha256_nofollow(dest_dir, rel_path)
    return 0 if digest is not None and digest in expected else 1


COMMANDS = {
    "validate-source-manifest": cmd_validate_source_manifest,
    "load-profile-paths": cmd_load_profile_paths,
    "source-version": cmd_source_version,
    "doctor-source": cmd_doctor_source,
    "doctor-manifest": cmd_doctor_manifest,
    "doctor-links": cmd_doctor_links,
    "doctor-spec-readiness": cmd_doctor_spec_readiness,
    "select-update-models": cmd_select_update_models,
    "prepare-manifest-models": cmd_prepare_manifest_models,
    "prepare-ownership": cmd_prepare_ownership,
    "write-manifest": cmd_write_manifest,
    "write-migration-plan": cmd_write_migration_plan,
    "check-legacy-rename": cmd_check_legacy_rename,
    "verify-sha256": cmd_verify_sha256,
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(f"Usage: installer_lib.py <{'|'.join(COMMANDS)}> ...", file=sys.stderr)
        return 2
    cmd = COMMANDS[argv[0]]
    try:
        return cmd(argv[1:])
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
