#!/usr/bin/env bash
set -euo pipefail

# Rebuild all services and restart them
# Usage: ./rebuild-all.sh [--no-cache]

NO_CACHE=false
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE=true
fi

echo "Rebuilding all services (no-cache=$NO_CACHE)"
if [ "$NO_CACHE" = true ]; then
  docker compose build --no-cache
else
  docker compose build
fi

docker compose up -d

echo "Showing last 50 log lines for frontend and backend..."
docker compose logs --no-color --tail=50 frontend backend || true
