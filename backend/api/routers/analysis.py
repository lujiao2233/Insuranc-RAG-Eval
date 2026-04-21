"""文档分析API路由
处理文档的LLM分析功能
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from uuid import UUID
from datetime import datetime

from api.dependencies import get_current_user
from config.database import get_db
from models.database import User, Document as DocumentModel
from services.task_manager import task_manager
from services.document_service import DocumentService

router = APIRouter()
document_service = DocumentService()

@router.post("/analyze/{document_id}")
async def analyze_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """分析单个文档，支持异步任务"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.is_analyzed:
        return {"message": "文档已分析", "document_id": str(document_id), "status": "already_analyzed"}
    
    task_id = task_manager.submit_task(
        task_type="document_analysis",
        params={
            "document_id": str(document_id),
            "user_id": str(current_user.id),
        }
    )
    
    return {
        "task_id": task_id,
        "message": "分析任务已启动",
        "status": "processing"
    }

@router.get("/status/{task_id}")
async def get_analysis_task_status(task_id: str):
    """获取分析任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task

@router.get("/results/{document_id}")
async def get_analysis_results(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档分析结果"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if not document.is_analyzed:
        raise HTTPException(status_code=400, detail="文档尚未分析")
    
    return {
        "document_id": str(document_id),
        "filename": document.filename,
        "metadata": document.doc_metadata_col,
        "outline": document.outline,
        "product_entities": document.product_entities,
        "page_count": document.page_count,
        "analyzed_at": document.analyzed_at
    }
