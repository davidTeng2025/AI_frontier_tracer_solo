#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

export CONFIG_PATH="$SCRIPT_DIR/config.test.json"
export DB_PATH="$SKILL_ROOT/assets/data.test.db"
cd "$SCRIPT_DIR"
python main.py
