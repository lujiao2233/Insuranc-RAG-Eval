"""数据库模型
定义MySQL数据库的表结构
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, BigInteger, Index, Float
from sqlalchemy.dialects.mysql import CHAR
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')  # admin, user
    full_name = Column(String(100))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)

    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    testsets = relationship("TestSet", back_populates="user", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="user", cascade="all, delete-orphan")
    configurations = relationship("Configuration", back_populates="user", cascade="all, delete-orphan")

class Document(Base):
    __tablename__ = "documents"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    user_id = Column(CHAR(36), ForeignKey("users.id"), nullable=True)
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(20), nullable=False)  # pdf, docx, xlsx, pptx, txt, excel
    file_size = Column(BigInteger, nullable=False)
    page_count = Column(Integer)
    upload_time = Column(DateTime, server_default=func.now())
    status = Column(String(20), default='active')  # active, inactive, processing, analyzed, failed
    is_analyzed = Column(Boolean, default=False)  # 是否已进行LLM分析
    analyzed_at = Column(DateTime)  # 分析完成时间
    doc_metadata_col = Column(JSON)  # 存储文档元数据
    outline = Column(JSON)  # 存储文档大纲结构 (三级树)
    category = Column(String(100), default='未分类')  # 文档分类
    product_entities = Column(JSON)  # 提取的产品实体列表
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    # 不对测试集做级联删除，避免删除文档时连带删除测试集/报告
    testsets = relationship("TestSet", back_populates="document")

class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    document_id = Column(CHAR(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)  # 切片内容
    md5 = Column(String(32), index=True, nullable=False)  # 内容MD5
    sequence_number = Column(Integer, nullable=False)  # 全局序号
    start_char = Column(Integer)  # 原文中起始字符位置
    end_char = Column(Integer)  # 原文中截止字符位置
    overlap_ratio = Column(JSON)  # 与前后切片的重叠信息
    entities = Column(JSON)  # 该切片中的实体信息
    dense_vector = Column(JSON)  # 稠密向量存储 (JSON数组)
    chunk_metadata = Column(JSON)  # 切片级别的额外元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    document = relationship("Document", back_populates="chunks")

    # 建立全文索引以支持关键字搜索
    __table_args__ = (
        Index('idx_content_fulltext', content, mysql_prefix='FULLTEXT'),
    )

class TestSet(Base):
    __tablename__ = "testsets"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    # 允许文档删除后保留测试集，关联置空
    document_id = Column(CHAR(36), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    question_count = Column(Integer, default=0)
    question_types = Column(JSON)  # 存储问题类型分布
    generation_method = Column(String(50), default='qwen_model')  # qwen_model, ragas, csv_import
    create_time = Column(DateTime, server_default=func.now())
    file_path = Column(String(500))  # CSV文件路径
    testset_metadata = Column(JSON)  # 额外元数据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    document = relationship("Document", back_populates="testsets")
    user = relationship("User", back_populates="testsets")
    questions = relationship("Question", back_populates="testset", cascade="all, delete-orphan")
    evaluations = relationship("Evaluation", back_populates="testset")

class Question(Base):
    __tablename__ = "questions"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    testset_id = Column(CHAR(36), ForeignKey("testsets.id", ondelete="CASCADE"), nullable=False)
    question = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # factual, reasoning, creative
    category_major = Column(String(100))  # 问题大类
    category_minor = Column(String(100))  # 问题小类/评估维度
    expected_answer = Column(Text)  # 预期/参考答案
    answer = Column(Text)  # 模型生成的答案（评估后填充）
    context = Column(Text)  # 问题相关的上下文文本
    question_metadata = Column(JSON)  # 额外元数据（来源文档、章节信息等）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    testset = relationship("TestSet", back_populates="questions")
    results = relationship("EvaluationResult", back_populates="question", cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    testset_id = Column(CHAR(36), ForeignKey("testsets.id", ondelete="SET NULL"), nullable=True)  # 可为空，允许评估非测试集问题
    evaluation_method = Column(String(50), default='ragas_official')  # ragas_official, deepeval
    total_questions = Column(Integer, nullable=False)
    evaluated_questions = Column(Integer, nullable=False)
    evaluation_time = Column(Integer)  # 评估耗时（秒）
    timestamp = Column(DateTime, server_default=func.now())
    evaluation_metrics = Column(JSON)  # 使用的评估指标列表
    overall_metrics = Column(JSON)  # 总体指标统计
    eval_config = Column(JSON)  # 评估配置
    status = Column(String(20), default='completed')  # pending, running, completed, failed
    error_message = Column(Text)  # 错误信息（如果评估失败）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="evaluations")
    testset = relationship("TestSet", back_populates="evaluations")
    results = relationship("EvaluationResult", back_populates="evaluation", cascade="all, delete-orphan")

class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    evaluation_id = Column(CHAR(36), ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(CHAR(36), ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)  # 可为空，允许评估非测试集问题
    question_text = Column(Text, nullable=False)
    expected_answer = Column(Text)
    generated_answer = Column(Text)
    context = Column(Text)
    metrics = Column(JSON)  # 各评估指标的分数
    reasons = Column(JSON)  # 存储各指标对应的打分依据
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    evaluation = relationship("Evaluation", back_populates="results")
    question = relationship("Question", back_populates="results")

class Configuration(Base):
    __tablename__ = "configurations"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    user_id = Column(CHAR(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    config_key = Column(String(100), nullable=False)  # 如 "qwen.api_key", "evaluation.metrics"
    config_value = Column(Text)  # 配置值，可以是JSON格式
    config_description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    user = relationship("User", back_populates="configurations")

class BackgroundTask(Base):
    __tablename__ = "background_tasks"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    task_type = Column(String(50), nullable=False, index=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    progress = Column(Float, default=0.0, nullable=False)
    message = Column(Text)
    logs = Column(JSON)
    result = Column(JSON)
    error = Column(Text)
    params = Column(JSON)
    current_step = Column(Integer)
    total_steps = Column(Integer)
    worker_id = Column(String(100))
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=1, nullable=False)
    claimed_at = Column(DateTime)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ApiUsageLog(Base):
    """记录LLM API调用的Token消耗流水"""
    __tablename__ = "api_usage_logs"

    id = Column(CHAR(36), primary_key=True, default=generate_uuid)
    module_name = Column(String(50), nullable=False)  # 调用模块，如: document_analysis, testset_gen, evaluation
    model_name = Column(String(50), nullable=False)   # 实际调用的模型名称，如: qwen3.5-plus
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    latency_ms = Column(Integer, default=0)           # 请求耗时 (毫秒)
    cost = Column(String(20), default="0")            # 费用，使用字符串防止精度丢失
    is_error = Column(Boolean, default=False)
    error_msg = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
