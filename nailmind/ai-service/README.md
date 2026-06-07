# NailMind AI 服务

## 技术栈
- FastAPI + Python 3.12
- PyTorch / Transformers / Diffusers (可选，视模型选择)
- Pillow / NumPy

## 核心能力
1. 手部检测与分割
2. 美甲款式迁移（试戴生成）
3. 风格标签理解

## 目录结构
```
ai-service/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置
│   ├── models/              # AI 模型加载与推理
│   ├── routers/             # API 路由
│   └── utils/               # 图像处理工具
└── models/                  # 预训练模型存放
```

## 启动命令
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```
