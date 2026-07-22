#!/usr/bin/env python3
"""Validate the non-live Antigravity CLI conformance-fixture contract."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests/fixtures/antigravity-conformance.json"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def main() -> None:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    required = {
        "schema_version", "fixture", "runtime", "runtime_version", "launcher",
        "workspace_context_files", "adapter_path", "agent_manager_command", "scenarios",
        "live_runtime_evidence",
    }
    require(required.issubset(data), f"missing fields: {sorted(required - set(data))}")
    require(data["schema_version"] == 1, "unsupported schema version")
    require(data["fixture"] is True and data["live_runtime_evidence"] is False, "fixture must not claim live runtime evidence")
    require(data["runtime"] == "antigravity-cli", "fixture runtime must be antigravity-cli")
    require(data["launcher"] == "agy", "fixture launcher must be agy")
    require(data["adapter_path"] == "GEMINI.md", "Antigravity compatibility adapter must remain GEMINI.md")
    require(set(data["workspace_context_files"]) == {"AGENTS.md", "GEMINI.md"}, "fixture must cover both workspace context files")
    require(data["agent_manager_command"] == "/agents", "fixture must cover the agent manager")
    require(set(data["scenarios"]) == {"workspace-rules-discovery", "permission-approval", "parallel-subagent-management"}, "fixture scenarios changed")
    print("PASS: Antigravity CLI conformance fixture")


if __name__ == "__main__":
    try:
        main()
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
