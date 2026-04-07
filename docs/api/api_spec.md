# RAG 评估系统 API 文档

## 概述

RAG 评估系统提供了一套完整的 API 接口，用于管理文档、测试集、评估任务等。API 遵循 RESTful 设计原则，返回 JSON 格式的数据。

## 基础信息

- 基础 URL: `http://localhost:8000/api/v1`
- 认证方式: Bearer Token
- 内容类型: `application/json`

## 认证

大多数 API 端点需要认证。认证通过在请求头中添加 `Authorization` 字段实现：

```
Authorization: Bearer {access_token}
```

## API 端点

### 认证相关

#### POST /auth/login
用户登录

**请求体:**
```json
{
  "username": "string",
  "password": "string"
}
```

**响应:**
```json
{
  "access_token": "string",
  "token_type": "string"
}
```

#### POST /auth/register
用户注册

**请求体:**
```json
{
  "username": "string",
  "email": "string",
  "password": "string"
}
```

**响应:**
```json
{
  "id": "uuid",
  "username": "string",
  "email": "string",
  "created_at": "datetime"
}
```

### 文档管理

#### GET /documents
获取文档列表

**查询参数:**
- `skip`: 跳过的记录数 (默认: 0)
- `limit`: 返回的记录数 (默认: 100)
- `status`: 文档状态过滤

**响应:**
```json
{
  "items": [
    {
      "id": "uuid",
      "filename": "string",
      "file_path": "string",
      "file_type": "string",
      "file_size": 0,
      "upload_time": "datetime",
      "status": "string"
    }
  ],
  "total": 0,
  "page": 0,
  "size": 0,
  "pages": 0
}
```

#### POST /documents/upload
上传文档

**请求:**
multipart/form-data 格式，包含 `file` 字段

**响应:**
```json
{
  "id": "uuid",
  "filename": "string",
  "file_path": "string",
  "file_type": "string",
  "file_size": 0
}
```

#### GET /documents/{document_id}
获取特定文档信息

**响应:**
```json
{
  "id": "uuid",
  "filename": "string",
  "file_path": "string",
  "file_type": "string",
  "file_size": 0,
  "upload_time": "datetime",
  "status": "string"
}
```

### 测试集管理

#### GET /testsets
获取测试集列表

**查询参数:**
- `skip`: 跳过的记录数 (默认: 0)
- `limit`: 返回的记录数 (默认: 100)
- `document_id`: 按文档ID过滤

**响应:**
```json
{
  "items": [
    {
      "id": "uuid",
      "name": "string",
      "description": "string",
      "question_count": 0,
      "document_id": "uuid",
      "create_time": "datetime"
    }
  ],
  "total": 0,
  "page": 0,
  "size": 0,
  "pages": 0
}
```

#### POST /testsets
创建测试集

**请求体:**
```json
{
  "document_id": "uuid",
  "name": "string",
  "description": "string"
}
```

**响应:**
```json
{
  "id": "uuid",
  "name": "string",
  "description": "string",
  "question_count": 0,
  "document_id": "uuid",
  "create_time": "datetime"
}
```

### 评估管理

#### POST /evaluations
运行评估

**请求体:**
```json
{
  "testset_id": "uuid",
  "evaluation_method": "ragas_official",
  "evaluation_metrics": ["string"]
}
```

**响应:**
```json
{
  "id": "uuid",
  "testset_id": "uuid",
  "status": "pending",
  "total_questions": 0
}
```

#### GET /evaluations/{evaluation_id}
获取评估结果

**响应:**
```json
{
  "id": "uuid",
  "testset_id": "uuid",
  "status": "completed",
  "overall_metrics": {},
  "evaluation_time": 0
}
```

## 错误处理

API 使用标准的 HTTP 状态码：

- `200 OK`: 请求成功
- `201 Created`: 资源创建成功
- `400 Bad Request`: 请求参数错误
- `401 Unauthorized`: 未认证
- `403 Forbidden`: 无权限访问
- `404 Not Found`: 资源不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误信息"
}
```

## 速率限制

为了防止滥用，API 实施了速率限制：

- 每分钟最多 100 个请求
- 每小时最多 1000 个请求