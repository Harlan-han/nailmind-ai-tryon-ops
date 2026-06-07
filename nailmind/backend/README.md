# NailMind 后端服务

## 技术栈
- FastAPI + Python 3.12
- SQLAlchemy + Alembic
- PostgreSQL
- Redis

## 目录结构
```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── models/              # SQLAlchemy 模型
│   ├── routers/             # API 路由
│   ├── services/            # 业务逻辑
│   └── utils/               # 工具函数
├── alembic/                 # 数据库迁移
├── tests/                   # 测试
└── requirements.txt         # 依赖列表
```

## 启动命令
```bash
# 开发模式
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API 文档
启动后访问: http://localhost:8000/docs
