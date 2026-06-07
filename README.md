<p align="center">
  <img src="./assets/github-cover.png" alt="NailMind cover" width="100%" />
</p>

# NailMind

**甲感 NailMind：AI 原生美甲试戴与智能运营系统。**

[用户端预览](http://123.207.77.38:3001/) · [运营端预览](http://123.207.77.38:3001/admin/) · [部署说明](./DEPLOYMENT.md)

甲感 NailMind 是一个面向美甲消费与经营场景的 AI 双端产品：用户端帮助消费者完成美甲试戴、款式筛选、偏好沉淀与智能推荐；运营端帮助商家/运营团队识别趋势信号、管理款式、跟进预约并生成可执行的运营建议。

产品的核心不是单次图片生成，而是把“用户试戴与选择行为”转化为“运营决策信号”：用户在试戴、收藏、评论、预约和对话中的行为，会回流到运营侧，辅助趋势判断、冷门款修复和后续推荐优化。

> GitHub 可以展示仓库、README、图片资产和静态文档，但不能直接运行这套完整预览。NailMind 需要同时运行 Next.js 前端、FastAPI 后端和独立 AI 生成服务，因此线上体验需要部署到云服务器。

## 中文简介

- 用户端：AI 美甲试戴、预设手部档案、候选清单、多款对比、偏好画像、评论/预约、对话式选款助手。
- 运营端：趋势分析、爆款/冷门识别、款式管理、建议中心、预约跟进、运营 Agent。
- 数据闭环：试戴、收藏、候选、评论、预约和用户助手对话等行为，沉淀为运营洞察和推荐信号。

## 主要能力

- AI 试戴主链路：上传手照或使用预设手模，选择美甲款式后调用 RunningHub 工作流生成试戴结果。
- 用户决策辅助：支持候选清单、多款对比、偏好画像、模板评论、预约意向和个性化推荐。
- 小甲灵用户助手：基于用户问题和模板标签数据，进行对话式款式推荐与风格建议。
- 运营智能分析：提供趋势看板、冷门款修复、库存/款式建议、预约跟进和运营 Agent 对话能力。
- 双端联动：用户侧行为数据进入运营侧看板，帮助判断真实偏好、热门趋势和潜在转化机会。

## English Overview

**AI-native nail try-on and operations intelligence platform.**

NailMind is a dual-sided product for beauty retail scenarios: the consumer side helps users try on nail designs, compare styles, manage candidates, and get AI-powered recommendations; the operations side helps teams read trend signals, manage designs, follow appointments, and generate actionable operation suggestions.

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

## 技术架构 / Architecture

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

## 仓库说明 / Repository Notes

- `nailmind/` 是可运行产品代码。
- `02_产品规划/`、`03_架构规划/`、`04_迭代路线/` 保留产品规划、信息架构、系统架构和阶段路线。
- 本地日志、数据库、生成结果图、私有工作流痕迹和敏感密钥均已排除。
- 仓库保留了一组本地样例款式封面与手部样张，用于演示和开发。

## 快速启动 / Quick Start

### 1. 安装依赖

前端：

```bash
cd nailmind/frontend
npm install
```

后端：

```bash
cd nailmind/backend
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

AI 服务：

```bash
cd nailmind/ai-service
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

### 2. 配置环境变量

本地或服务器至少准备这些环境变量：

- `RUNNINGHUB_API_KEY`：AI 试戴工作流调用。
- `DEEPSEEK_API_KEY`：用户助手与运营 Agent。
- `SECRET_KEY`：后端登录态签名。

不要提交真实密钥。请使用系统环境变量、服务器密钥管理或被 `.gitignore` 排除的 `.env` 文件。

### 3. 启动本地预览

```powershell
.\nailmind\scripts\start-local.ps1 -FrontendPort 3133 -BackendPort 8004 -AiPort 8003
```

默认本地访问地址：

- 用户端：`http://127.0.0.1:3133`
- 运营端：`http://127.0.0.1:3133/admin/assistant`
- 后端健康检查：`http://127.0.0.1:8004/health`

### 4. 初始化样例数据

如果本地数据库为空：

```bash
cd nailmind/backend
venv\Scripts\python.exe seed.py
venv\Scripts\python.exe generate_mock_data.py
```

## 部署预览 / Deployment

云服务器访问入口：

- 用户端：[http://123.207.77.38:3001/](http://123.207.77.38:3001/)
- 运营端：[http://123.207.77.38:3001/admin/](http://123.207.77.38:3001/admin/)

部署步骤、环境变量和验收命令见 [DEPLOYMENT.md](./DEPLOYMENT.md)。

## 验证命令 / Verification

- Frontend lint: `cd nailmind/frontend && npm run lint`
- Frontend tests: `cd nailmind/frontend && npm test`
- Frontend build: `cd nailmind/frontend && npm run build`
- Backend tests: `cd nailmind/backend && venv\Scripts\python.exe -m unittest discover -s tests -v`
- Backend compile check: `cd nailmind/backend && venv\Scripts\python.exe -m compileall app`
- AI service tests: `cd nailmind/ai-service && venv\Scripts\python.exe -m unittest discover -s tests`
- AI service compile check: `cd nailmind/ai-service && venv\Scripts\python.exe -m compileall app`

## 当前阶段 / Current Status

当前版本已经支持：

- 用户试戴与记录链路。
- 按账号隔离的候选、评论和预约数据流。
- 用户侧选款助手。
- 运营侧趋势分析与建议闭环。
- RunningHub 真实生成链路接入。

## 后续计划 / Roadmap

- 真实手机号、邮箱和第三方登录。
- HTTPS、域名绑定和生产级云端部署。
- 更细粒度的推荐算法与用户画像建模。
- 带审批控制的运营 Agent 执行闭环。
- 更自然的试戴迁移效果和多模态理解能力。

## 规划文档 / Planning Documents

- 项目总览：[00_项目总览.md](./00_项目总览.md)
- 产品规划：[02_产品规划](./02_产品规划)
- 架构规划：[03_架构规划](./03_架构规划)
- 迭代路线：[04_迭代路线](./04_迭代路线)
