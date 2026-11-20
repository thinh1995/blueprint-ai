#!/usr/bin/env python3
"""Portable validation installed with a downstream project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# The installed validator must not leave generated files in a project merely
# because CI or a developer ran a documentation check.
sys.dont_write_bytecode = True

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    import _sdd_core  # noqa: E402
except ImportError as exc:
    print(
        f"FAIL: validate-docs.py requires tools/_sdd_core.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if user-owned): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

if getattr(_sdd_core, "SDD_CORE_API_VERSION", 0) < 1 or not hasattr(_sdd_core, "require"):
    print(
        f"FAIL: validate-docs.py requires an up-to-date tools/_sdd_core.py (SDD_CORE_API_VERSION >= 1) in {SCRIPT_DIR} "
        "(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if tools/_sdd_core.py is user-owned)",
        file=sys.stderr,
    )
    sys.exit(1)

REQUIRED_DV_SYMBOLS = (
    "compute_contract_sha256",
    "require",
    "validate_clarify_gate",
    "validate_feature_specs",
    "validate_links",
    "validate_mermaid",
    "validate_owned_paths_diff",
)

try:
    import docs_validation as _dv  # noqa: E402
except ImportError as exc:
    print(
        f"FAIL: validate-docs.py requires docs_validation.py in {SCRIPT_DIR} "
        f"(run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if docs_validation.py is user-owned): {exc}",
        file=sys.stderr,
    )
    sys.exit(1)

missing_dv = [sym for sym in REQUIRED_DV_SYMBOLS if not hasattr(_dv, sym)]
if missing_dv:
    print(
        f"FAIL: validate-docs.py requires an up-to-date docs_validation.py in {SCRIPT_DIR} "
        f"(missing: {', '.join(missing_dv)}; run 'setup.sh --update', or 'setup.sh --update --force' / manual sync if docs_validation.py is user-owned)",
        file=sys.stderr,
    )
    sys.exit(1)

require = _dv.require
validate_clarify_gate = _dv.validate_clarify_gate
validate_feature_specs = _dv.validate_feature_specs
validate_links = _dv.validate_links
validate_mermaid = _dv.validate_mermaid
validate_owned_paths_diff = _dv.validate_owned_paths_diff

DEFAULT_ROOT = SCRIPT_DIR.parent


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate downstream project documentation links, Mermaid diagrams, Clarify Gate, and Cross-Spec traceability."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Project root containing docs/current (defaults to parent directory of tools/).",
    )
    parser.add_argument(
        "--require-tasks",
        action="store_true",
        help="Require 4. Tasks.md (or 1. Mini Spec.md) and 'self'+contract_sha256 (or 40-hex SHA) source_revision on every approved feature folder.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce strict source_revision ('self' + 64-hex contract_sha256, or 40-character lowercase Git SHA) on approved specs.",
    )
    parser.add_argument(
        "--check-owned-paths",
        action="store_true",
        help="Verify Git changes match declared Owned paths of the active approved feature spec.",
    )
    parser.add_argument(
        "--feature",
        help="Target active feature folder or slug (requires --check-owned-paths).",
    )
    parser.add_argument(
        "--base",
        help="Explicit Git base revision for --check-owned-paths range diff (requires --check-owned-paths).",
    )
    parser.add_argument(
        "--task",
        help="Validate working-tree/staged changes strictly against one T-xx task row with zero exemptions (requires --check-owned-paths).",
    )
    parser.add_argument(
        "--strict-owned-paths",
        action="store_true",
        help="Disable all default doc/changelog/evidence exemptions under --check-owned-paths.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not args.check_owned_paths and (
        args.feature is not None
        or args.base is not None
        or args.task is not None
        or args.strict_owned_paths
    ):
        raise ValueError(
            "--feature, --base, --task, and --strict-owned-paths require --check-owned-paths"
        )
    require(not args.root.is_symlink(), f"project root cannot be a symlink: {args.root}")
    root = args.root.resolve()
    docs = root / "docs"
    current = docs / "current"
    if not current.is_dir():
        raise ValueError("docs/current is missing")
    files = sorted(current.rglob("*.md"))
    for p in files:
        require(not p.is_symlink(), f"{p.relative_to(root)}: Markdown document must not be a symlink")
    if not files:
        raise ValueError("docs/current has no Markdown documents")

    strict = args.strict or args.require_tasks
    validate_links(root, docs, files)
    validate_mermaid(root, files)
    clarify_warnings = validate_clarify_gate(root, files, strict=strict)
    spec_warnings = validate_feature_specs(
        root,
        current / "05 - Product Features",
        require_tasks=args.require_tasks,
        strict=strict,
    )
    owned_warnings: list[str] = []
    if args.check_owned_paths:
        owned_warnings = validate_owned_paths_diff(
            root,
            feature_arg=args.feature,
            base_rev=args.base,
            task_id=args.task,
            strict_owned_paths=args.strict_owned_paths,
        )
    for warning in dict.fromkeys(clarify_warnings + spec_warnings + owned_warnings):
        print(f"WARN: {warning}", file=sys.stderr)
    print("PASS: downstream documentation links and Mermaid structure")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
