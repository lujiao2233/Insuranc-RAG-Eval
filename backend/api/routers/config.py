"""配置管理API路由
处理系统配置、API密钥、评估参数等设置
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db
from models.database import User, Configuration
from schemas import Configuration as ConfigurationSchema, ConfigurationCreate, ConfigurationUpdate
from services.config_service import ConfigService

router = APIRouter()


class ConfigBatchUpdate(BaseModel):
    configs: Dict[str, Any]


class APIKeyUpdate(BaseModel):
    service: str
    api_key: str


class ConfigImport(BaseModel):
    configs: Dict[str, Any]
    overwrite: bool = True


@router.get("/all")
async def get_all_configurations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有配置分组"""
    config_service = ConfigService(db)
    
    return {
        "qwen": config_service.get_qwen_config(str(current_user.id)),
        "evaluation": config_service.get_evaluation_config(str(current_user.id)),
        "thresholds": config_service.get_thresholds(str(current_user.id)),
        "system": config_service.get_system_config(str(current_user.id))
    }


@router.get("/")
async def list_configurations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取所有配置"""
    config_service = ConfigService(db)
    configs = config_service.get_all_configs(str(current_user.id))
    
    result = []
    for config in configs:
        config_dict = {
            "id": config.id,
            "config_key": config.config_key,
            "config_value": config.config_value,
            "description": config.config_description,
            "created_at": config.created_at.isoformat() if config.created_at else None,
            "updated_at": config.updated_at.isoformat() if config.updated_at else None
        }
        if any(s in config.config_key.lower() for s in ["api_key", "secret", "password"]):
            config_dict["config_value"] = "***"
        result.append(config_dict)
    
    return {"items": result, "total": len(result)}


@router.post("/")
async def create_configuration(
    config: ConfigurationCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新配置"""
    config_service = ConfigService(db)
    
    existing = config_service.get_config(str(current_user.id), config.config_key)
    if existing:
        raise HTTPException(status_code=400, detail="配置项已存在，请使用PUT方法更新")
    
    new_config = config_service.set_config(
        str(current_user.id),
        config.config_key,
        config.config_value,
        config.description
    )
    
    return {
        "id": new_config.id,
        "config_key": new_config.config_key,
        "config_value": new_config.config_value,
        "description": new_config.config_description,
        "message": "配置创建成功"
    }


@router.post("/batch")
async def batch_update_configurations(
    batch: ConfigBatchUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """批量更新配置"""
    config_service = ConfigService(db)
    result = config_service.batch_update_configs(str(current_user.id), batch.configs)
    return result


@router.get("/api/status")
async def get_api_status(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取API配置状态"""
    config_service = ConfigService(db)
    status = config_service.get_api_status(str(current_user.id))
    return {"api_status": status}


@router.post("/api/key")
async def set_api_key(
    api_key_update: APIKeyUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """设置API密钥"""
    config_service = ConfigService(db)
    config_service.set_api_key(str(current_user.id), api_key_update.service, api_key_update.api_key)
    return {"message": f"{api_key_update.service.upper()} API密钥已保存"}


@router.post("/api/test")
async def test_api_connection(
    service: str = "qwen",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """测试API连接"""
    config_service = ConfigService(db)
    result = config_service.test_api_connection(str(current_user.id), service)
    
    if result["success"]:
        return {"status": "success", "message": result["message"], "response": result.get("response")}
    else:
        return {"status": "error", "message": result["message"]}


@router.get("/qwen/all")
async def get_qwen_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取Qwen配置"""
    config_service = ConfigService(db)
    configs = config_service.get_qwen_config(str(current_user.id))
    return {"configs": configs}


@router.get("/evaluation/all")
async def get_evaluation_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取评估配置"""
    config_service = ConfigService(db)
    configs = config_service.get_evaluation_config(str(current_user.id))
    return {"configs": configs}


@router.get("/rag/all")
async def get_rag_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取RAG配置"""
    config_service = ConfigService(db)
    configs = config_service.get_rag_config(str(current_user.id))
    return {"configs": configs}


@router.get("/thresholds/all")
async def get_thresholds_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取性能阈值配置"""
    config_service = ConfigService(db)
    configs = config_service.get_thresholds(str(current_user.id))
    return {"configs": configs}


@router.get("/system/all")
async def get_system_config(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取系统配置"""
    config_service = ConfigService(db)
    configs = config_service.get_system_config(str(current_user.id))
    return {"configs": configs}


@router.post("/reset")
async def reset_to_defaults(
    prefix: str = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """重置为默认配置"""
    config_service = ConfigService(db)
    count = config_service.reset_to_defaults(str(current_user.id), prefix)
    return {"message": f"已重置 {count} 个配置项为默认值", "count": count}


@router.get("/export")
async def export_configurations(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """导出配置"""
    config_service = ConfigService(db)
    configs = config_service.export_configs(str(current_user.id))
    return {"configs": configs}


@router.post("/import")
async def import_configurations(
    config_import: ConfigImport,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """导入配置"""
    config_service = ConfigService(db)
    result = config_service.import_configs(
        str(current_user.id),
        config_import.configs,
        config_import.overwrite
    )
    return result


@router.get("/group/{prefix:path}")
async def get_config_group(
    prefix: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取指定前缀的配置组"""
    config_service = ConfigService(db)
    configs = config_service.get_configs_by_prefix(str(current_user.id), prefix)
    return {"prefix": prefix, "configs": configs}


@router.get("/{config_key:path}")
async def get_configuration(
    config_key: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取特定配置"""
    config_service = ConfigService(db)
    config = config_service.get_config(str(current_user.id), config_key)
    
    if not config:
        value = config_service.get_config_value(str(current_user.id), config_key)
        if value is not None:
            return {
                "config_key": config_key,
                "config_value": value,
                "source": "default"
            }
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    return {
        "id": config.id,
        "config_key": config.config_key,
        "config_value": config.config_value,
        "description": config.config_description,
        "created_at": config.created_at.isoformat() if config.created_at else None,
        "updated_at": config.updated_at.isoformat() if config.updated_at else None
    }


@router.put("/{config_key:path}")
async def update_configuration(
    config_key: str,
    config_update: ConfigurationUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新配置"""
    config_service = ConfigService(db)
    
    import json
    if isinstance(config_update.config_value, (dict, list)):
        value = json.dumps(config_update.config_value, ensure_ascii=False)
    else:
        value = config_update.config_value
    
    updated_config = config_service.set_config(
        str(current_user.id),
        config_key,
        value,
        config_update.description
    )
    
    return {
        "id": updated_config.id,
        "config_key": updated_config.config_key,
        "config_value": updated_config.config_value,
        "description": updated_config.config_description,
        "message": "配置更新成功"
    }


@router.delete("/{config_key:path}")
async def delete_configuration(
    config_key: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除配置"""
    config_service = ConfigService(db)
    
    if config_service.delete_config(str(current_user.id), config_key):
        return {"message": "配置删除成功"}
    
    raise HTTPException(status_code=404, detail="配置项不存在")
