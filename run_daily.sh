#!/usr/bin/env bash
# Cron wrapper: loads .env, activates the venv, runs the scraper+mailer, logs output.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

mkdir -p logs

if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

exec "$SCRIPT_DIR/.venv/bin/python" "$SCRIPT_DIR/daily_run.py" >> "$SCRIPT_DIR/logs/cron.log" 2>&1
