"""LLM服务接口
定义LLM服务的基础接口和实现
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import os
import json


from sqlalchemy.orm import Session
from models.database import Configuration, ApiUsageLog
from config.database import SessionLocal
import asyncio
import httpx
import time
from datetime import datetime
from utils.logger import get_logger

logger = get_logger("llm_service")

def log_token_usage(module_name: str, model_name: str, usage: dict, latency_ms: int = 0, is_error: bool = False, error_msg: str = None):
    """异步或同步记录Token消耗及耗时到数据库"""
    try:
        if not usage and not is_error:
            return
        
        usage = usage or {}
        
        db = SessionLocal()
        try:
            log_entry = ApiUsageLog(
                module_name=module_name,
                model_name=model_name,
                prompt_tokens=usage.get("prompt_tokens", 0),
                completion_tokens=usage.get("completion_tokens", 0),
                total_tokens=usage.get("total_tokens", 0),
                latency_ms=latency_ms,
                is_error=is_error,
                error_msg=error_msg,
                # 显式写入应用本地时间，避免数据库时区设置导致展示偏移
                created_at=datetime.now()
            )
            db.add(log_entry)
            db.commit()
            if is_error:
                logger.error(f"Token使用记录异常: {module_name} ({model_name}) - 耗时 {latency_ms}ms - 错误: {error_msg}")
            else:
                logger.info(f"Token使用记录成功: {module_name} ({model_name}) - {usage.get('total_tokens', 0)} tokens, {latency_ms}ms")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"记录Token使用失败: {e}")


class LLMServiceInterface(ABC):
    """LLM服务接口"""

    @abstractmethod
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        pass

    @abstractmethod
    async def analyze_document(self, text: str, task: str = "summarize") -> Dict[str, Any]:
        """分析文档"""
        pass

    @abstractmethod
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """提取元数据"""
        pass

    @abstractmethod
    async def generate_outline(self, text: str) -> List[Dict[str, Any]]:
        """生成大纲"""
        pass

class QwenService(LLMServiceInterface):
    """Qwen模型服务"""
    
    def __init__(self, api_key: str = None, base_url: str = None, model: str = "qwen3.5-plus"):
        self.api_key = api_key or os.getenv("QWEN_API_KEY")
        self.model = model
        self.base_url = base_url or "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本，包含重试机制和更长的超时时间"""
        max_retries = kwargs.get("max_retries", 3)
        # 进一步放宽超时到 300 秒，处理复杂文档提纲
        timeout_value = kwargs.get("timeout", 300)
        retry_delay = 5  # 增加重试延迟
        module_name = kwargs.get("module_name", "unknown") # 获取调用模块名称
        
        last_error = None
        # 使用 httpx.Timeout 精确控制各项超时
        timeout = httpx.Timeout(timeout_value, connect=20.0, read=timeout_value, write=20.0)
        
        model_name = self.model
        logger.info(f"LLM开始生成请求: model={model_name}, timeout={timeout_value}s, prompt_len={len(prompt)}")
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    # 判断是否使用 OpenAI 兼容模式
                    is_openai_format = "/compatible-mode" in self.base_url or "/v1/chat/completions" in self.base_url
                    
                    if is_openai_format:
                        # OpenAI 兼容格式
                        url = self.base_url
                        if not url.endswith("/chat/completions"):
                            url = url.rstrip("/") + "/chat/completions"
                        
                        data = {
                            "model": self.model,
                            "messages": [
                                {"role": "user", "content": prompt}
                            ],
                            "temperature": kwargs.get("temperature", 0.7),
                            "max_tokens": kwargs.get("max_tokens", 65536)
                        }
                        
                        start_time = time.time()
                        response = await client.post(
                            url,
                            headers=self.headers,
                            json=data
                        )
                        duration = time.time() - start_time
                        
                        if response.status_code == 200:
                            logger.info(f"LLM请求成功: model={self.model}, duration={duration:.2f}s")
                            result = response.json()
                            usage = result.get("usage", {})
                            latency_ms = int(duration * 1000)
                            # 异步记录以避免阻塞
                            asyncio.create_task(asyncio.to_thread(log_token_usage, module_name, self.model, usage, latency_ms))
                            return result["choices"][0]["message"]["content"]
                        else:
                            raise Exception(f"OpenAI兼容接口调用失败: {response.status_code} - {response.text}")
                    else:
                        # DashScope 原生格式
                        data = {
                            "model": self.model,
                            "input": {
                                "messages": [
                                    {"role": "user", "content": prompt}
                                ]
                            },
                            "parameters": {
                                "temperature": kwargs.get("temperature", 0.7),
                                "top_p": kwargs.get("top_p", 0.8),
                                "max_tokens": kwargs.get("max_tokens", 30000)
                            }
                        }
                        
                        start_time = time.time()
                        response = await client.post(
                            self.base_url,
                            headers=self.headers,
                            json=data
                        )
                        duration = time.time() - start_time
                        
                        if response.status_code == 200:
                            logger.info(f"LLM请求成功: model={self.model}, duration={duration:.2f}s")
                            result = response.json()
                            usage = result.get("usage", {})
                            if not usage and "usage" in result.get("output", {}):
                                usage = result["output"]["usage"]
                            # 提取 DashScope 特定的 usage 格式 (input_tokens, output_tokens)
                            if usage and "input_tokens" in usage:
                                usage = {
                                    "prompt_tokens": usage.get("input_tokens", 0),
                                    "completion_tokens": usage.get("output_tokens", 0),
                                    "total_tokens": usage.get("total_tokens", 0)
                                }
                            latency_ms = int(duration * 1000)
                            # 异步记录以避免阻塞
                            asyncio.create_task(asyncio.to_thread(log_token_usage, module_name, self.model, usage, latency_ms))
                            return result["output"]["text"]
                        else:
                            raise Exception(f"DashScope原生接口调用失败: {response.status_code} - {response.text}")
                            
                except Exception as e:
                    last_error = e
                    import traceback
                    error_details = traceback.format_exc()
                    logger.warning(f"LLM调用第 {attempt + 1} 次尝试失败: {type(e).__name__} - {str(e)}\n{error_details}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay * (attempt + 1))
                    else:
                        break
        
        # 如果重试耗尽仍然失败，记录失败日志
        error_msg = f"LLM生成文本最终失败，重试 {max_retries} 次后错误: {str(last_error)}"
        asyncio.create_task(asyncio.to_thread(log_token_usage, module_name, self.model, {}, 0, is_error=True, error_msg=error_msg))
        raise Exception(error_msg)
    
    async def analyze_document(self, text: str, task: str = "summarize") -> Dict[str, Any]:
        """分析文档"""
        task_prompts = {
            "summarize": "请总结以下文档内容：\n\n{text}\n\n请提供简洁的摘要。",
            "extract_key_points": "请提取以下文档的关键要点：\n\n{text}\n\n请列出主要观点。",
            "analyze_structure": "请分析以下文档的结构：\n\n{text}\n\n请描述文档的组织结构。"
        }
        
        prompt = task_prompts.get(task, task_prompts["summarize"]).format(text=text)
        
        try:
            result = await self.generate_text(prompt, module_name="document_analysis")
            return {
                "task": task,
                "result": result,
                "success": True
            }
        except Exception as e:
            return {
                "task": task,
                "result": None,
                "success": False,
                "error": str(e)
            }
    
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """提取元数据"""
        prompt = f"""请分析以下文档内容，提取以下元数据信息：
1. 文档标题（如果有）
2. 作者（如果有）
3. 主题/关键词
4. 文档类型
5. 创建时间（如果有）
6. 语言
7. 主要内容概述（100字以内）

文档内容：
{text}

请以JSON格式返回结果，格式如下：
{{
    "title": "文档标题",
    "keywords": ["关键词1", "关键词2"],
    "document_type": "文档类型",
    "created_date": "创建时间",
    "language": "语言",
    "summary": "内容概述"
}}
"""
        
        try:
            result = await self.generate_text(prompt, module_name="metadata_extraction")
            # 尝试解析JSON
            try:
                metadata = json.loads(result)
                return {
                    "success": True,
                    "metadata": metadata
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "metadata": None,
                    "error": "无法解析元数据JSON"
                }
        except Exception as e:
            return {
                "success": False,
                "metadata": None,
                "error": str(e)
            }
    
    async def generate_outline(self, text: str) -> List[Dict[str, Any]]:
        """生成大纲"""
        prompt = f"""请分析以下文档内容，生成文档大纲。

文档内容：
{text}

请识别文档的章节结构，并以JSON格式返回大纲，格式如下：
[
    {{
        "level": 1,
        "title": "章节标题",
        "content": "章节内容概述"
    }},
    {{
        "level": 2,
        "title": "子章节标题",
        "content": "子章节内容概述"
    }}
]

请确保返回有效的JSON数组。
"""
        
        try:
            result = await self.generate_text(prompt, module_name="outline_generation")
            # 尝试解析JSON
            try:
                outline = json.loads(result)
                return {
                    "success": True,
                    "outline": outline
                }
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "outline": [],
                    "error": "无法解析大纲JSON"
                }
        except Exception as e:
            return {
                "success": False,
                "outline": [],
                "error": str(e)
            }


