# 保险行业RAG 评估系统

## 项目概述

这是一个现代化的 RAG (Retrieval-Augmented Generation) 评估系统，采用前后端分离架构，使用 Vue 3 作为前端框架，FastAPI 作为后端框架。

## 项目结构

```
new/
├── frontend/                 # Vue 3 前端应用
│   ├── public/              # 静态资源
│   ├── src/                 # 源代码
│   │   ├── assets/          # 静态资源
│   │   ├── components/      # Vue 组件
│   │   ├── views/           # 页面视图
│   │   ├── router/          # 路由配置
│   │   ├── store/           # 状态管理
│   │   └── utils/           # 工具函数
│   ├── package.json         # 前端依赖
│   └── vite.config.js       # 构建配置
├── backend/                 # FastAPI 后端服务
│   ├── main.py             # 应用入口
│   ├── api/                # API 路由
│   │   ├── routers/        # 路由定义
│   │   ├── middleware/     # 中间件
│   │   └── dependencies/   # 依赖项
│   ├── models/             # 数据模型
│   ├── schemas/            # Pydantic 模型
│   ├── services/           # 业务逻辑
│   ├── utils/              # 工具函数
│   ├── config/             # 配置文件
│   ├── migrations/         # 数据库迁移
│   ├── tests/              # 测试文件
│   └── requirements.txt    # 后端依赖
├── shared/                 # 前后端共享资源
│   ├── interfaces/         # 接口定义
│   ├── types/              # 类型定义
│   └── utils/              # 共享工具函数
└── docs/                   # 项目文档
    ├── architecture/       # 架构文档
    ├── api/               # API 文档
    ├── deployment/        # 部署文档
    └── development/       # 开发文档
```

## 快速开始

### 前端启动

```bash
cd frontend
npm install
npm run dev
```

### 后端启动

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

## 技术栈

- 前端: Vue 3, TypeScript, Vite, Element Plus
- 后端: Python, FastAPI, SQLAlchemy, PostgreSQL
- 数据库: PostgreSQL (推荐) 或 SQLite
- 测试: Pytest, Jest
- 部署: Docker, Nginx
