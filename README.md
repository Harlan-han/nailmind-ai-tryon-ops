<p align="center">
  <img src="./assets/github-cover.png" alt="NailMind cover" width="100%" />
</p>

# NailMind

**AI-native nail try-on and operations intelligence platform.**

[Consumer App](http://123.207.77.38:3001/) · [Operations Console](http://123.207.77.38:3001/admin/) · [Deployment Guide](./DEPLOYMENT.md)

NailMind is a dual-sided product for beauty retail scenarios: the consumer side helps users try on nail designs, compare styles, manage candidates, and get AI-powered recommendations; the operations side helps teams read trend signals, manage designs, follow appointments, and generate actionable operation suggestions.

> GitHub can display the repository, README, assets, and GitHub Pages static documentation. It cannot directly run this full-stack preview because NailMind needs a Next.js app, a FastAPI backend, and a separate AI generation service.

## Product Scope

- Consumer experience: AI nail try-on, saved hand profiles, candidate list, design comparison, preference profile, and a conversational style assistant.
- Operations console: trend analytics, design management, cold-style repair, suggestion center, appointment follow-up, and operations Agent.
- Core loop: user try-on behavior becomes trend signals; operations decisions then feed back into recommendations and conversion.

## Key Capabilities

- AI try-on flow: upload a hand photo or use preset hand profiles, choose a design, and generate results through a RunningHub workflow.
- Decision support: candidates, comparisons, preference profile, personalized recommendations, comments, and appointments.
- Consumer assistant: chat-based design discovery that recommends nail styles from template metadata and stores preference signals.
- Operations intelligence: insights dashboard, unpopular-design recovery, suggestion center, appointment follow-up, and Agent-assisted operations.
- Closed-loop data: try-ons, favorites, candidates, comments, appointments, and assistant conversations flow back into operational analysis.

## Architecture

```text
repo/
├── nailmind/
│   ├── frontend/      # Next.js 16 + TypeScript + Tailwind CSS
│   ├── backend/       # FastAPI + SQLAlchemy
│   ├── ai-service/    # FastAPI + RunningHub / OpenCV / MediaPipe
│   ├── docker/        # Docker Compose scaffold
│   └── scripts/       # Local startup, acceptance, and helper scripts
├── 01_项目规范/
├── 02_产品规划/
├── 03_架构规划/
└── 04_迭代路线/
```

## Repository Notes

- `nailmind/` contains the runnable product code.
- `02_产品规划/`, `03_架构规划/`, and `04_迭代路线/` keep product planning, information architecture, system architecture, and roadmap notes.
- Local logs, databases, generated try-on results, private workflow traces, and sensitive credentials are excluded from this public repository.
- A small set of local design covers and hand-profile samples is included for demo and development.

## Quick Start

### 1. Install Dependencies

Frontend:

```bash
cd nailmind/frontend
npm install
```

Backend:

```bash
cd nailmind/backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

AI service:

```bash
cd nailmind/ai-service
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. Configure Environment Variables

Prepare these variables locally or on the server:

- `RUNNINGHUB_API_KEY`: AI try-on workflow provider.
- `DEEPSEEK_API_KEY`: consumer assistant and operations Agent.
- `SECRET_KEY`: backend auth signing key.

Do not commit real keys. Use OS-level environment variables, a server-side secret manager, or ignored `.env` files.

### 3. Start Local Preview

```powershell
.\nailmind\scripts\start-local.ps1 -FrontendPort 3133 -BackendPort 8004 -AiPort 8003
```

Default local URLs:

- Consumer app: `http://127.0.0.1:3133`
- Operations console: `http://127.0.0.1:3133/admin/assistant`
- Backend health check: `http://127.0.0.1:8004/health`

### 4. Seed Sample Data

If the local database is empty:

```bash
cd nailmind/backend
venv\Scripts\python.exe seed.py
venv\Scripts\python.exe generate_mock_data.py
```

## Deployment

Preview links:

- Consumer app: [http://123.207.77.38:3001/](http://123.207.77.38:3001/)
- Operations console: [http://123.207.77.38:3001/admin/](http://123.207.77.38:3001/admin/)

For setup details, environment variables, and verification commands, see [DEPLOYMENT.md](./DEPLOYMENT.md).

## Verification

- Frontend lint: `cd nailmind/frontend && npm run lint`
- Frontend tests: `cd nailmind/frontend && npm test`
- Frontend build: `cd nailmind/frontend && npm run build`
- Backend tests: `cd nailmind/backend && venv\Scripts\python.exe -m unittest discover -s tests -v`
- Backend compile check: `cd nailmind/backend && venv\Scripts\python.exe -m compileall app`
- AI service tests: `cd nailmind/ai-service && venv\Scripts\python.exe -m unittest discover -s tests`
- AI service compile check: `cd nailmind/ai-service && venv\Scripts\python.exe -m compileall app`

## Current Status

The current version supports:

- Consumer try-on and records flow.
- Account-scoped candidates, comments, and appointment data.
- Consumer-side style assistant.
- Operations trend and suggestion loop.
- Real RunningHub generation workflow integration.

## Roadmap

- Real phone, email, and third-party authentication.
- HTTPS, domain binding, and production-grade cloud deployment.
- More granular recommendation algorithms and preference modeling.
- Operations Agent execution loop with safer approval controls.
- More natural try-on transfer quality and multimodal understanding.

## Planning Documents

- Project overview: [00_项目总览.md](./00_项目总览.md)
- Product planning: [02_产品规划](./02_产品规划)
- Architecture planning: [03_架构规划](./03_架构规划)
- Roadmap: [04_迭代路线](./04_迭代路线)