class MockLLMService(LLMServiceInterface):
    """模拟LLM服务（用于测试）"""
    
    async def generate_text(self, prompt: str, **kwargs) -> str:
        """生成文本"""
        return f"这是对提示词的模拟响应: {prompt[:100]}..."
    
    async def analyze_document(self, text: str, task: str = "summarize") -> Dict[str, Any]:
        """分析文档"""
        return {
            "task": task,
            "result": "这是模拟的文档分析结果",
            "success": True
        }
    
    async def extract_metadata(self, text: str) -> Dict[str, Any]:
        """提取元数据"""
        return {
            "success": True,
            "metadata": {
                "title": "模拟文档标题",
                "author": "模拟作者",
                "keywords": ["关键词1", "关键词2"],
                "document_type": "技术文档",
                "language": "中文",
                "summary": "这是模拟的文档摘要"
            }
        }
    
    async def generate_outline(self, text: str) -> List[Dict[str, Any]]:
        """生成大纲"""
        return {
            "success": True,
            "outline": [
                {"level": 1, "title": "第一章", "content": "第一章内容概述"},
                {"level": 2, "title": "1.1 小节", "content": "小节内容概述"}
            ]
        }


def get_llm_service(use_mock: bool = False, user_id: str = None, db: Session = None) -> LLMServiceInterface:
    """获取LLM服务实例，支持按用户从数据库读取配置"""
    if use_mock:
        return MockLLMService()
    
    api_key = None
    base_url = None
    model = os.getenv("QWEN_MODEL", "qwen3.5-plus")

    # 如果提供了user_id和db，尝试从数据库获取配置
    if user_id and db:
        from services.config_service import ConfigService
        cs = ConfigService(db)
        api_key = cs.get_api_key(user_id, "qwen")
        base_url = cs.get_config_value(user_id, "qwen.api_endpoint")
        model = cs.get_config_value(user_id, "qwen.generation_model", model)

    # 如果数据库没有配置，回退到环境变量
    if not api_key:
        api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
    
    if not base_url:
        base_url = os.getenv("OPENAI_BASE_URL") or os.getenv("QWEN_BASE_URL")

    if not api_key:
        print(f"警告: 用户 {user_id} 未设置 QWEN_API_KEY 且环境变量也未设置，使用模拟服务")
        return MockLLMService()
    
    return QwenService(api_key=api_key, base_url=base_url, model=model)
