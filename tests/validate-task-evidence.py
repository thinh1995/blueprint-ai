#!/usr/bin/env python3

import datetime as dt
import argparse
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
parser = argparse.ArgumentParser()
parser.add_argument("--evidence-dir", default="docs/current/00 - Onboarding/task-evidence")
parser.add_argument("--require-completed", action="store_true")
args = parser.parse_args()
EVIDENCE_DIR = ROOT / args.evidence_dir
if not EVIDENCE_DIR.is_dir() and args.require_completed:
    raise ValueError(f"evidence directory does not exist: {EVIDENCE_DIR}")


def frontmatter(text: str, path: Path) -> dict[str, str]:
    match = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    data = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def require(data: dict[str, str], keys: list[str], path: Path) -> None:
    missing = [key for key in keys if not data.get(key)]
    if missing:
        raise ValueError(f"{path}: missing completed-task fields: {', '.join(missing)}")


completed_records = 0
for path in (EVIDENCE_DIR.glob("*.md") if EVIDENCE_DIR.is_dir() else []):
    if path.name.startswith("_"):
        continue
    text = path.read_text()
    data = frontmatter(text, path)
    if data.get("status") != "completed":
        continue
    completed_records += 1
    require(data, ["task_id", "recorded_at", "recorded_by", "source_revision", "completed_at", "reviewer", "environment", "output_artifact_sha256", "output_artifact_path"], path)
    if not re.search(r"\| AC-[^|]+\|\s*[^|\s].*\|\s*[^|\s].*\|\s*[^|\s].*\|", text):
        raise ValueError(f"{path}: completed task needs a non-empty AC validation row")
    artifact = ROOT / data["output_artifact_path"]
    if not artifact.is_file():
        raise ValueError(f"{path}: output artifact does not exist: {artifact}")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    if digest != data["output_artifact_sha256"].lower():
        raise ValueError(f"{path}: output artifact checksum does not match")

if args.require_completed and completed_records == 0:
    raise ValueError("no completed task evidence record found")

inventory = ROOT / "docs/current/02 - Architecture/Generated Reference Inventory.md"
data = frontmatter(inventory.read_text(), inventory)
if data.get("verified") == "true":
    require(data, ["generated_at", "source_revision", "generation_command", "artifact_path", "scope", "verified_at", "verified_by", "verification_method", "verification_evidence", "artifact_checksum", "valid_until"], inventory)
    try:
        expiry = dt.date.fromisoformat(data["valid_until"][:10])
    except ValueError as exc:
        raise ValueError(f"{inventory}: valid_until must start with ISO date") from exc
    if expiry < dt.date.today():
        raise ValueError(f"{inventory}: verified inventory is expired")

print("PASS: task evidence and inventory validation")
