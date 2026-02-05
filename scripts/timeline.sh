#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

DB_PATH_DEFAULT="$SKILL_ROOT/assets/data.db"
DB_PATH_ARG="${DB_PATH:-$DB_PATH_DEFAULT}"
DIMENSION="${1:-}"
shift || true

if [[ -z "$DIMENSION" ]]; then
  echo "Usage: bash scripts/timeline.sh \"维度名\" [limit] [--months N|--days N|--since YYYY-MM-DD|--until YYYY-MM-DD]"
  echo "  或:  bash scripts/timeline.sh \"维度名\" --limit N --months 6"
  echo "Tip: 先运行 list_dimensions.sh 查看可用维度"
  exit 2
fi

# 兼容旧用法：第二个参数若为纯数字则视为 --limit
EXTRA=()
if [[ -n "${1:-}" && "$1" =~ ^[0-9]+$ ]]; then
  EXTRA=(--limit "$1")
  shift || true
fi

cd "$SCRIPT_DIR"
exec python query_tech_insights.py --db "$DB_PATH_ARG" --dimension "$DIMENSION" "${EXTRA[@]}" "$@"
