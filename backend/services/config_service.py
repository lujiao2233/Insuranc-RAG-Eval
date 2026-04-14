"""配置管理服务
提供系统配置的统一管理，包括API密钥、系统设置、评估参数等
"""
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
import json
import os
import uuid
from datetime import datetime

from models.database import Configuration, User
from utils.logger import get_logger

logger = get_logger("config_service")


DEFAULT_CONFIGS = {
    "qwen.api_endpoint": {
        "value": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "description": "Qwen API端点地址"
    },
    "qwen.generation_model": {
        "value": "qwen3.5-plus",
        "description": "生成测试集使用的模型"
    },
    "qwen.evaluation_model": {
        "value": "qwen3.5-plus",
        "description": "评估使用的模型"
    },
    "qwen.temperature": {
        "value": "0.1",
        "description": "模型温度参数"
    },
    "qwen.max_tokens": {
        "value": "2000",
        "description": "最大生成token数"
    },
    "default.num_questions": {
        "value": "10",
        "description": "默认问题数量"
    },
    "default.batch_size": {
        "value": "5",
        "description": "默认批处理大小"
    },
    "default.timeout": {
        "value": "60",
        "description": "默认超时时间(秒)"
    },
    "rag.chunk_size": {
        "value": "500",
        "description": "文档分块大小"
    },
    "rag.chunk_overlap": {
        "value": "50",
        "description": "分块重叠大小"
    },
    "rag.top_k": {
        "value": "5",
        "description": "检索文档数量"
    },
    "rag.similarity_threshold": {
        "value": "0.7",
        "description": "相似度阈值"
    },
    "evaluation.ragas_metrics": {
        "value": '["answer_relevance", "context_relevance", "faithfulness"]',
        "description": "RAGAS评估指标"
    },
    "evaluation.batch_size": {
        "value": "5",
        "description": "评估批处理大小"
    },
    "evaluation.temperature": {
        "value": "0.1",
        "description": "评估LLM温度"
    },
    "thresholds.answer_relevance.excellent": {
        "value": "0.8",
        "description": "答案相关性优秀阈值"
    },
    "thresholds.answer_relevance.good": {
        "value": "0.6",
        "description": "答案相关性良好阈值"
    },
    "thresholds.faithfulness.excellent": {
        "value": "0.8",
        "description": "忠实度优秀阈值"
    },
    "thresholds.faithfulness.good": {
        "value": "0.6",
        "description": "忠实度良好阈值"
    },
    "thresholds.overall.excellent": {
        "value": "0.8",
        "description": "总体优秀阈值"
    },
    "thresholds.overall.good": {
        "value": "0.6",
        "description": "总体良好阈值"
    },
    "files.max_size_mb": {
        "value": "50",
        "description": "最大文件大小(MB)"
    },
    "files.supported_formats": {
        "value": '["pdf", "docx", "xlsx"]',
        "description": "支持的文件格式"
    },
    "chunking.short_merge_threshold": {
        "value": "60",
        "description": "切片短片合并阈值（字符）"
    },
    "chunking.max_chunk_chars": {
        "value": "500",
        "description": "单切片最大字符数"
    },
    "storage.retention_days": {
        "value": "30",
        "description": "数据保留天数"
    },
    "logging.level": {
        "value": "INFO",
        "description": "日志级别"
    }
}

SENSITIVE_KEYS = ["qwen.api_key", "openai.api_key", "api_key"]


