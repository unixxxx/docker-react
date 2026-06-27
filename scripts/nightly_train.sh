#!/usr/bin/env bash
# Nightly training job — the data-flywheel step.
# Retrains the model from logged sessions and atomically replaces the artifact.
# Schedule with cron, e.g.:  0 3 * * *  /path/to/scripts/nightly_train.sh
set -euo pipefail

cd "$(dirname "$0")/.."

# Use the project virtualenv if present.
if [ -d ".venv" ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
fi

echo "[$(date -u +%FT%TZ)] Retraining Fishing Copilot model from logged sessions..."
python -m ml.train

echo "[$(date -u +%FT%TZ)] Done. The backend hot-reloads the new artifact automatically."
