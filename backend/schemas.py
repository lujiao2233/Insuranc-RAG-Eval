from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid

# 枚举类型定义
class UserRole(str, Enum):
    admin = "admin"
    user = "user"

class DocumentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    processing = "processing"

class QuestionType(str, Enum):
    factual = "factual"
    reasoning = "reasoning"
    creative = "creative"

class EvaluationMethod(str, Enum):
    ragas_official = "ragas_official"
    deepeval = "deepeval"

class EvaluationStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

# 用户相关模型
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[str] = Field(None, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    full_name: Optional[str] = None
    is_active: Optional[bool] = None

class User(UserBase):
    id: uuid.UUID
    role: UserRole = UserRole.user
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    is_active: bool = True

    model_config = {"from_attributes": True}

# 文档相关模型
class DocumentBase(BaseModel):
    filename: str
    file_path: str
    file_type: str
    file_size: int
    page_count: Optional[int] = None
    status: str = "active"
    is_analyzed: bool = False
    doc_metadata: Optional[Dict[str, Any]] = Field(default=None, alias="doc_metadata_col")
    outline: Optional[Any] = None
    category: str = "未分类"
    product_entities: Optional[List[str]] = None

    model_config = {"populate_by_name": True}

class DocumentChunkBase(BaseModel):
    document_id: uuid.UUID
    content: str
    md5: str
    sequence_number: int
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    entities: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="chunk_metadata")

class DocumentChunk(DocumentChunkBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

class DocumentCreate(DocumentBase):
    pass

class DocumentUpdate(BaseModel):
    status: Optional[DocumentStatus] = None
    is_analyzed: Optional[bool] = None
    doc_metadata: Optional[Dict[str, Any]] = None
    outline: Optional[Any] = None  # 可以是 Dict 或 List
    category: Optional[str] = None

class Document(DocumentBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    upload_time: datetime
    analyzed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

# 测试集相关模型
class TestSetBase(BaseModel):
    name: str
    description: Optional[str] = None
    question_count: int = 0
    question_types: Optional[Dict[str, float]] = None
    generation_method: str = "qwen_model"
    file_path: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="testset_metadata")

    model_config = {"populate_by_name": True}

class TestSetCreate(TestSetBase):
    document_id: uuid.UUID

class TestSetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    question_count: Optional[int] = None
    question_types: Optional[Dict[str, float]] = None
    metadata: Optional[Dict[str, Any]] = None

class TestSet(TestSetBase):
    id: uuid.UUID
    document_id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    create_time: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

# 问题相关模型
class QuestionBase(BaseModel):
    question: str
    question_type: QuestionType
    category_major: Optional[str] = None
    category_minor: Optional[str] = None
    expected_answer: Optional[str] = None
    answer: Optional[str] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default=None, alias="question_metadata")

    model_config = {"populate_by_name": True}

class QuestionCreate(QuestionBase):
    testset_id: uuid.UUID

class QuestionUpdate(BaseModel):
    question: Optional[str] = None
    question_type: Optional[QuestionType] = None
    category_major: Optional[str] = None
    category_minor: Optional[str] = None
    expected_answer: Optional[str] = None
    answer: Optional[str] = None
    context: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class Question(QuestionBase):
    id: uuid.UUID
    testset_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

# 评估相关模型
class EvaluationBase(BaseModel):
    testset_id: Optional[uuid.UUID] = None
    evaluation_method: EvaluationMethod = EvaluationMethod.ragas_official
    total_questions: int = 0
    evaluated_questions: int = 0
    evaluation_time: Optional[float] = None
    evaluation_metrics: Optional[List[str]] = None
    overall_metrics: Optional[Dict[str, Any]] = None
    eval_config: Optional[Dict[str, Any]] = None
    status: EvaluationStatus = EvaluationStatus.pending
    error_message: Optional[str] = None

class EvaluationCreate(BaseModel):
    testset_id: uuid.UUID
    evaluation_method: Optional[str] = "ragas_official"
    evaluation_metrics: Optional[List[str]] = None
    eval_config: Optional[Dict[str, Any]] = None

class EvaluationUpdate(BaseModel):
    status: Optional[EvaluationStatus] = None
    error_message: Optional[str] = None
    evaluation_time: Optional[float] = None
    overall_metrics: Optional[Dict[str, float]] = None

class Evaluation(EvaluationBase):
    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    timestamp: datetime
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# 评估结果相关模型
class EvaluationResultBase(BaseModel):
    question_text: str
    expected_answer: Optional[str] = None
    generated_answer: Optional[str] = None
    context: Optional[str] = None
    metrics: Optional[Dict[str, float]] = None
    reasons: Optional[Dict[str, str]] = None

class EvaluationResultCreate(EvaluationResultBase):
    evaluation_id: uuid.UUID
    question_id: Optional[uuid.UUID] = None

class EvaluationResultUpdate(BaseModel):
    metrics: Optional[Dict[str, float]] = None
    reasons: Optional[Dict[str, str]] = None
    generated_answer: Optional[str] = None

class EvaluationResult(EvaluationResultBase):
    id: uuid.UUID
    evaluation_id: uuid.UUID
    question_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}

# 配置相关模型
class ConfigurationBase(BaseModel):
    config_key: str
    config_value: Optional[str] = None
    description: Optional[str] = Field(default=None, alias="config_description")

    model_config = {"populate_by_name": True}

class ConfigurationCreate(ConfigurationBase):
    pass

class ConfigurationUpdate(BaseModel):
    config_value: Optional[str] = None
    description: Optional[str] = None

class Configuration(ConfigurationBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "populate_by_name": True}

# 响应模型
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    user_id: Optional[uuid.UUID] = None
    role: Optional[UserRole] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    size: int
    pages: int