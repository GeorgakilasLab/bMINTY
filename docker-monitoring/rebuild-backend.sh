#!/usr/bin/env bash
set -euo pipefail

# Rebuild and restart only the backend service
# Usage: ./rebuild-backend.sh [--no-cache]

NO_CACHE=false
if [[ "${1:-}" == "--no-cache" ]]; then
  NO_CACHE=true
fi

echo "Rebuilding backend (no-cache=$NO_CACHE)"
if [ "$NO_CACHE" = true ]; then
  docker compose build --no-cache backend
else
  docker compose build backend
fi

docker compose up -d backend

echo "Waiting for backend to start and showing last 50 log lines..."
docker compose logs --no-color --tail=50 backend
