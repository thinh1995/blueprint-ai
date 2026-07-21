#!/usr/bin/env python3
"""Validate the versioned runtime-delegation evidence schema fixture."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/runtime-delegation-evidence.json"
REQUIRED_FIELDS = {
    "schema_version",
    "fixture",
    "runtime",
    "runtime_version",
    "host",
    "captured_at",
    "coordinator",
    "mode",
    "capability_check",
    "delegation_evidence",
    "roles",
}
REQUIRED_ROLES = {"source-discovery", "architecture-api", "product-ba", "qa-traceability"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    require(data.get("fixture") is True, "fixture must be explicitly marked as non-live evidence")
    require(data.get("schema_version") == 1, "unsupported schema version")
    require(REQUIRED_FIELDS.issubset(data), f"missing fields: {sorted(REQUIRED_FIELDS - set(data))}")
    valid_modes = {"delegated", "sequential-fallback", "blocked-before-run"}
    require(data["mode"] in valid_modes, "invalid delegation mode")
    for record in (ROOT / "docs/internal/runtime-delegation-evidence").glob("*.md"):
        frontmatter = record.read_text(encoding="utf-8").split("---", 2)[1]
        if "status: skipped" in frontmatter:
            require("mode: blocked-before-run" in frontmatter, f"{record.relative_to(ROOT)}: skipped record must use blocked-before-run")
    require(all(isinstance(data[field], str) and data[field] for field in REQUIRED_FIELDS - {"roles", "fixture", "schema_version"}), "empty evidence field")
    require(isinstance(data["roles"], list) and REQUIRED_ROLES.issubset(data["roles"]), "fixture does not cover every required role")
    print("PASS: runtime delegation evidence schema fixture")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
