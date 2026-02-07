# Docker monitoring helpers

This folder contains small shell helpers to monitor the frontend and backend services locally (using `docker compose`).

Files:

- `frontend-last50.sh` — prints the last 50 lines of the `frontend` service logs.
- `backend-last50.sh` — prints the last 50 lines of the `backend` service logs.
- `poll-frontend.sh` — continuously polls the frontend HTTP endpoint and prints timestamp + HTTP status code. Defaults to `http://127.0.0.1:3000`.
- `poll-backend.sh` — continuously polls the backend HTTP endpoint and prints timestamp + HTTP status code. Defaults to `http://127.0.0.1:8000`.

Usage examples:

```bash
# show last 50 lines of frontend logs
./docker-monitoring/frontend-last50.sh

# show last 50 lines of backend logs
./docker-monitoring/backend-last50.sh

# poll frontend every 5s (default)
./docker-monitoring/poll-frontend.sh

# poll backend every 2s
INTERVAL=2 ./docker-monitoring/poll-backend.sh
```

Notes:

- Scripts assume `docker compose` is available and that the compose file defines services named `frontend` and `backend`.
- The pollers use `curl` from the host. If your services are behind a reverse proxy or on different ports, set the `URL` environment variable when running the script.
