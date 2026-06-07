# Deployment Guide

NailMind is not a static website. A production preview needs three running services:

- `frontend`: Next.js app, exposed to users.
- `backend`: FastAPI API service.
- `ai-service`: FastAPI generation service connected to RunningHub.

## Preview Links

- Consumer app: `http://123.207.77.38:3001/`
- Operations console: `http://123.207.77.38:3001/admin/`

If these URLs return `502 Bad Gateway`, check the frontend container/process, reverse proxy upstream, and backend health endpoints first.

## Required Environment Variables

Do not commit real secrets. Configure these on the server through OS environment variables, an ignored `.env` file, or the cloud provider's secret manager.

### Frontend

```bash
NEXT_PUBLIC_API_BASE_URL=/api
NEXT_PUBLIC_BACKEND_ORIGIN=http://backend:8000
NEXT_PUBLIC_AI_SERVICE_ORIGIN=http://ai-service:8001
```

For a direct non-proxy setup, `NEXT_PUBLIC_API_BASE_URL` can point to the public backend API URL.

### Backend

```bash
DEBUG=false
DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>
REDIS_URL=redis://<host>:6379/0
AI_SERVICE_URL=http://ai-service:8001
CORS_ORIGINS=http://123.207.77.38:3001
SECRET_KEY=<generate-a-long-random-value>
DEEPSEEK_API_KEY=<server-secret>
```

When `DEBUG=false`, the backend requires explicit `CORS_ORIGINS`, a non-default `SECRET_KEY`, and a non-SQLite production database URL.

### AI Service

```bash
BACKEND_WEBHOOK_URL=http://backend:8000/api/tryon/webhook/result
RUNNINGHUB_API_KEY=<server-secret>
RUNNINGHUB_WORKFLOW_ID=<workflow-id>
RUNNINGHUB_INSTANCE_TYPE=default
RUNNINGHUB_USE_PERSONAL_QUEUE=false
RUNNINGHUB_TIMEOUT_SECONDS=360
RUNNINGHUB_POLL_INTERVAL_SECONDS=5
```

## Docker Compose Deployment

The compose file under `nailmind/docker/docker-compose.yml` is a deployment scaffold. Before using it on a real server:

1. Replace all placeholder secrets through environment variables.
2. Use a persistent production database volume or a managed database.
3. Expose only the frontend port publicly unless backend and AI service need direct debugging access.
4. Put Nginx, Caddy, or a cloud gateway in front of the frontend if HTTPS/domain access is needed.

Typical server commands:

```bash
cd nailmind/docker
docker compose up -d --build
docker compose ps
```

Check service health:

```bash
curl http://127.0.0.1:3001/
curl http://127.0.0.1:8004/health
curl http://127.0.0.1:8003/health
```

## Manual Deployment

Frontend:

```bash
cd nailmind/frontend
npm install
npm run build
npm run start -- -p 3001
```

Backend:

```bash
cd nailmind/backend
python -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

AI service:

```bash
cd nailmind/ai-service
python -m venv venv
venv/bin/python -m pip install -r requirements.txt
venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8003
```

On Windows, replace `venv/bin/python` with `venv\Scripts\python.exe`.

## Post-deployment Checks

- The consumer homepage loads without a 500/502 response.
- The operations console loads at `/admin/`.
- `GET /health` works for backend and AI service.
- Login works without exposing operator-only routes to consumer accounts.
- The try-on flow reaches RunningHub and receives the webhook result.
- DeepSeek-backed assistant endpoints respond without showing missing-key warnings.

## GitHub Preview Note

GitHub Pages is suitable for static documentation and marketing pages. This repository's product preview is a full-stack app, so GitHub cannot directly host the runnable preview without an external deployment target.
