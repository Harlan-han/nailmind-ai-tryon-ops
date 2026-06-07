# NailMind App

这里是 NailMind 的可运行应用目录，包含用户端、运营端、后端服务与 AI 服务。

## 目录结构

```text
nailmind/
├── frontend/      # Next.js 16 + TypeScript + Tailwind CSS
├── backend/       # FastAPI + SQLAlchemy
├── ai-service/    # FastAPI + RunningHub / OpenCV / MediaPipe
├── docker/        # Docker Compose scaffold
└── scripts/       # 启动、验收、辅助脚本
```

## 本地运行

### 快速启动

```powershell
.\scripts\start-local.ps1 -FrontendPort 3133 -BackendPort 8004 -AiPort 8003
```

### 手动启动

后端：

```bash
cd backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8004
```

AI 服务：

```bash
cd ai-service
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8003
```

前端：

```bash
cd frontend
npm install
npm run dev -- -p 3133
```

## 必要环境变量

- `RUNNINGHUB_API_KEY`
- `DEEPSEEK_API_KEY`
- `SECRET_KEY`

## 主要页面

- 用户端首页：`/`
- 上传手照：`/upload`
- 试戴结果：`/tryon`
- 记录页：`/records`
- 用户助手：`/assistant`
- 运营端：`/admin`
- 运营 Agent：`/admin/assistant`

## 验证命令

- `cd frontend && npm run lint`
- `cd frontend && npm test`
- `cd frontend && npm run build`
- `cd backend && venv\Scripts\python.exe -m unittest discover -s tests -v`
- `cd ai-service && venv\Scripts\python.exe -m unittest discover -s tests`

## 说明

- 仓库已保留一组可直接演示的本地样例款式封面和官方手模
- 本地数据库、日志、生成结果图和私有调试文件不会进入公开仓库
- 更完整的产品背景和路线图见仓库根目录 README 与规划文档
