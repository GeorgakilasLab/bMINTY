#!/usr/bin/env bash
set -euo pipefail

# Rebuild and restart only the frontend service
# Usage: ./rebuild-frontend.sh [--no-cache]

NO_CACHE=false
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE=true
fi

echo "Rebuilding frontend (no-cache=$NO_CACHE)"
if [ "$NO_CACHE" = true ]; then
  docker compose build --no-cache frontend
else
  docker compose build frontend
fi

docker compose up -d frontend

echo "Waiting for frontend to start and showing last 50 log lines..."
docker compose logs --no-color --tail=50 frontend
