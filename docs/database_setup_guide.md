# RAG评估系统 - MySQL数据库环境配置指南

## 概述

本文档详细说明了如何为RAG评估系统配置MySQL数据库环境。该系统从前端Streamlit应用迁移到Vue + FastAPI架构，并将数据存储从JSON文件迁移到MySQL数据库。

## 配置摘要

### 1. 依赖更新
- **数据库驱动**: PyMySQL, mysql-connector-python
- **ORM**: SQLAlchemy 2.0.23
- **连接池**: 内置SQLAlchemy连接池管理

### 2. 数据库配置
- **数据库类型**: MySQL 8.0+
- **连接URL**: `mysql+pymysql://root:password@localhost:3306/rag_evaluation`
- **字符集**: UTF8MB4
- **连接池**: 自动管理，支持连接复用

### 3. 数据表结构
系统包含以下核心数据表：

#### users (用户表)
- id: CHAR(36) - 用户唯一标识符
- username: VARCHAR(50) - 用户名（唯一）
- email: VARCHAR(100) - 邮箱（唯一）
- password_hash: VARCHAR(255) - 密码哈希
- role: VARCHAR(20) - 用户角色
- created_at: DATETIME - 创建时间
- is_active: BOOLEAN - 是否激活

#### documents (文档表)
- id: CHAR(36) - 文档唯一标识符
- user_id: CHAR(36) - 所属用户ID（外键）
- filename: VARCHAR(255) - 文件名
- file_path: VARCHAR(500) - 文件路径
- file_type: VARCHAR(10) - 文件类型
- file_size: BIGINT - 文件大小
- upload_time: DATETIME - 上传时间
- doc_metadata_col: JSON - 文档元数据
- status: VARCHAR(20) - 状态

#### testsets (测试集表)
- id: CHAR(36) - 测试集唯一标识符
- document_id: CHAR(36) - 关联文档ID（外键）
- name: VARCHAR(255) - 测试集名称
- question_count: INT - 问题数量
- generation_method: VARCHAR(50) - 生成方法
- testset_metadata: JSON - 测试集元数据

#### questions (问题表)
- id: CHAR(36) - 问题唯一标识符
- testset_id: CHAR(36) - 关联测试集ID（外键）
- question: TEXT - 问题内容
- question_type: VARCHAR(50) - 问题类型
- category_major: VARCHAR(100) - 问题大类
- category_minor: VARCHAR(100) - 问题小类
- question_metadata: JSON - 问题元数据

#### evaluations (评估表)
- id: CHAR(36) - 评估唯一标识符
- testset_id: CHAR(36) - 关联测试集ID（外键）
- evaluation_method: VARCHAR(50) - 评估方法
- total_questions: INT - 总问题数
- overall_metrics: JSON - 总体指标
- eval_config: JSON - 评估配置

#### evaluation_results (评估结果表)
- id: CHAR(36) - 结果唯一标识符
- evaluation_id: CHAR(36) - 关联评估ID（外键）
- question_id: CHAR(36) - 关联问题ID（外键）
- question_text: TEXT - 问题文本
- metrics: JSON - 评估指标

#### configurations (配置表)
- id: CHAR(36) - 配置唯一标识符
- user_id: CHAR(36) - 关联用户ID（外键）
- config_key: VARCHAR(100) - 配置键
- config_value: TEXT - 配置值
- config_description: TEXT - 配置描述

## 部署步骤

### 1. 环境准备
```bash
# 安装依赖
cd d:\AIAI\AIAI\new\backend
pip install -r requirements.txt

# 确保MySQL服务正在运行
```

### 2. 数据库初始化
```sql
-- 在MySQL中创建数据库
CREATE DATABASE rag_evaluation CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### 3. 运行数据库初始化脚本
```bash
cd d:\AIAI\AIAI\new\backend
python init_db_mysql.py
```

### 4. 验证配置
```bash
python verify_env.py
```

## 配置文件说明

### .env 配置文件
```
# 数据库配置
DATABASE_URL=mysql+pymysql://root:password@localhost:3306/rag_evaluation

# API配置
API_V1_STR=/api/v1
SECRET_KEY=your-secret-key-here-change-this-to-a-random-string
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 项目配置
PROJECT_NAME=RAG Evaluation System
BACKEND_CORS_ORIGINS=http://localhost,http://localhost:3000,https://localhost,https://localhost:3000

# 评估配置
DEFAULT_EVALUATION_TIMEOUT=300
DEFAULT_MAX_WORKERS=4

# 文件上传配置
MAX_FILE_SIZE=50MB
ALLOWED_EXTENSIONS=.pdf,.docx,.xlsx
UPLOAD_DIR=data/uploads
```

## 连接池配置

数据库连接池已配置为：
- `pool_pre_ping=True`: 连接前验证连接有效性
- `pool_recycle=300`: 每5分钟回收连接
- `echo=False`: 关闭SQL日志（生产环境）

## 安全注意事项

1. **密码安全**: 生产环境中不要使用默认密码
2. **网络访问**: 限制数据库远程访问权限
3. **SSL连接**: 在生产环境中启用SSL连接
4. **定期备份**: 建立数据库定期备份机制

## 故障排除

### 常见问题
1. **连接失败**: 检查MySQL服务是否运行
2. **权限错误**: 确认数据库用户有相应权限
3. **表创建失败**: 确认数据库存在且用户有创建表权限

### 验证脚本
运行 `python verify_env.py` 检查环境配置

## 后续步骤

1. 启动后端服务: `uvicorn main:app --reload`
2. 部署前端应用
3. 配置反向代理（如Nginx）
4. 设置监控和日志系统