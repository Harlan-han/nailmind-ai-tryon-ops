# Local Service Scripts

## Start local preview

Run from the project root:

```powershell
.\nailmind\scripts\start-local.ps1
```

Useful variants:

```powershell
.\nailmind\scripts\start-local.ps1 -BackendOnly
.\nailmind\scripts\start-local.ps1 -AiOnly
.\nailmind\scripts\start-local.ps1 -FrontendOnly
.\nailmind\scripts\start-local.ps1 -BackendOnly -BackendPort 8014
.\nailmind\scripts\start-local.ps1 -FrontendOnly -FrontendPort 3010
```

The script does not kill existing processes. If port `8004`, `8003`, or `3000` is already in use, stop the old process first, then run the script again.

On this machine the original backend venv may point to a removed Python 3.12 install. `start-local.ps1` falls back to the Codex bundled Python runtime and the existing project `venv\Lib\site-packages` when that happens. Temporary launcher files are written under `nailmind/scripts/.runtime/`.

When custom backend or AI ports are passed, `start-local.ps1` also wires the service URLs. Backend gets `AI_SERVICE_URL=http://localhost:<AiPort>`, AI service gets `BACKEND_WEBHOOK_URL=http://localhost:<BackendPort>/api/tryon/webhook/result` plus `BACKEND_ORIGIN=http://localhost:<BackendPort>`, and frontend gets `NEXT_PUBLIC_BACKEND_ORIGIN`, `NEXT_PUBLIC_API_BASE_URL`, and `NEXT_PUBLIC_AI_SERVICE_ORIGIN` for same-origin rewrites. Explicit environment variables still take precedence.

## Current runtime requirements

- Backend: Python 3.12, `nailmind/backend/venv`, FastAPI/Uvicorn dependencies from `requirements.txt`.
- AI service: Python 3.12, `nailmind/ai-service/venv`, dependencies from `requirements.txt`.
- Frontend: Node + npm, `nailmind/frontend`, `npm run dev`.

To point a frontend instance at non-default services, set these variables before starting Next.js:

```powershell
$env:NEXT_PUBLIC_BACKEND_ORIGIN = "http://localhost:8014"
$env:NEXT_PUBLIC_API_BASE_URL = "http://localhost:8014/api"
$env:NEXT_PUBLIC_AI_SERVICE_ORIGIN = "http://localhost:8013"
```

## Operations Agent environment variables

Set these in your local shell before starting backend if needed:

```powershell
$env:DEEPSEEK_API_KEY = "<your-key>"
$env:FEISHU_BOT_WEBHOOK_URL = "<optional-feishu-bot-webhook>"
$env:OPERATIONS_AGENT_EXTERNAL_TOKEN = "<optional-external-webhook-token>"
```

Do not commit secrets to the repository.

To save local API keys safely to the current Windows user environment without writing them to the repo, run:

```powershell
.\nailmind\scripts\set-local-secrets.ps1 -DeepSeekOnly
```

The script uses hidden input and only stores the value in Windows user environment variables. Restart the backend after setting secrets. `start-local.ps1` will inherit `DEEPSEEK_*`, `RUNNINGHUB_*`, Feishu webhook variables, and `BACKEND_WEBHOOK_SECRET`/`AI_WEBHOOK_SECRET` from the current process, user, or machine environment without printing them.

## Check local runtime

After restarting services, run:

```powershell
.\nailmind\scripts\check-local.ps1
```

Useful variants:

```powershell
.\nailmind\scripts\check-local.ps1 -Backend http://localhost:8014
.\nailmind\scripts\check-local.ps1 -InProcessBackend
```

`-InProcessBackend` starts the latest FastAPI app with an in-process Uvicorn server on a temporary port and calls it through real HTTP requests. Use it when `8004` is still occupied by an old backend process but you need to verify current backend route registration, auth, Agent capability APIs, and the external webhook.

It checks:

- frontend `http://localhost:3000`
- backend health `http://localhost:8004/health`
- login code API `/api/auth/request-code`
- operations Agent capability API `/api/operations/assistant/capabilities`
- operations Agent status API `/api/operations/assistant/status`
- external Agent webhook `/api/operations/assistant/webhook`

If auth, capabilities, or webhook return `404`, port `8004` is still serving old backend code.

## Run end-to-end acceptance

After all three local services are running, use the acceptance script to verify the real business loop:

```powershell
.\nailmind\scripts\acceptance-e2e.ps1
```

It calls the running services through real HTTP requests and verifies:

- consumer phone-code login
- hand photo record creation
- try-on creation and AI-result webhook completion
- favorite, candidate, and booking intent creation
- operator phone-code login
- operations overview, today workbench, booking follow-up queue, merchant activity, and user-facing trending signals
- AI operations insights endpoint
- merchant booking status update from pending to contacted, including removal from pending workbench action cards
- consumer tokens cannot access operator overview

The script intentionally creates one new local acceptance user, operator, try-on, favorite, candidate, and booking signal per run.
