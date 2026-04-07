"""测试集问题生成服务
使用Qwen大模型生成测试问题，集成原始代码库中的高级功能
"""
import asyncio
import os
import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from fastapi import Query
import httpx
import random

from utils.logger import get_logger
from config.settings import settings
from services.advanced_testset_generator import advanced_testset_generator
from services.context_selector import context_selector
from services.chunking_service import ChunkingService

logger = get_logger("question_generator")


def _has_cjk(text: str) -> bool:
    """
    检测文本是否包含中日韩（CJK）字符
    """
    if not text:
        return False
    for ch in text:
        if "\u4e00" <= ch <= "\u9fff":
            return True
    return False


from sqlalchemy.orm import Session
from models.database import Configuration

class QuestionGenerator:
    """问题生成器类"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
        self.model = model or os.getenv("QWEN_MODEL", "qwen3.5-plus")
        self.client = self.get_llm_client()
        self.chunking_service = ChunkingService()
    
    def get_llm_client(self):
        """获取LLM客户端"""
        try:
            from openai import AsyncOpenAI
            
            if not self.api_key:
                logger.warning("未设置 API Key，问题生成将跳过")
                return None
            
            return AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=120.0,
                max_retries=3
            )
        except ImportError:
            logger.info("OpenAI库不可用，问题生成将跳过")
            return None
        except Exception as e:
            logger.error(f"初始化LLM客户端失败: {e}")
            return None

    async def generate_questions(
        self,
        context: str,
        num_questions: int = 5,
        question_types: Optional[List[str]] = None,
        max_tokens: int = 50000
    ) -> List[Dict[str, Any]]:
        """生成测试问题"""
        if not self.client:
            logger.warning("LLM客户端未初始化，跳过问题生成")
            return []
        
        if not context or len(context.strip()) < 50:
            logger.warning("上下文内容太短，无法生成问题")
            return []
        
        limited_context = context[:8000]
        
        if question_types:
            type_desc = "，问题类型包括：" + "、".join(question_types)
        else:
            type_desc = "，问题类型应多样化，包括事实性问题、理解性问题、应用性问题等"
        
        prompt = f"""
        请基于以下上下文生成{num_questions}个高质量的测试问题{type_desc}：
        
        上下文：
        {limited_context}
        
        要求：
        1. 问题必须基于上下文内容，不能超出上下文范围
        2. 问题应具有实际意义，避免过于简单或复杂
        3. 问题应清晰明确，避免歧义
        4. 为每个问题提供预期答案
        5. 问题类型应多样化，涵盖不同的认知层次
        
        请以JSON格式返回，格式如下：
        [
          {{
            "question": "问题内容",
            "question_type": "问题类型",
            "expected_answer": "预期答案",
            "context": "相关上下文片段"
          }}
        ]
        
        注意：只返回JSON数据，不要包含其他说明文字。
        """
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的测试问题生成助手，能够基于给定的上下文生成高质量的测试问题。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content.strip()
            
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                questions = json.loads(json_str)
                
                validated_questions = []
                for q in questions:
                    if isinstance(q, dict) and 'question' in q and q['question'].strip():
                        validated_q = {
                            "question": q.get("question", "").strip(),
                            "question_type": q.get("question_type", "factual").strip(),
                            "expected_answer": q.get("expected_answer", "").strip(),
                            "context": q.get("context", limited_context[:200]).strip(),
                            "category_major": q.get("category_major"),
                            "category_minor": q.get("category_minor")
                        }
                        validated_questions.append(validated_q)
                
                return validated_questions[:num_questions]
            else:
                logger.warning(f"未能从响应中提取JSON数据: {content[:200]}")
                return []
                
        except Exception as e:
            logger.error(f"生成问题时出错: {e}")
            return []

    async def generate_advanced_questions(
        self,
        content: List[Dict[str, Any]],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """使用原始代码库的高级功能生成问题
        
        Returns:
            包含 questions, count, warnings 的字典
        """
        result = advanced_testset_generator.generate_testset(content, params)
        
        if isinstance(result, dict):
            return result
        return {"questions": result, "count": len(result), "warnings": []}

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """获取文本的稠密向量"""
        if not self.client:
            return []
        try:
            response = await self.client.embeddings.create(
                model=os.getenv("EMBEDDING_MODEL", "text-embedding-v3"),
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"获取向量失败: {e}")
            return []

    async def generate_multidoc_questions(
        self,
        documents: List[Dict[str, Any]],
        strategy: str = "deep_dive",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """生成多文档关联问题"""
        questions = context_selector.generate_multidoc_questions(
            documents, 
            strategy, 
            **kwargs
        )
        return questions

    async def chunk_text(
        self,
        text: str,
        outline: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """对文本进行切片（统一使用 ChunkingService）
        
        Args:
            text: 待切片文本
            outline: 文档提纲（可选）
            metadata: 文档元数据（可选）
            
        Returns:
            切片列表
        """
        return await self.chunking_service.chunk_document(
            text=text,
            outline=outline or [],
            doc_metadata=metadata or {}
        )


def get_question_generator(user_id: str = None, db: Session = None):
    """获取问题生成器实例，支持按用户从数据库读取配置"""
    api_key = None
    base_url = None
    model = None

    if user_id and db:
        from services.config_service import ConfigService
        cs = ConfigService(db)
        api_key = cs.get_api_key(user_id, "qwen")
        base_url = cs.get_config_value(user_id, "qwen.api_endpoint")
        model = cs.get_config_value(user_id, "qwen.generation_model")

    if base_url and "compatible-mode" not in base_url and "dashscope" in base_url:
        if base_url.endswith("/"):
            base_url = base_url + "compatible-mode/v1"
        else:
            base_url = base_url + "/compatible-mode/v1"

    return QuestionGenerator(api_key=api_key, base_url=base_url, model=model)
