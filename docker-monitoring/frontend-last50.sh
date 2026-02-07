#!/usr/bin/env bash
set -euo pipefail

# Show the last 50 lines of the frontend service logs (docker compose)
# Usage: ./frontend-last50.sh

exec docker compose logs --no-color --tail=50 frontend
