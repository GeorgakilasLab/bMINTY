#!/usr/bin/env bash
set -euo pipefail

# Poll the frontend HTTP endpoint periodically and print timestamp + status code.
# Defaults:
#   INTERVAL=5   seconds between polls
#   URL=http://127.0.0.1:3000
# Usage:
#   INTERVAL=2 URL=http://localhost:3000 ./poll-frontend.sh

INTERVAL=${INTERVAL:-5}
URL=${URL:-http://127.0.0.1:3000}

echo "Polling $URL every ${INTERVAL}s. Press Ctrl-C to stop."
while true; do
  ts=$(date --iso-8601=seconds)
  status=$(curl -s -o /dev/null -w "%{http_code}" "$URL" || echo "000")
  echo "[$ts] $URL -> $status"
  sleep "$INTERVAL"
done
