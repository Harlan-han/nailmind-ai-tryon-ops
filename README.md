# NailMind

NailMind 是一个面向美甲消费与经营场景的 AI 原生双端产品：一端帮助用户完成美甲试戴、筛选与决策，另一端帮助运营团队识别趋势、管理款式并生成可执行建议。

## 项目定位

- C 端：AI 美甲试戴、候选清单、多款对比、偏好画像、对话式选款助手
- B 端：趋势分析、爆款/冷门识别、款式管理、建议中心、运营 Agent
- 核心闭环：用户试戴行为沉淀为趋势信号，运营调整再反哺用户推荐与转化

## 主要能力

- AI 试戴主链路：上传手照或使用预设手模，选择款式，调用 RunningHub 工作流生成结果
- 决策辅助：候选清单、多款对比、偏好画像、个性化推荐
- 用户侧助手：对话式推荐美甲风格与款式，并记录偏好信号
- 运营侧洞察：趋势看板、冷门修复、建议中心、预约跟进、运营 Agent
- 双端数据联动：试戴、收藏、候选、评论、预约等行为回流到运营分析侧

## 技术架构

```text
repo/
├── nailmind/
│   ├── frontend/      # Next.js 16 + TypeScript + Tailwind CSS
│   ├── backend/       # FastAPI + SQLAlchemy
│   ├── ai-service/    # FastAPI + RunningHub / OpenCV / MediaPipe
│   ├── docker/        # Docker Compose scaffold
│   └── scripts/       # 本地启动、验收、辅助脚本
├── 01_项目规范/
├── 02_产品规划/
├── 03_架构规划/
└── 04_迭代路线/
```

## 仓库内容说明

- `nailmind/` 是可运行代码
- `02_产品规划/`、`03_架构规划/`、`04_迭代路线/` 保留了产品规划、信息架构与阶段路线
- 仓库已剔除本地日志、数据库、生成结果图、私有工作流痕迹与敏感密钥
- 仓库内保留了一组本地样例款式封面与官方手模，用于开箱演示

## 快速启动

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

至少准备这些环境变量：

- `RUNNINGHUB_API_KEY`：AI 试戴工作流调用
- `DEEPSEEK_API_KEY`：用户助手与运营 Agent
- `SECRET_KEY`：后端登录态签名

### 3. 启动本地预览

推荐直接使用仓库脚本：

```powershell
.\nailmind\scripts\start-local.ps1 -FrontendPort 3133 -BackendPort 8004 -AiPort 8003
```

启动后默认访问：

- 用户端：`http://127.0.0.1:3133`
- 运营端：`http://127.0.0.1:3133/admin/assistant`
- 后端健康检查：`http://127.0.0.1:8004/health`

### 4. 初始化样例数据

如果本地数据库为空，可执行：

```bash
cd nailmind/backend
venv\Scripts\python.exe seed.py
venv\Scripts\python.exe generate_mock_data.py
```

## 验证命令

- 前端 lint：`cd nailmind/frontend && npm run lint`
- 前端测试：`cd nailmind/frontend && npm test`
- 前端构建：`cd nailmind/frontend && npm run build`
- 后端单测：`cd nailmind/backend && venv\Scripts\python.exe -m unittest discover -s tests -v`
- AI 服务单测：`cd nailmind/ai-service && venv\Scripts\python.exe -m unittest discover -s tests`

## 当前阶段

当前版本已经跑通：

- 用户试戴与记录链路
- 账号隔离下的候选/评论/预约数据流
- 用户侧选款助手
- 运营侧趋势与建议闭环
- RunningHub 真实生成链路接入

## 后续计划

- 真实手机号 / 邮箱 / 第三方登录
- 更完整的云端部署与 HTTPS 化
- 更细粒度的推荐算法与用户画像建模
- 运营 Agent 的自动执行闭环
- 更自然的试戴迁移效果和多模态理解能力

## 文档索引

- 项目总览：[00_项目总览.md](./00_项目总览.md)
- 产品规划：[02_产品规划](./02_产品规划)
- 架构规划：[03_架构规划](./03_架构规划)
- 迭代路线：[04_迭代路线](./04_迭代路线)
