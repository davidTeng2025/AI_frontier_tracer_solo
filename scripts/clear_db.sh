#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DB_PATH_DEFAULT="$SKILL_ROOT/assets/data.db"
DB_PATH_ARG="${1:-$DB_PATH_DEFAULT}"

cd "$SCRIPT_DIR"
python clear_db_data.py --db "$DB_PATH_ARG"
