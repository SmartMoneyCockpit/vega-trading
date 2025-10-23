#!/usr/bin/env bash
# Example cron job (Linux): run every 15 minutes
# crontab -e
# */15 * * * * /bin/bash /path/to/your/repo/tools/cron_example.sh

set -euo pipefail
cd "$(dirname "$0")/.."

# Activate venv if you have one
if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

python3 tools/update_home_data.py
