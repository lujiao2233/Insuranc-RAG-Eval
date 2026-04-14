"""文档管理API路由
处理文档上传、查询、删除等操作，集成原始代码库中的高级功能
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Query, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import os
import uuid
import asyncio
from datetime import datetime
from pathlib import Path

from api.dependencies import get_current_user
from config.database import get_db
from schemas import Document, DocumentCreate, DocumentUpdate, PaginatedResponse
from models.database import User, Document as DocumentModel, TestSet as TestSetModel
from config.settings import settings
from services.document_service import DocumentService
from utils.logger import get_logger

logger = get_logger("documents_router")

router = APIRouter()

# 初始化文档服务
document_service = DocumentService()

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def sanitize_filename(filename: str) -> str:
    """清理文件名，防止路径遍历攻击"""
    filename = filename.replace('/', '').replace('\\', '')
    import re
    filename = re.sub(r'[^\w\.-]', '_', filename)
    if len(filename) > 100:
        name, ext = os.path.splitext(filename)
        filename = name[:100-len(ext)] + ext
    return filename


def _normalize_page_count(value) -> Optional[int]:
    if value is None:
        return None
    try:
        page_count = int(value)
    except (TypeError, ValueError):
        return None
    return page_count if page_count > 0 else None


@router.get("/", response_model=PaginatedResponse)
async def list_documents(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    is_analyzed: Optional[bool] = None,
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档列表"""
    query = db.query(DocumentModel).filter(DocumentModel.user_id == current_user.id)
    
    if status:
        query = query.filter(DocumentModel.status == status)
    
    if is_analyzed is not None:
        query = query.filter(DocumentModel.is_analyzed == is_analyzed)
    
    if category:
        query = query.filter(DocumentModel.category == category)
    
    total = query.count()
    documents = query.order_by(DocumentModel.upload_time.desc()).offset(skip).limit(limit).all()
    
    return PaginatedResponse(
        items=[Document.from_orm(doc) for doc in documents],
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


from services.task_manager import task_manager
from models.database import DocumentChunk as ChunkModel
from schemas import DocumentChunk as ChunkSchema

@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定文档信息，如果未分析则自动触发分析"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    task_id = None
    if not document.is_analyzed and document.status != 'processing':
        # 自动触发分析
        document.status = 'processing'
        db.commit()
        
        task_id = task_manager.create_task(
            task_type="document_analysis",
            params={"document_id": str(document_id)}
        )
        
        # 启动异步任务
        import asyncio
        from services.document_service import DocumentService
        ds = DocumentService()
        asyncio.create_task(ds.analyze_document_task(str(document_id), str(current_user.id), task_id))
    
    doc_data = Document.from_orm(document).dict()
    if not doc_data.get("page_count"):
        meta = doc_data.get("doc_metadata") or {}
        fallback = meta.get("page_count") or meta.get("total_pages") or meta.get("pages")
        normalized = _normalize_page_count(fallback)
        if normalized:
            doc_data["page_count"] = normalized
            document.page_count = normalized
            db.commit()
    doc_data["task_id"] = task_id
    
    return doc_data


@router.post("/upload", response_model=Document)
async def upload_document(
    file: UploadFile = File(...),
    category: str = Form("未分类"),
    analyze: bool = Form(False),  # 是否立即分析文档
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传文档文件"""
    
    file_extension = Path(file.filename).suffix.lower()
    if file_extension not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"不支持的文件类型: {file_extension}. 支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制: {file_size} bytes (最大: {settings.MAX_FILE_SIZE} bytes)"
        )
    
    safe_filename = sanitize_filename(file.filename)
    file_path = UPLOAD_DIR / safe_filename
    
    if file_path.exists():
        stem = file_path.stem
        suffix = file_path.suffix
        counter = 1
        while file_path.exists():
            safe_filename = f"{stem}_{counter}{suffix}"
            file_path = UPLOAD_DIR / safe_filename
            counter += 1
    
    try:
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")
    
    # 创建文档记录
    document = DocumentModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(file_path),
        file_type=file_extension.lstrip('.'),
        file_size=file_size,
        category=category,
        status='active',
        is_analyzed=False,
        upload_time=datetime.now()
    )
    
    db.add(document)
    db.commit()
    db.refresh(document)
    
    # 如果需要立即分析文档
    if analyze:
        try:
            document.status = 'processing'
            db.commit()
            
            task_id = task_manager.create_task(
                task_type="document_analysis",
                params={"document_id": str(document.id)}
            )
            asyncio.create_task(document_service.analyze_document_task(str(document.id), str(current_user.id), task_id))
        except Exception as e:
            logger.error(f"启动文档分析失败: {str(e)}")
            # 即使启动分析失败也不影响文档上传
    
    return Document.from_orm(document)


@router.post("/{document_id}/analyze")
async def analyze_single_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动触发分析"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    if document.is_analyzed:
        raise HTTPException(status_code=400, detail="文档已完成分析，禁止重复分析")

    document.status = 'processing'
    db.commit()
    
    task_id = task_manager.create_task(
        task_type="document_analysis",
        params={"document_id": str(document_id)}
    )
    
    # 启动异步任务
    asyncio.create_task(document_service.analyze_document_task(str(document_id), str(current_user.id), task_id))
    
    return {"task_id": task_id, "message": "分析任务已启动"}

@router.get("/{document_id}/chunks", response_model=PaginatedResponse)
async def list_document_chunks(
    document_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    keyword: Optional[str] = None,
    entity_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档切片，支持关键词高亮和实体筛选"""
    query = db.query(ChunkModel).filter(ChunkModel.document_id == str(document_id))
    
    if keyword:
        query = query.filter(ChunkModel.content.like(f"%{keyword}%"))
    
    if entity_type:
        # 假设 entities 是 JSON 数组，包含产品名
        query = query.filter(ChunkModel.entities.contains([entity_type]))
    
    total = query.count()
    chunks = query.order_by(ChunkModel.sequence_number.asc()).offset(skip).limit(limit).all()
    
    # 简单的高亮处理
    items = []
    for c in chunks:
        chunk_dict = ChunkSchema.from_orm(c).dict()
        if keyword:
            chunk_dict["content"] = chunk_dict["content"].replace(keyword, f"<mark>{keyword}</mark>")
        items.append(chunk_dict)

    return PaginatedResponse(
        items=items,
        total=total,
        page=skip // limit + 1,
        size=limit,
        pages=(total + limit - 1) // limit
    )


@router.post("/upload-batch", response_model=List[Document])
async def upload_documents_batch(
    files: List[UploadFile] = File(...),
    category: str = Form("未分类"),
    analyze: bool = Form(False),  # 是否立即分析文档
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量上传文档文件"""
    uploaded_documents = []
    
    for file in files:
        try:
            # 传递analyze参数
            doc = await upload_document(file, category, analyze, current_user, db)
            uploaded_documents.append(doc)
        except HTTPException:
            continue
    
    return uploaded_documents


@router.post("/analyze-batch")
async def analyze_documents_batch(
    document_ids: List[UUID] = Query(..., description="要分析的文档ID列表"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """批量分析文档"""
    documents = db.query(DocumentModel).filter(
        DocumentModel.id.in_([str(doc_id) for doc_id in document_ids]),
        DocumentModel.user_id == current_user.id
    ).all()
    
    if not documents:
        raise HTTPException(status_code=404, detail="未找到指定的文档")
    
    results = []
    success_count = 0
    
    for document in documents:
        if document.is_analyzed:
             results.append({
                 "document_id": str(document.id),
                 "filename": document.filename,
                 "status": "skipped",
                 "message": "已完成分析，跳过"
             })
             continue
             
        try:
            # 更新状态为处理中
            document.status = 'processing'
            db.commit()
            
            # 创建异步分析任务
            task_id = task_manager.create_task(
                task_type="document_analysis",
                params={"document_id": str(document.id)}
            )
            asyncio.create_task(document_service.analyze_document_task(str(document.id), str(current_user.id), task_id))
            
            results.append({
                "document_id": str(document.id),
                "filename": document.filename,
                "status": "processing",
                "message": "分析任务已启动",
                "task_id": task_id
            })
            success_count += 1
        except Exception as e:
            logger.error(f"启动文档 {document.id} 分析失败: {str(e)}")
            results.append({
                "document_id": str(document.id),
                "filename": document.filename,
                "status": "failed",
                "message": f"启动分析失败: {str(e)}"
            })
    
    return {
        "message": f"批量分析任务已提交，已启动: {success_count}，跳过或失败: {len(documents) - success_count}",
        "results": results,
        "total": len(documents)
    }


@router.put("/{document_id}", response_model=Document)
async def update_document(
    document_id: UUID,
    document_update: DocumentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新文档信息"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    update_data = document_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)
    
    db.commit()
    db.refresh(document)
    
    return Document.from_orm(document)


@router.delete("/{document_id}")
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除文档"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    try:
        # 删除物理文件
        if document.file_path:
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()
        
        # 先解绑测试集，确保删除文档时不会影响测试集和后续报告
        db.query(TestSetModel).filter(
            TestSetModel.document_id == str(document_id),
            TestSetModel.user_id == current_user.id
        ).update(
            {TestSetModel.document_id: None},
            synchronize_session=False
        )

        # chunks 由 ondelete/cascade 清理；testsets 已解绑，不会被联动删除
        db.delete(document)
        db.commit()
        
        return {"message": "文档已删除", "id": str(document_id)}
    except Exception as e:
        db.rollback()
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail="删除失败，请检查 testsets.document_id 外键是否已迁移为 SET NULL")


@router.get("/{document_id}/content")
async def get_document_content(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档内容和元数据"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    content = await document_service.get_document_content(document)
    
    return {
        "document_id": str(document.id),
        "filename": document.filename,
        "content": content,
        "metadata": document.doc_metadata_col,
        "is_analyzed": document.is_analyzed
    }


@router.get("/{document_id}/download")
async def download_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """下载文档文件"""
    document = db.query(DocumentModel).filter(
        DocumentModel.id == str(document_id),
        DocumentModel.user_id == current_user.id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    file_path = Path(document.file_path)
    if not file_path.exists():
        fallback_path = UPLOAD_DIR / document.filename
        if fallback_path.exists():
            file_path = fallback_path
        else:
            raise HTTPException(status_code=404, detail="文件不存在")
    
    return FileResponse(
        path=file_path,
        filename=document.filename,
        media_type='application/octet-stream'
    )


@router.get("/stats/summary")
async def get_document_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取文档统计信息"""
    total_documents = db.query(DocumentModel).filter(
        DocumentModel.user_id == current_user.id
    ).count()
    
    analyzed_documents = db.query(DocumentModel).filter(
        DocumentModel.user_id == current_user.id,
        DocumentModel.is_analyzed == True
    ).count()
    
    unanalyzed_documents = total_documents - analyzed_documents
    
    type_stats = {}
    documents = db.query(DocumentModel).filter(
        DocumentModel.user_id == current_user.id
    ).all()
    
    for doc in documents:
        file_type = doc.file_type.upper()
        type_stats[file_type] = type_stats.get(file_type, 0) + 1
    
    return {
        "total_documents": total_documents,
        "analyzed_documents": analyzed_documents,
        "unanalyzed_documents": unanalyzed_documents,
        "type_distribution": type_stats
    }
