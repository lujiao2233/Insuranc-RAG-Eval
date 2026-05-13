# RAG 评估系统

面向保险行业的 RAG (Retrieval-Augmented Generation) 系统评估平台，提供文档解析、测试集生成、多维度评估和报告展示的全流程支持。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109.0-green.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.4-brightgreen.svg)](https://vuejs.org/)
[![License](https://img.shields.io/badge/License-MIT-gray.svg)](LICENSE)

---

## 目录

- [项目概述](#项目概述)
- [核心功能](#核心功能)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [API 接口](#api-接口)
- [前端路由](#前端路由)
- [项目结构](#项目结构)
- [数据库模型](#数据库模型)
- [测试](#测试)
- [部署指南](#部署指南)
- [贡献规范](#贡献规范)
- [许可证](#许可证)

---

## 项目概述

RAG 评估系统是一个专为保险行业设计的质量评估平台，能够对检索增强生成系统进行全方位的测试与评估。系统支持从文档上传、测试集自动生成到多维度评估的完整工作流，帮助团队持续提升 RAG 系统的检索准确性和回答质量。

### 核心价值

- **全流程自动化**: 从文档上传到评估报告生成，端到端自动化
- **多模态文档支持**: 支持 PDF、Word、Excel、PPT、文本等多种格式
- **智能测试集生成**: 基于 LLM 自动生成事实型、推理型、创意型测试问题
- **多维度评估**: 支持 Ragas、DeepEval 等主流评估框架
- **单轮与多轮对话**: 支持单轮问答和带上下文依赖的多轮对话评估
- **可视化报告**: 通过仪表盘和图表直观展示评估结果

---

## 核心功能

| 功能模块 | 说明 |
|----------|------|
| **文档管理** | 支持上传 PDF/DOCX/XLSX/PPTX/TXT/Excel 等格式，自动解析文本、提取元数据、生成大纲树 |
| **语义分片** | 基于语义边界对文档进行智能分片，支持重叠策略，确保上下文完整性 |
| **测试集生成** | 自动从文档生成事实型、推理型、创意型问题，支持单轮和多轮对话模式 |
| **评估执行** | 支持 Ragas 官方指标、DeepEval 对话评估，后台异步执行并实时反馈进度 |
| **报告中心** | 自动生成评估报告，展示各维度得分、排名和趋势分析 |
| **用量统计** | 记录 LLM API 调用量、Token 消耗和费用，支持按模块分析 |
| **系统配置** | 管理 API 密钥、评估指标、超时参数等系统配置 |
| **用户认证** | JWT 身份认证，支持注册、登录、权限管理 |

---

## 技术栈

### 后端

| 组件 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | 0.109.0 |
| ASGI 服务器 | Uvicorn | 0.27.0 |
| ORM | SQLAlchemy | 2.0.25 |
| 数据校验 | Pydantic | 2.8.2 |
| 数据库 | MySQL (PyMySQL) | 1.1.0 |
| 认证 | python-jose + bcrypt | - |
| LLM 集成 | DashScope / LangChain | 1.15.0 / 0.1.x |
| 评估框架 | Ragas / DeepEval | 0.1.2 / 3.9.7 |
| 文档处理 | python-docx / python-pptx / openpyxl / PyPDF2 / PyMuPDF / Camelot | - |

### 前端

| 组件 | 技术 | 版本 |
|------|------|------|
| 框架 | Vue 3 + Composition API | 3.4+ |
| 语言 | TypeScript | 5.0+ |
| 构建工具 | Vite | 5.0+ |
| 状态管理 | Pinia | 2.1+ |
| 路由 | Vue Router | 4.2+ |
| UI 框架 | Element Plus | 2.4+ |
| 图表 | ECharts | 5.4+ |
| HTTP 客户端 | Axios | 1.6+ |
| 样式 | SCSS + Tailwind CSS | - |

### 基础设施

| 组件 | 版本 |
|------|------|
| 数据库 | MySQL 5.7+ |
| Python | 3.10+ |
| Node.js | 18+ |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端应用 (Vue 3)                          │
├─────────────────────────────────────────────────────────────────┤
│  Views → Components → Composables → Stores → API Layer           │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP (Axios)
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     后端服务 (FastAPI)                           │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ──────────┐  ┌──────────┐         │
│  │  Auth    │  │ Documents│  │ TestSets │  │ Evaluations│       │
│  │ Router   │  │ Router   │  │ Router   │  │ Router   │         │
│  └────┬─────┘  └─────────┘  └────┬─────┘  └────┬─────         │
│       └─────────────┼─────────────┼──────────────────────────┘  │
│                     │             │             │                 │
│  ┌──────────────────┴──────────────────────────┴──────────────┐ │
│  │                    Service Layer                            │ │
│  │  DocumentService │ LLMService │ RAGASEvaluator │ TaskManager│ │
│  └──────────────────┬─────────────┬─────────────┬──────────────┘ │
│                     │             │             │                 │
│  ┌──────────────────┴─────────────┴─────────────┴──────────────┐ │
│  │                   Data Layer                                │ │
│  │  SQLAlchemy ORM │ MySQL │ BackgroundTask Queue               │ │
│  ─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python >= 3.10
- Node.js >= 18
- MySQL >= 5.7

### 后端启动

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置数据库连接和 API 密钥

# 初始化数据库
python scripts/init_db.py

# 启动开发服务器
uvicorn main:app --reload --host 0.0.0.0 --port 8001

# 或指定端口
python main.py
```

### 前端启动

```bash
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8001 |
| API 文档 (Swagger) | http://localhost:8001/docs |
| API 文档 (ReDoc) | http://localhost:8001/redoc |

---

## 配置说明

### 后端配置

后端通过 `.env` 文件进行配置（参考 `backend/.env.example`）：

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SECRET_KEY` | JWT 签名密钥 | `your-secret-key-change-this-in-production` |
| `DATABASE_URL` | MySQL 连接字符串 | `mysql+pymysql://root:password@localhost:3306/rag_evaluation` |
| `QWEN_API_KEY` | 阿里云百炼 API 密钥 | 无（不配置则使用模拟服务） |
| `UPLOAD_DIR` | 文件上传目录 | `data/uploads` |
| `MAX_FILE_SIZE` | 最大文件大小 (字节) | `52428800` (50MB) |

### 前端配置

前端通过环境变量配置（参考 `frontend/.env.development`）：

| 变量 | 说明 |
|------|------|
| `VITE_API_BASE_URL` | 后端 API 基础路径 |
| `VITE_APP_TITLE` | 应用标题 |

### 支持的文档格式

| 格式 | 扩展名 |
|------|--------|
| PDF | `.pdf` |
| Word | `.docx`, `.doc` |
| Excel | `.xlsx`, `.xls` |
| PowerPoint | `.pptx` |
| 文本 | `.txt`, `.md` |

---

## API 接口

后端提供 RESTful API，所有接口均以 `/api/v1/` 为前缀。

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/auth/register` | 用户注册 |
| `POST` | `/api/v1/auth/login` | 用户登录 |
| `POST` | `/api/v1/auth/logout` | 用户登出 |

### 文档接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/documents/` | 获取文档列表 |
| `POST` | `/api/v1/documents/upload` | 上传单个文档 |
| `POST` | `/api/v1/documents/upload-batch` | 批量上传文档 |
| `GET` | `/api/v1/documents/:id` | 获取文档详情 |
| `GET` | `/api/v1/documents/:id/download` | 下载文档 |
| `DELETE` | `/api/v1/documents/:id` | 删除文档 |
| `POST` | `/api/v1/documents/:id/analyze` | 触发 LLM 分析 |

### 测试集接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/testsets/` | 获取测试集列表 |
| `POST` | `/api/v1/testsets/` | 创建测试集 |
| `POST` | `/api/v1/testsets/:id/generate` | 自动生成问题 |
| `GET` | `/api/v1/testsets/:id` | 获取测试集详情 |
| `DELETE` | `/api/v1/testsets/:id` | 删除测试集 |
| `POST` | `/api/v1/testsets/:id/execute` | 执行测试集 |

### 评估接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/evaluations/` | 获取评估记录列表 |
| `POST` | `/api/v1/evaluations/` | 创建评估任务 |
| `GET` | `/api/v1/evaluations/:id` | 获取评估详情 |
| `DELETE` | `/api/v1/evaluations/:id` | 删除评估记录 |

### 报告接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/reports/` | 获取报告列表 |
| `GET` | `/api/v1/reports/:id` | 获取报告详情 |

### 配置接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/config/` | 获取配置列表 |
| `POST` | `/api/v1/config/` | 创建/更新配置 |
| `DELETE` | `/api/v1/config/:id` | 删除配置 |

### 用量统计接口

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET` | `/api/v1/usage/tokens` | 获取 Token 消耗统计 |
| `GET` | `/api/v1/usage/cost` | 获取费用统计 |
| `GET` | `/api/v1/usage/models` | 获取按模型分类的用量 |

---

## 前端路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/login` | LoginView | 登录页 |
| `/register` | RegisterView | 注册页 |
| `/dashboard` | DashboardView | 仪表盘 |
| `/usage` | UsageView | 用量统计 |
| `/documents` | DocumentsView | 文档列表 |
| `/documents/:id` | DocumentDetailView | 文档详情 |
| `/testsets` | TestSetsView | 测试集列表 |
| `/testsets/new` | TestSetGenerationView | 新建测试集 |
| `/testsets/:id` | TestSetDetailView | 测试集详情 |
| `/testsets/:id/execute` | TestSetExecutionView | 执行测试集 |
| `/evaluations` | EvaluationsView | 评估列表 |
| `/evaluations/new` | EvaluationCreateView | 新建评估 |
| `/evaluations/:id` | EvaluationDetailView | 评估详情 |
| `/reports` | ReportsView | 报告中心 |
| `/config` | ConfigView | 系统配置 |

---

## 项目结构

```
new/
── frontend/                          # Vue 3 前端应用
│   ├── src/
│   │   ├── api/                       # API 请求封装 (Axios)
│   │   ├── assets/styles/             # 全局样式 (SCSS + Tailwind)
│   │   ├── components/
│   │   │   ├── business/              # 业务组件
│   │   │   └── layout/                # 布局组件
│   │   ├── composables/               # 组合式函数 (Hooks)
│   │   ├── router/                    # 路由配置
│   │   ├── stores/                    # Pinia 状态管理
│   │   ├── types/                     # TypeScript 类型定义
│   │   ├── utils/                     # 工具函数
│   │   └── views/                     # 页面视图
│   ├── .env.development               # 开发环境变量
│   ├── .env.production                # 生产环境变量
│   ├── package.json                   # 前端依赖
│   └── vite.config.ts                 # Vite 构建配置
│
├── backend/                           # FastAPI 后端服务
│   ├── api/
│   │   ├── routers/                   # 路由模块
│   │   │   ├── auth.py                # 认证路由
│   │   │   ├── documents.py           # 文档路由
│   │   │   ├── testsets.py            # 测试集路由
│   │   │   ├── evaluations.py         # 评估路由
│   │   │   ├── reports.py             # 报告路由
│   │   │   ├── analysis.py            # 分析路由
│   │   │   ├── config.py              # 配置路由
│   │   │   ── usage.py               # 用量路由
│   │   └── dependencies.py            # 依赖注入
│   ├── config/                        # 配置模块
│   │   ├── database.py                # 数据库连接
│   │   ├── settings.py                # 应用设置
│   │   └── category_hierarchy.json    # 文档分类体系
│   ├── models/                        # SQLAlchemy ORM 模型
│   │   └── database.py                # 所有表定义
│   ├── services/                      # 业务逻辑层
│   │   ├── document_service.py        # 文档服务
│   │   ├── document_processor.py      # 文档处理器
│   │   ├── llm_service.py             # LLM 调用服务
│   │   ├── ragas_evaluator.py         # Ragas 评估器
│   │   ├── question_generator.py      # 问题生成器
│   │   ├── task_manager.py            # 后台任务管理器
│   │   └── ...
│   ├── scripts/                       # 工具脚本
│   │   ├── init_db.py                 # 一键建表
│   │   ├── verify_env.py              # 环境验证
│   │   └── ...
│   ├── tests/
│   │   ├── unit/                      # 单元测试
│   │   ├── integration/               # 集成测试
│   │   ├── e2e/                       # 端到端测试
│   │   └── fixtures/                  # 测试数据
│   ├── utils/                         # 工具函数
│   ├── migrations/                    # 数据库迁移目录 (历史参考)
│   ├── main.py                        # 应用入口
│   ├── schemas.py                     # Pydantic 模型
│   ├── requirements.txt               # 后端依赖
│   └── .env.example                   # 配置模板
│
└── docs/                              # 项目文档
    ├── api/                           # API 文档
    ├── architecture/                  # 架构设计
    ├── deployment/                    # 部署指南
    ├── development/                   # 开发指南
    └── reference/                     # 参考资源
```

---

## 数据库模型

系统使用 MySQL 数据库，通过 SQLAlchemy ORM 管理 14 个数据表：

| 表名 | 说明 |
|------|------|
| `users` | 用户账户信息 |
| `documents` | 上传的文档记录 |
| `document_chunks` | 文档分片内容（含全文索引） |
| `testsets` | 测试集定义 |
| `questions` | 单轮测试问题 |
| `conversation_test_cases` | 多轮对话测试用例 |
| `conversation_turns` | 多轮对话轮次定义 |
| `evaluations` | 评估任务记录 |
| `evaluation_results` | 评估结果明细 |
| `conversation_executions` | 对话执行记录 |
| `conversation_turn_results` | 对话轮次执行结果 |
| `configurations` | 系统配置 |
| `background_tasks` | 后台任务队列 |
| `api_usage_logs` | LLM API 调用日志 |

一键建表：
```bash
cd backend
python scripts/init_db.py
```

---

## 测试

### 运行测试

```bash
cd backend

# 运行所有测试
pytest tests/

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 运行端到端测试
pytest tests/e2e/

# 带覆盖率报告
pytest --cov=services tests/
```

### 测试分类

| 类型 | 目录 | 说明 |
|------|------|------|
| 单元测试 | `tests/unit/` | 独立测试单个服务/函数 |
| 集成测试 | `tests/integration/` | 测试 API 端点和模块集成 |
| 端到端测试 | `tests/e2e/` | 测试完整业务流程 |

---

## 部署指南

### 生产环境部署

```bash
# 1. 安装依赖
cd backend
pip install -r requirements.txt

# 2. 配置生产环境变量
cp .env.example .env
# 编辑 .env，设置生产数据库连接、SECRET_KEY 等

# 3. 初始化数据库
python scripts/init_db.py

# 4. 启动服务（使用进程管理器）
uvicorn main:app --host 0.0.0.0 --port 8001 --workers 4

# 或使用 gunicorn + uvicorn
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8001
```

### 前端构建

```bash
cd frontend

# 构建生产版本
npm run build

# 生成的文件位于 dist/ 目录，可通过 Nginx 部署
```

### 安全建议

1. 修改 `SECRET_KEY` 为强随机字符串
2. 使用 HTTPS 部署后端 API
3. 限制 `BACKEND_CORS_ORIGINS` 仅允许前端域名
4. 定期轮换 API 密钥
5. 限制文件上传类型和大小

---

## 贡献规范

### 分支管理

- `main`: 生产分支
- `develop`: 开发分支
- `feature/*`: 功能分支
- `fix/*`: 修复分支

### 代码风格

**后端**: 遵循 PEP 8，使用 `ruff` 进行代码检查
**前端**: 使用 ESLint + Prettier，提交时自动格式化

### 提交信息

```
类型(模块): 简短描述

详细描述（可选）

相关 issue: #123
```

类型: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## 许可证

MIT License

---

## 联系方式

如有问题或建议，请通过 Issue 提交。
