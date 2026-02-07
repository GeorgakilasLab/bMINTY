# bMINTY - Setup Guide

bMINTY is a locally deployed web application, offering structured management of data produced by the analysis of high-throughput sequencing experiments.

**GitHub Patges:**
You can learn more about bMinty in our [GitHub Page][https://georgakilaslab.github.io/bMINTY].

**Repo layout:**
- Backend (Django API): [`bmintyApi`](bmintyApi)
- Frontend (React app): [`bmintyReact`](bmintyReact)
- Default ports: backend `8000`, frontend `3000`

---

## Quick Start with Docker

**Prerequisites:** Docker

The simplest way to run bMINTY is with Docker. **No need to install Python, npm, or any other dependencies on your host system** - Docker handles everything automatically.

```bash
# Clone the repository
git clone https://github.com/GeorgakilasLab/bMINTY
cd bMinty

# Start both frontend and backend with one command
docker compose up --build
```

That's it! By running the commands above you will:
- Build both frontend and backend containers
- Automatically run `npm install` for the React frontend
- Automatically run `pip install` for the Django backend
- Install all dependencies and start both services

**Access the application:**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000

**To stop:**
```bash
docker compose down
```

### Changing Docker Ports

If the default ports (3000, 8000) are already in use on your system, you can easily change them:

**Option 1: Using environment variables (Quick)**
```bash
# Use different ports for this session
FRONTEND_PORT=3001 BACKEND_PORT=8001 docker compose up --build
```

**Option 2: Using .env file (Persistent)**
```bash
# Create a .env file from the example
cp .env.example .env

# Edit .env and change the ports:
# FRONTEND_PORT=3001
# BACKEND_PORT=8001

# Then run with rebuild
docker compose up --build
```

---



## Docker Configuration Details

The Docker setup uses [`docker-compose.yml`](docker-compose.yml) to orchestrate both services:

- **Backend container:**
  - Built from [`bmintyApi/Dockerfile`](bmintyApi/Dockerfile)
  - Uses Python 3.11 with Django and all dependencies
  - Default port: `8000` (configurable via `BACKEND_PORT`)

- **Frontend container:**
  - Built from [`bmintyReact/Dockerfile`](bmintyReact/Dockerfile)
  - Uses React and npm packages
  - Default port: `3000` (configurable via `FRONTEND_PORT`)

**Port Configuration:**
- Ports are configurable via environment variables (see [.env.example](.env.example))
- Default values: `FRONTEND_PORT=3000`, `BACKEND_PORT=8000`

---

## Quick Reference

### Docker Commands
```bash
# Start with default ports (3000, 8000)
docker compose up

# Start with custom ports (requires --build for API base change)
FRONTEND_PORT=3001 BACKEND_PORT=8001 docker compose up --build

# Stop services
docker compose down

# Rebuild after code changes
docker compose up --build

# View logs
docker compose logs -f
```

### Configuration Files
- [docker-compose.yml](docker-compose.yml) - Docker orchestration configuration
- [.env.example](.env.example) - Example environment variables (copy to `.env` to customize)
- [bmintyReact/src/config.js](bmintyReact/src/config.js) - Frontend API configuration
