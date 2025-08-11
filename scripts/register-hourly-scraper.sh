#!/usr/bin/env bash
# Registers a cron job to run `manage.py fetch_bbc_news` every hour.
# Use on Linux/macOS or WSL. Idempotent: it replaces previous block between markers.
set -euo pipefail

# --- Config (can be overridden via env/flags) ---
PYTHON_BIN="${PYTHON_BIN:-python3}"
SCHEDULE="${SCHEDULE:-0 * * * *}"  # default: at minute 0 every hour

# Resolve project root (one level up from this script)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
MANAGE="$PROJECT_ROOT/manage.py"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/cron-fetch.log"

# Flags: --python <bin> --schedule "CRON_EXPR"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --python)
      PYTHON_BIN="$2"; shift 2;;
    --schedule)
      SCHEDULE="$2"; shift 2;;
    *) echo "Unknown arg: $1"; exit 2;;
  esac
done

mkdir -p "$LOG_DIR"

BEGIN_MARK="# BEGIN WAGTAIL_BBC_SCRAPER"
END_MARK="# END WAGTAIL_BBC_SCRAPER"
CRON_LINE="$SCHEDULE cd '$PROJECT_ROOT' && $PYTHON_BIN '$MANAGE' scrape_news >> '$LOG_FILE' 2>&1"

# Read existing crontab (if any)
EXISTING="$(crontab -l 2>/dev/null || true)"
# Remove old block if present
FILTERED="$(printf "%s\n" "$EXISTING" | sed "/^${BEGIN_MARK//\//\/}","/^${END_MARK//\//\/}/d")"

# Compose new crontab
{
  printf "%s\n" "$FILTERED" | sed '/^\s*$/d'
  echo "$BEGIN_MARK"
  echo "$CRON_LINE"
  echo "$END_MARK"
} | crontab -

echo "[OK] Registered hourly cron for scrape_news using $PYTHON_BIN"
echo "Schedule: $SCHEDULE"
echo "Logs: $LOG_FILE"
