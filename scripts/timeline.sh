#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DB_PATH_DEFAULT="$SKILL_ROOT/assets/data.db"
DB_PATH_ARG="${DB_PATH:-$DB_PATH_DEFAULT}"
DIMENSION="${1:-}"
LIMIT="${2:-}"

if [[ -z "$DIMENSION" ]]; then
  echo "Usage: bash scripts/timeline.sh \"维度名\" [limit]"
  echo "Tip: 先运行 list_dimensions.sh 查看可用维度"
  exit 2
fi

cd "$SCRIPT_DIR"
if [[ -n "$LIMIT" ]]; then
  python query_tech_insights.py --db "$DB_PATH_ARG" --dimension "$DIMENSION" --limit "$LIMIT"
else
  python query_tech_insights.py --db "$DB_PATH_ARG" --dimension "$DIMENSION"
fi