class ConfigService:
    """配置管理服务类"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_config(self, user_id: str, config_key: str) -> Optional[Configuration]:
        """获取单个配置项"""
        return self.db.query(Configuration).filter(
            and_(
                Configuration.user_id == user_id,
                Configuration.config_key == config_key
            )
        ).first()
    
    def get_config_value(self, user_id: str, config_key: str, default: Any = None) -> Any:
        """获取配置值"""
        config = self.get_config(user_id, config_key)
        if config and config.config_value:
            try:
                return json.loads(config.config_value)
            except (json.JSONDecodeError, TypeError):
                return config.config_value
        if config_key in DEFAULT_CONFIGS:
            try:
                return json.loads(DEFAULT_CONFIGS[config_key]["value"])
            except (json.JSONDecodeError, TypeError):
                return DEFAULT_CONFIGS[config_key]["value"]
        return default
    
    def get_all_configs(self, user_id: str) -> List[Configuration]:
        """获取用户所有配置"""
        return self.db.query(Configuration).filter(
            Configuration.user_id == user_id
        ).all()
    
    def get_configs_by_prefix(self, user_id: str, prefix: str) -> Dict[str, Any]:
        """获取指定前缀的所有配置"""
        configs = self.db.query(Configuration).filter(
            and_(
                Configuration.user_id == user_id,
                Configuration.config_key.like(f"{prefix}%")
            )
        ).all()
        
        result = {}
        for config in configs:
            key = config.config_key
            try:
                result[key] = json.loads(config.config_value) if config.config_value else None
            except (json.JSONDecodeError, TypeError):
                result[key] = config.config_value
        
        for key, meta in DEFAULT_CONFIGS.items():
            if key.startswith(prefix) and key not in result:
                try:
                    result[key] = json.loads(meta["value"])
                except (json.JSONDecodeError, TypeError):
                    result[key] = meta["value"]
        
        return result
    
    def set_config(self, user_id: str, config_key: str, config_value: Any, description: str = None) -> Configuration:
        """设置配置项"""
        config = self.get_config(user_id, config_key)
        
        if isinstance(config_value, (dict, list)):
            value_str = json.dumps(config_value, ensure_ascii=False)
        else:
            value_str = str(config_value)
        
        if config:
            config.config_value = value_str
            if description:
                config.config_description = description
            config.updated_at = datetime.now()
        else:
            if not description and config_key in DEFAULT_CONFIGS:
                description = DEFAULT_CONFIGS[config_key].get("description")
            
            config = Configuration(
                id=str(uuid.uuid4()),
                user_id=user_id,
                config_key=config_key,
                config_value=value_str,
                config_description=description
            )
            self.db.add(config)
        
        self.db.commit()
        self.db.refresh(config)
        
        logger.info(f"配置已更新: {config_key}")
        return config
    
    def delete_config(self, user_id: str, config_key: str) -> bool:
        """删除配置项"""
        config = self.get_config(user_id, config_key)
        if config:
            self.db.delete(config)
            self.db.commit()
            logger.info(f"配置已删除: {config_key}")
            return True
        return False
    
    def set_api_key(self, user_id: str, service: str, api_key: str) -> Configuration:
        """设置API密钥"""
        config_key = f"{service}.api_key"
        return self.set_config(user_id, config_key, api_key, f"{service.upper()} API密钥")
    
    def get_api_key(self, user_id: str, service: str) -> Optional[str]:
        """获取API密钥，        优先级：用户数据库配置 > 环境变量
        """
        config_key = f"{service}.api_key"
        db_key = self.get_config_value(user_id, config_key)
        if db_key:
            return db_key
        
        env_key = os.getenv(f"{service.upper()}_API_KEY")
        if env_key and env_key != "your_api_key_here":
            return env_key
        
        return None
    
    def get_api_status(self, user_id: str) -> Dict[str, str]:
        """获取API配置状态"""
        services = ["qwen", "openai"]
        status = {}
        for service in services:
            key = self.get_api_key(user_id, service)
            status[service] = "已配置" if key else "未配置"
        return status
    
    def get_qwen_config(self, user_id: str) -> Dict[str, Any]:
        """获取Qwen配置"""
        return self.get_configs_by_prefix(user_id, "qwen.")
    
    def get_evaluation_config(self, user_id: str) -> Dict[str, Any]:
        """获取评估配置"""
        return self.get_configs_by_prefix(user_id, "evaluation.")
    
    def get_rag_config(self, user_id: str) -> Dict[str, Any]:
        """获取RAG配置"""
        return self.get_configs_by_prefix(user_id, "rag.")
    
    def get_thresholds(self, user_id: str) -> Dict[str, Any]:
        """获取性能阈值配置"""
        return self.get_configs_by_prefix(user_id, "thresholds.")
    
    def get_system_config(self, user_id: str) -> Dict[str, Any]:
        """获取系统配置"""
        result = {}
        
        result["default"] = self.get_configs_by_prefix(user_id, "default.")
        result["files"] = self.get_configs_by_prefix(user_id, "files.")
        result["chunking"] = self.get_configs_by_prefix(user_id, "chunking.")
        result["storage"] = self.get_configs_by_prefix(user_id, "storage.")
        result["logging"] = self.get_configs_by_prefix(user_id, "logging.")
        
        return result
    
    def test_api_connection(self, user_id: str, service: str = "qwen") -> Dict[str, Any]:
        """测试API连接"""
        try:
            api_key = self.get_api_key(user_id, service)
            if not api_key:
                return {"success": False, "message": "API密钥未配置"}
            
            if service == "qwen":
                endpoint = self.get_config_value(user_id, "qwen.api_endpoint", 
                    "https://dashscope.aliyuncs.com/compatible-mode/v1")
                model = self.get_config_value(user_id, "qwen.generation_model", "qwen3-max")
                
                from openai import OpenAI
                client = OpenAI(api_key=api_key, base_url=endpoint)
                
                completion = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": "这是一个连通性测试，请简单回复OK。"}
                    ],
                    max_tokens=16
                )
                
                if completion and completion.choices:
                    content = completion.choices[0].message.content
                    return {
                        "success": True,
                        "message": f"API连接成功，模型 {model} 可用",
                        "response": content
                    }
            
            return {"success": False, "message": "不支持的API服务"}
            
        except Exception as e:
            logger.error(f"API连接测试失败: {str(e)}")
            return {"success": False, "message": f"连接失败: {str(e)}"}
    
    def batch_update_configs(self, user_id: str, configs: Dict[str, Any]) -> Dict[str, Any]:
        """批量更新配置"""
        updated = []
        errors = []
        
        for key, value in configs.items():
            try:
                self.set_config(user_id, key, value)
                updated.append(key)
            except Exception as e:
                errors.append({"key": key, "error": str(e)})
        
        return {
            "updated": updated,
            "errors": errors,
            "total_updated": len(updated),
            "total_errors": len(errors)
        }
    
    def reset_to_defaults(self, user_id: str, prefix: str = None) -> int:
        """重置为默认配置"""
        count = 0
        for key, meta in DEFAULT_CONFIGS.items():
            if prefix and not key.startswith(prefix):
                continue
            
            try:
                self.set_config(user_id, key, meta["value"], meta["description"])
                count += 1
            except Exception as e:
                logger.error(f"重置配置失败 {key}: {str(e)}")
        
        return count
    
    def export_configs(self, user_id: str) -> Dict[str, Any]:
        """导出配置"""
        configs = self.get_all_configs(user_id)
        result = {}
        
        for config in configs:
            if any(sensitive in config.config_key.lower() for sensitive in ["api_key", "secret", "password"]):
                result[config.config_key] = "***HIDDEN***"
            else:
                try:
                    result[config.config_key] = json.loads(config.config_value)
                except (json.JSONDecodeError, TypeError):
                    result[config.config_key] = config.config_value
        
        return result
    
    def import_configs(self, user_id: str, configs: Dict[str, Any], overwrite: bool = True) -> Dict[str, Any]:
        """导入配置"""
        imported = []
        skipped = []
        errors = []
        
        for key, value in configs.items():
            if value == "***HIDDEN***":
                skipped.append(key)
                continue
            
            existing = self.get_config(user_id, key)
            if existing and not overwrite:
                skipped.append(key)
                continue
            
            try:
                self.set_config(user_id, key, value)
                imported.append(key)
            except Exception as e:
                errors.append({"key": key, "error": str(e)})
        
        return {
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
            "total_imported": len(imported),
            "total_skipped": len(skipped)
        }
