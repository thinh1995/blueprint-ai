#!/bin/bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"

(
    cd "$ROOT_DIR"
    python3 -B -W error::ResourceWarning -m unittest tests.test_contracts tests.test_docs_and_tools
)

echo "PASS: documentation guardrail validation"
