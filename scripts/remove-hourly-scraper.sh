#!/usr/bin/env bash
# Removes the cron job registered by register-hourly-scraper.sh
set -euo pipefail

BEGIN_MARK="# BEGIN WAGTAIL_BBC_SCRAPER"
END_MARK="# END WAGTAIL_BBC_SCRAPER"

EXISTING="$(crontab -l 2>/dev/null || true)"
if [[ -z "${EXISTING//[[:space:]]/}" ]]; then
  echo "[INFO] No crontab found. Nothing to remove."
  exit 0
fi

FILTERED="$(printf "%s\n" "$EXISTING" | sed "/^${BEGIN_MARK//\//\/}","/^${END_MARK//\//\/}/d")"
if [[ "$FILTERED" == "$EXISTING" ]]; then
  echo "[INFO] No WAGTAIL_BBC_SCRAPER block found."
  exit 0
fi

printf "%s\n" "$FILTERED" | sed '/^\s*$/d' | crontab -
echo "[OK] Removed WAGTAIL_BBC_SCRAPER cron block"
