#!/usr/bin/env bash
set -euo pipefail

# Poll the backend HTTP endpoint periodically and print timestamp + status code.
# Defaults:
#   INTERVAL=5   seconds between polls
#   URL=http://127.0.0.1:8000
# Usage:
#   INTERVAL=2 URL=http://127.0.0.1:8000 ./poll-backend.sh

INTERVAL=${INTERVAL:-5}
URL=${URL:-http://127.0.0.1:8000}

echo "Polling $URL every ${INTERVAL}s. Press Ctrl-C to stop."
while true; do
  ts=$(date --iso-8601=seconds)
  status=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
  echo "[$ts] $URL -> $status"
  sleep "$INTERVAL"
done
