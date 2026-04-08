"""测试集管理API路由
处理测试集创建、查询、删除等操作
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
import os
import threading
import io
import csv
from urllib.parse import quote
from datetime import datetime

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db, SessionLocal
from schemas import TestSetCreate, TestSetUpdate
from models.database import User, TestSet as TestSetModel, Document, Question, Evaluation as EvaluationModel, EvaluationResult as EvaluationResultModel
from services.question_generator import get_question_generator
from services.task_manager import task_manager
from services.config_service import ConfigService
from services.advanced_testset_generator import QWEN_TAXONOMY_V1
from utils.logger import get_logger

logger = get_logger("testsets_router")

router = APIRouter()

_VALID_MAJOR_MINOR = {
    (str(item.get("major") or "").strip(), str(minor or "").strip())
    for item in QWEN_TAXONOMY_V1
    for minor in (item.get("minors") or [])
    if str(item.get("major") or "").strip() and str(minor or "").strip()
}
_MINOR_TO_MAJOR = {minor: major for major, minor in _VALID_MAJOR_MINOR}


def _normalize_question_category(question_type: Any, category_major: Any, category_minor: Any):
    qtype = str(question_type or "").strip()
    major = str(category_major or "").strip()
    minor = str(category_minor or "").strip()

    if qtype and "-" in qtype:
        left, right = [x.strip() for x in qtype.split("-", 1)]
        if (left, right) in _VALID_MAJOR_MINOR:
            major = major or left
            minor = minor or right

    if minor and not major:
        major = _MINOR_TO_MAJOR.get(minor, major)
    if qtype and not minor and qtype in _MINOR_TO_MAJOR:
        minor = qtype
        major = major or _MINOR_TO_MAJOR.get(minor, "")
    if major and minor and (major, minor) not in _VALID_MAJOR_MINOR:
        inferred_major = _MINOR_TO_MAJOR.get(minor)
        if inferred_major:
            major = inferred_major
        else:
            major = ""
            minor = ""
    if not major and not minor:
        major = "基础理解类"
        minor = "事实召回"
    qtype = minor or qtype or "事实召回"
    return qtype, major, minor


def _build_question_metadata(question_payload: Dict[str, Any]) -> Dict[str, Any]:
    """归一化问题元数据，确保多文档信息可持久化。"""
    raw_meta = question_payload.get("metadata")
    meta: Dict[str, Any] = dict(raw_meta) if isinstance(raw_meta, dict) else {}

    def _to_list(value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            values = value
        else:
            values = [value]
        cleaned: List[str] = []
        for item in values:
            text = str(item or "").strip()
            if text:
                cleaned.append(text)
        return cleaned

    def _uniq_keep_order(values: List[str]) -> List[str]:
        seen = set()
        result: List[str] = []
        for value in values:
            if value not in seen:
                seen.add(value)
                result.append(value)
        return result

    doc_ids = _uniq_keep_order(
        _to_list(meta.get("doc_ids"))
        + _to_list(meta.get("document_ids"))
        + _to_list(meta.get("doc_id"))
        + _to_list(question_payload.get("doc_ids"))
        + _to_list(question_payload.get("document_ids"))
        + _to_list(question_payload.get("doc_id"))
    )

    filenames = _uniq_keep_order(
        _to_list(meta.get("filenames"))
        + _to_list(meta.get("source_documents"))
        + _to_list(meta.get("source_document"))
        + _to_list(meta.get("filename"))
        + _to_list(question_payload.get("filenames"))
        + _to_list(question_payload.get("filename"))
    )

    if doc_ids:
        meta["doc_ids"] = doc_ids
        meta["doc_id"] = doc_ids[0]
    if filenames:
        meta["filenames"] = filenames
        meta["filename"] = filenames[0]

    return meta


def _ensure_generation_model_available(db: Session, user_id: str) -> None:
    cs = ConfigService(db)
    result = cs.test_api_connection(user_id, service="qwen")
    if not result.get("success"):
        message = result.get("message") or "模型不可用"
        raise HTTPException(status_code=400, detail=f"大模型不可用，请先检查配置：{message}")


@router.get("/")
async def list_testsets(
    skip: int = 0,
    limit: int = 100,
    document_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取测试集列表"""
    query = db.query(TestSetModel).filter(TestSetModel.user_id == current_user.id)
    
    if document_id:
        query = query.filter(TestSetModel.document_id == str(document_id))
    
    total = query.count()
    testsets = query.order_by(TestSetModel.create_time.desc()).offset(skip).limit(limit).all()
    
    items = []
    for t in testsets:
        answered_questions = db.query(Question).filter(
            Question.testset_id == t.id,
            Question.answer.isnot(None),
            Question.answer != ""
        ).count()
        total_questions = t.question_count or 0
        can_evaluate = total_questions > 0 and answered_questions >= total_questions

        latest_eval = db.query(EvaluationModel).filter(
            EvaluationModel.testset_id == str(t.id),
            EvaluationModel.status == 'completed'
        ).order_by(EvaluationModel.timestamp.desc()).first()

        is_evaluated = latest_eval is not None
        if is_evaluated:
            eval_status = "evaluated"
        elif can_evaluate:
            eval_status = "evaluable"
        else:
            eval_status = "not_evaluable"

        items.append({
            "id": t.id,
            "document_id": t.document_id,
            "name": t.name,
            "description": t.description,
            "question_count": total_questions,
            "answered_questions": answered_questions,
            "can_evaluate": can_evaluate,
            "eval_status": eval_status,
            "question_types": t.question_types,
            "generation_method": t.generation_method,
            "create_time": t.create_time.isoformat() if t.create_time else None,
            "file_path": t.file_path,
            "metadata": t.testset_metadata
        })

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/import")
async def import_testset_csv(
    file: UploadFile = File(...),
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    document_id: Optional[UUID] = Form(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """上传并导入测试集CSV（支持model_answer列用于可评估测试集）。"""
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="仅支持CSV文件导入")

    if document_id:
        document = db.query(Document).filter(
            Document.id == str(document_id),
            Document.user_id == current_user.id
        ).first()
        if not document:
            raise HTTPException(status_code=404, detail="关联文档不存在或无权限")
    else:
        document = db.query(Document).filter(
            Document.user_id == current_user.id
        ).order_by(Document.created_at.desc()).first()
        if not document:
            raise HTTPException(status_code=400, detail="请先上传至少一个文档后再导入测试集")

    raw = await file.read()
    text = None
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="CSV编码不支持，请使用UTF-8或GBK")

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV缺少表头")

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV中没有可导入的数据")

    parsed_questions = []

    def _pick_value(data: Dict[str, Any], *keys: str) -> str:
        for key in keys:
            value = data.get(key)
            if value is not None and str(value).strip():
                return str(value).strip()
        return ""

    for row in rows:
        question_text = _pick_value(row, "question", "问题")
        if not question_text:
            continue

        input_type = _pick_value(row, "question_type", "问题类型")
        n_type, n_major, n_minor = _normalize_question_category(input_type, None, None)
        expected_answer = _pick_value(row, "expected_answer", "参考答案")
        answer = _pick_value(row, "model_answer", "answer", "模型答案")
        context = _pick_value(row, "context", "切片内容")
        source_document = _pick_value(row, "source_document", "来源文档")
        persona_profile = _pick_value(row, "persona_profile", "角色画像")

        metadata: Dict[str, Any] = {}
        if source_document:
            metadata["source_document"] = source_document
            metadata["filenames"] = [item.strip() for item in source_document.split("|") if item.strip()]
        if persona_profile:
            metadata["persona_profile"] = persona_profile

        parsed_questions.append({
            "question": question_text,
            "question_type": n_type,
            "category_major": n_major,
            "category_minor": n_minor,
            "expected_answer": expected_answer,
            "answer": answer,
            "context": context,
            "metadata": metadata
        })

    if not parsed_questions:
        raise HTTPException(status_code=400, detail="CSV中未找到有效问题，请确认包含问题列")

    question_type_count: Dict[str, int] = {}
    answered_count = 0
    for item in parsed_questions:
        qt = item["question_type"] or "未分类"
        question_type_count[qt] = question_type_count.get(qt, 0) + 1
        if item["answer"]:
            answered_count += 1

    testset_name = (name or "").strip() or f"导入测试集_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    testset_description = (description or "").strip() or "通过CSV导入的测试集"
    testset = TestSetModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        document_id=document.id,
        name=testset_name,
        description=testset_description,
        question_count=len(parsed_questions),
        question_types=question_type_count,
        generation_method="csv_import",
        file_path=filename,
        testset_metadata={
            "imported": True,
            "source_file": filename,
            "has_model_answers": answered_count == len(parsed_questions),
            "answered_questions": answered_count
        }
    )
    db.add(testset)

    for item in parsed_questions:
        question = Question(
            id=str(uuid.uuid4()),
            testset_id=testset.id,
            question=item["question"],
            question_type=item["question_type"],
            expected_answer=item["expected_answer"],
            answer=item["answer"],
            context=item["context"],
            question_metadata=item["metadata"] or None,
            category_major=item["category_major"],
            category_minor=item["category_minor"]
        )
        db.add(question)

    db.commit()
    db.refresh(testset)

    return {
        "id": testset.id,
        "document_id": testset.document_id,
        "name": testset.name,
        "description": testset.description,
        "question_count": testset.question_count,
        "answered_questions": answered_count,
        "can_evaluate": answered_count == len(parsed_questions),
        "generation_method": testset.generation_method,
        "create_time": testset.create_time.isoformat() if testset.create_time else None,
        "message": "测试集导入成功"
    }


@router.get("/{testset_id}")
async def get_testset(
    testset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取特定测试集信息"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    questions = db.query(Question).filter(Question.testset_id == str(testset_id)).all()
    
    return {
        "id": testset.id,
        "document_id": testset.document_id,
        "name": testset.name,
        "description": testset.description,
        "question_count": testset.question_count,
        "question_types": testset.question_types,
        "generation_method": testset.generation_method,
        "create_time": testset.create_time.isoformat() if testset.create_time else None,
        "file_path": testset.file_path,
        "questions": [
            {
                "id": q.id,
                "question": q.question,
                "question_type": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[0],
                "category_major": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[1],
                "category_minor": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[2],
                "expected_answer": q.expected_answer,
                "context": q.context
            }
            for q in questions
        ]
    }


@router.post("/")
async def create_testset(
    testset_data: TestSetCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建新测试集"""
    document = db.query(Document).filter(Document.id == str(testset_data.document_id)).first()
    if not document:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    testset = TestSetModel(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        document_id=str(testset_data.document_id),
        name=testset_data.name,
        description=testset_data.description,
        question_count=0,
        generation_method=testset_data.generation_method or "qwen_model",
        testset_metadata=testset_data.metadata if hasattr(testset_data, 'metadata') else None
    )
    
    db.add(testset)
    db.commit()
    db.refresh(testset)
    
    return {
        "id": testset.id,
        "document_id": testset.document_id,
        "name": testset.name,
        "description": testset.description,
        "question_count": testset.question_count,
        "generation_method": testset.generation_method,
        "create_time": testset.create_time.isoformat() if testset.create_time else None,
        "message": "测试集创建成功"
    }


@router.put("/{testset_id}")
async def update_testset(
    testset_id: UUID,
    testset_update: TestSetUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新测试集信息"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    update_data = testset_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(testset, field, value)
    
    db.commit()
    db.refresh(testset)
    
    return {
        "id": testset.id,
        "name": testset.name,
        "description": testset.description,
        "question_count": testset.question_count,
        "message": "测试集更新成功"
    }


@router.delete("/{testset_id}")
async def delete_testset(
    testset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除测试集"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    db.query(Question).filter(Question.testset_id == str(testset_id)).delete()
    
    db.delete(testset)
    db.commit()
    
    return {"message": "测试集已删除", "id": str(testset_id)}


@router.get("/{testset_id}/questions")
async def get_testset_questions(
    testset_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取测试集中的问题列表"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    total = db.query(Question).filter(Question.testset_id == str(testset_id)).count()
    questions = db.query(Question).filter(
        Question.testset_id == str(testset_id)
    ).offset(skip).limit(limit).all()
    
    return {
        "testset_id": str(testset_id),
        "total": total,
        "items": [
            {
                "id": q.id,
                "question": q.question,
                "question_type": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[0],
                "category_major": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[1],
                "category_minor": _normalize_question_category(q.question_type, q.category_major, q.category_minor)[2],
                "expected_answer": q.expected_answer,
                "answer": q.answer,
                "context": q.context
            }
            for q in questions
        ]
    }


from pydantic import BaseModel

class GenerateQuestionsRequest(BaseModel):
    num_questions: int = 5
    question_types: Optional[str] = None
    generation_mode: Optional[str] = "advanced"
    enable_safety_robustness: bool = True
    multi_doc_ratio: float = 0.1
    document_ids: Optional[List[UUID]] = None
    persona_list: Optional[List[Dict[str, Any]]] = None


def _run_generation_task(
    task_id: str,
    testset_id: str,
    user_id: str,
    num_questions: int,
    question_types: Optional[str],
    generation_mode: str,
    enable_safety_robustness: bool,
    multi_doc_ratio: float,
    document_ids: Optional[List[str]],
    persona_list: Optional[List[Dict[str, Any]]]
):
    """后台任务：生成测试问题"""
    db = SessionLocal()
    try:
        # 仅保留 qwen_llm 生成分支
        generation_mode = "advanced"
        task_manager.update_status(task_id, "running")
        task_manager.append_log(task_id, "开始生成测试问题...")
        
        testset = db.query(TestSetModel).filter(
            TestSetModel.id == testset_id,
            TestSetModel.user_id == user_id
        ).first()
        
        if not testset:
            task_manager.fail_task(task_id, "测试集不存在")
            return
        
        from models.database import DocumentChunk as ChunkModel
        target_doc_ids = [testset.document_id]
        if document_ids:
            for doc_id in document_ids:
                if doc_id and doc_id not in target_doc_ids:
                    target_doc_ids.append(doc_id)

        documents = db.query(Document).filter(
            Document.id.in_(target_doc_ids),
            Document.user_id == user_id
        ).all()
        documents_map = {str(d.id): d for d in documents}
        if len(documents_map) != len(target_doc_ids):
            task_manager.fail_task(task_id, "存在无权限或不存在的文档")
            return

        content_data = []
        total_chunks = 0
        for doc_id in target_doc_ids:
            document = documents_map.get(doc_id)
            if not document:
                continue
            chunks = db.query(ChunkModel).filter(
                ChunkModel.document_id == document.id
            ).order_by(ChunkModel.sequence_number.asc()).all()
            if not chunks:
                if not document.is_analyzed:
                    task_manager.fail_task(task_id, f"文档尚未分析：{document.filename}")
                else:
                    task_manager.fail_task(task_id, f"文档缺少切片数据，请重新分析：{document.filename}")
                return
            if chunks:
                content_data.extend([{
                    "content": c.content,
                    "doc_id": str(document.id),
                    "filename": document.filename,
                    "chunk_id": str(c.id),
                    "metadata": c.chunk_metadata or {},
                    "sequence_number": c.sequence_number,
                    "start_char": c.start_char,
                    "end_char": c.end_char
                } for c in chunks])
                total_chunks += len(chunks)
                continue
        task_manager.append_log(
            task_id,
            f"已准备 {len(target_doc_ids)} 个文档，切片 {total_chunks} 个"
        )
        if not content_data:
            task_manager.fail_task(task_id, "未获取到可用于生成的问题素材")
            return

        types_list = [t.strip() for t in question_types.split(",")] if question_types else None
        generator = get_question_generator()
        created_questions = []
        
        if generation_mode == "advanced":
            task_manager.append_log(task_id, f"使用{generation_mode}模式生成问题...")
            
            import re
            def _progress_callback(payload):
                text = str(payload or "")
                task_manager.append_log(task_id, text)
                m = re.search(r"第\s*(\d+)\s*/\s*(\d+)\s*题", text)
                if m:
                    cur = int(m.group(1))
                    tot = max(int(m.group(2)), 1)
                    task_manager.update_progress(task_id, cur / tot, f"生成进度 {cur}/{tot}")

            params = {
                "testset_size": num_questions,
                "enable_safety_robustness": enable_safety_robustness,
                "generation_mode": "qwen_llm",
                "multi_doc_ratio": multi_doc_ratio,
                "language": "chinese",
                "chunk_size": 512,
                "persona_list": persona_list or [],
                "question_types": types_list,
                "user_id": user_id,
                "_progress_callback": _progress_callback
            }
            
            import asyncio
            generated_questions = asyncio.run(generator.generate_advanced_questions(content_data, params))
            questions_list = generated_questions.get("questions", []) if isinstance(generated_questions, dict) else generated_questions
            for q in questions_list:
                if len(created_questions) >= num_questions:
                    break
                normalized_type, normalized_major, normalized_minor = _normalize_question_category(
                    q.get("question_type"),
                    q.get("category_major"),
                    q.get("category_minor")
                )
                question_metadata = _build_question_metadata(q)
                question = Question(
                    id=str(uuid.uuid4()),
                    testset_id=testset_id,
                    question=q.get("question", ""),
                    question_type=normalized_type,
                    expected_answer=q.get("expected_answer", ""),
                    context=q.get("context", ""),
                    question_metadata=question_metadata or None,
                    category_major=normalized_major,
                    category_minor=normalized_minor
                )
                db.add(question)
                created_questions.append({
                    "id": question.id,
                    "question": question.question,
                    "question_type": question.question_type,
                    "expected_answer": question.expected_answer,
                    "context": question.context,
                    "metadata": question_metadata
                })
        
        testset.question_count = len(created_questions)
        db.commit()
        
        if len(created_questions) == 0:
            task_manager.fail_task(task_id, "未能生成任何问题，请检查LLM配置是否正确")
            return
        
        task_manager.finish_task(
            task_id,
            result={
                "questions": created_questions,
                "generation_mode": generation_mode,
                "testset_id": testset_id
            },
            message=f"成功生成 {len(created_questions)} 个问题"
        )
        task_manager.append_log(task_id, f"生成完成，共 {len(created_questions)} 个问题")
        
    except Exception as e:
        task_manager.fail_task(task_id, str(e))
        task_manager.append_log(task_id, f"生成失败: {e}")
    finally:
        db.close()


@router.post("/{testset_id}/generate_async")
async def generate_questions_async(
    testset_id: UUID,
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """异步生成测试问题 - 返回任务ID，前端轮询状态"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    document = db.query(Document).filter(Document.id == testset.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="关联文档不存在")

    _ensure_generation_model_available(db, str(current_user.id))
    
    task_id = task_manager.create_task(
        task_type="generate_questions",
        params={
            "testset_id": str(testset_id),
            "num_questions": request.num_questions,
            "generation_mode": request.generation_mode,
            "document_ids": [str(doc_id) for doc_id in request.document_ids] if request.document_ids else None
        }
    )
    
    thread = threading.Thread(
        target=_run_generation_task,
        args=(
            task_id,
            str(testset_id),
            str(current_user.id),
            request.num_questions,
            request.question_types,
            request.generation_mode,
            request.enable_safety_robustness,
            request.multi_doc_ratio,
            [str(doc_id) for doc_id in request.document_ids] if request.document_ids else None,
            request.persona_list
        ),
        daemon=True
    )
    thread.start()
    
    return {
        "task_id": task_id,
        "message": "任务已创建，请轮询状态接口获取进度"
    }


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取异步任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


@router.post("/{testset_id}/generate")
async def generate_questions(
    testset_id: UUID,
    request: GenerateQuestionsRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """生成测试问题"""
    num_questions = request.num_questions
    question_types = request.question_types
    generation_mode = request.generation_mode
    enable_safety_robustness = request.enable_safety_robustness
    multi_doc_ratio = request.multi_doc_ratio

    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    document = db.query(Document).filter(Document.id == testset.document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="关联文档不存在")

    _ensure_generation_model_available(db, str(current_user.id))
    
    if not document.is_analyzed:
        raise HTTPException(status_code=400, detail="文档尚未分析，请先分析文档")
    
    from models.database import DocumentChunk as ChunkModel
    chunks = db.query(ChunkModel).filter(ChunkModel.document_id == document.id).order_by(ChunkModel.sequence_number.asc()).all()
    
    if not chunks:
        raise HTTPException(status_code=400, detail="文档缺少切片数据，请重新分析后再生成测试集")

    content_data = [{
        "content": c.content,
        "doc_id": str(document.id),
        "filename": document.filename,
        "chunk_id": str(c.id),
        "metadata": c.chunk_metadata or {},
        "sequence_number": c.sequence_number,
        "start_char": c.start_char,
        "end_char": c.end_char
    } for c in chunks]
    logger.info(f"使用文档切片数据，共 {len(content_data)} 个切片")
    
    types_list = None
    if question_types:
        types_list = [t.strip() for t in question_types.split(",")]
    
    try:
        generator = get_question_generator()
        created_questions = []
        
        generation_mode = "advanced"
        if generation_mode == "advanced":
            params = {
                "testset_size": num_questions,
                "enable_safety_robustness": enable_safety_robustness,
                "generation_mode": "qwen_llm",
                "multi_doc_ratio": multi_doc_ratio,
                "language": "chinese",
                "persona_list": [],
                "question_types": types_list,
                "user_id": str(current_user.id)
            }
            
            generated_questions = await generator.generate_advanced_questions(
                content_data,
                params
            )
            
            questions_list = generated_questions.get("questions", []) if isinstance(generated_questions, dict) else generated_questions
            
            for q in questions_list:
                if len(created_questions) >= num_questions:
                    break
                    
                normalized_type, normalized_major, normalized_minor = _normalize_question_category(
                    q.get("question_type"),
                    q.get("category_major"),
                    q.get("category_minor")
                )
                question_metadata = _build_question_metadata(q)
                question = Question(
                    id=str(uuid.uuid4()),
                    testset_id=str(testset_id),
                    question=q.get("question", ""),
                    question_type=normalized_type,
                    expected_answer=q.get("expected_answer", ""),
                    context=q.get("context", ""),
                    question_metadata=question_metadata or None,
                    category_major=normalized_major,
                    category_minor=normalized_minor
                )
                db.add(question)
                created_questions.append({
                    "id": question.id,
                    "question": question.question,
                    "question_type": question.question_type,
                    "expected_answer": question.expected_answer,
                    "context": question.context,
                    "metadata": question_metadata
                })
        
        testset.question_count = len(created_questions)
        db.commit()
        
        if len(created_questions) == 0:
            raise HTTPException(
                status_code=500, 
                detail="未能生成任何问题，请检查LLM配置是否正确（DASHSCOPE_API_KEY或QWEN_API_KEY）"
            )
        
        return {
            "message": f"成功生成 {len(created_questions)} 个问题",
            "questions": created_questions,
            "generation_mode": generation_mode,
            "enable_safety_robustness": enable_safety_robustness,
            "multi_doc_ratio": multi_doc_ratio
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成问题失败: {str(e)}")


@router.post("/{testset_id}/questions")
async def add_question(
    testset_id: UUID,
    question_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """手动添加问题"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    normalized_type, normalized_major, normalized_minor = _normalize_question_category(
        question_data.get("question_type"),
        question_data.get("category_major"),
        question_data.get("category_minor")
    )
    question = Question(
        id=str(uuid.uuid4()),
        testset_id=str(testset_id),
        question=question_data.get("question", ""),
        question_type=normalized_type,
        expected_answer=question_data.get("expected_answer", ""),
        context=question_data.get("context", ""),
        category_major=normalized_major,
        category_minor=normalized_minor
    )
    
    db.add(question)
    testset.question_count = (testset.question_count or 0) + 1
    db.commit()
    db.refresh(question)
    
    return {
        "id": question.id,
        "question": question.question,
        "question_type": question.question_type,
        "expected_answer": question.expected_answer,
        "context": question.context
    }


@router.put("/{testset_id}/questions/{question_id}")
async def update_question(
    testset_id: UUID,
    question_id: UUID,
    question_data: dict,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """更新问题"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    question = db.query(Question).filter(
        Question.id == str(question_id),
        Question.testset_id == str(testset_id)
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="问题不存在")
    
    if any(k in question_data for k in ["question_type", "category_major", "category_minor"]):
        n_type, n_major, n_minor = _normalize_question_category(
            question_data.get("question_type", question.question_type),
            question_data.get("category_major", question.category_major),
            question_data.get("category_minor", question.category_minor),
        )
        question.question_type = n_type
        question.category_major = n_major
        question.category_minor = n_minor
    for field, value in question_data.items():
        if field in ["question_type", "category_major", "category_minor"]:
            continue
        if hasattr(question, field):
            setattr(question, field, value)
    
    db.commit()
    db.refresh(question)
    
    return {
        "id": question.id,
        "question": question.question,
        "question_type": question.question_type,
        "expected_answer": question.expected_answer,
        "context": question.context
    }


@router.delete("/{testset_id}/questions/{question_id}")
async def delete_question(
    testset_id: UUID,
    question_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除问题"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    question = db.query(Question).filter(
        Question.id == str(question_id),
        Question.testset_id == str(testset_id)
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="问题不存在")
    
    db.delete(question)
    testset.question_count = max(0, (testset.question_count or 0) - 1)
    db.commit()
    
    return {"message": "问题已删除", "id": str(question_id)}


@router.get("/advanced/config")
async def get_advanced_config(
    current_user: User = Depends(get_current_active_user)
):
    """获取高级功能配置"""
    # 返回原始代码库中的分类体系
    from services.advanced_testset_generator import advanced_testset_generator
    taxonomy = advanced_testset_generator.get_qwen_taxonomy()
    
    return {
        "taxonomy": taxonomy,
        "strategies": [
            {"id": "deep_dive", "name": "深度挖掘", "description": "基于同一文档的多个切片生成关联问题"},
            {"id": "cross_product", "name": "跨产品比较", "description": "基于不同文档的相似内容生成对比问题"},
            {"id": "theme_chain", "name": "主题链", "description": "基于文档间的主题关联生成问题"}
        ],
        "features": {
            "advanced_generation": True,
            "multidoc_support": True,
            "persona_matching": True,
            "product_extraction": True,
            "safety_robustness": True
        }
    }


@router.get("/{testset_id}/export")
async def export_testset(
    testset_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """导出测试集"""
    testset = db.query(TestSetModel).filter(
        TestSetModel.id == str(testset_id),
        TestSetModel.user_id == current_user.id
    ).first()
    
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    questions = db.query(Question).filter(Question.testset_id == str(testset_id)).all()
    main_document = None
    if testset.document_id:
        main_document = db.query(Document).filter(Document.id == testset.document_id).first()
    doc_ids_in_meta = set()
    for q in questions:
        meta = q.question_metadata if isinstance(q.question_metadata, dict) else {}
        doc_ids = meta.get("doc_ids") or meta.get("document_ids") or []
        if isinstance(doc_ids, list):
            for d in doc_ids:
                if d:
                    doc_ids_in_meta.add(str(d))
        one_doc_id = meta.get("doc_id")
        if one_doc_id:
            doc_ids_in_meta.add(str(one_doc_id))
    if testset.document_id:
        doc_ids_in_meta.add(str(testset.document_id))
    document_name_map = {}
    if doc_ids_in_meta:
        docs = db.query(Document).filter(Document.id.in_(list(doc_ids_in_meta))).all()
        document_name_map = {str(d.id): (d.filename or "") for d in docs}
    
    latest_eval = db.query(EvaluationModel).filter(
        EvaluationModel.testset_id == str(testset_id),
        EvaluationModel.status == 'completed'
    ).order_by(EvaluationModel.timestamp.desc()).first()

    base_headers = ["问题ID", "问题", "问题类型", "参考答案", "模型答案", "切片内容", "来源文档", "角色画像"]
    metrics_headers = []
    eval_results_map = {}
    
    if latest_eval:
        metrics_headers = latest_eval.evaluation_metrics or []
        results = db.query(EvaluationResultModel).filter(
            EvaluationResultModel.evaluation_id == latest_eval.id
        ).all()
        for r in results:
            eval_results_map[r.question_id] = r

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(base_headers + metrics_headers)
    for q in questions:
        normalized_type, normalized_major, normalized_minor = _normalize_question_category(
            q.question_type, q.category_major, q.category_minor
        )
        if normalized_major and normalized_minor:
            unified_question_type = f"{normalized_major}-{normalized_minor}"
        elif normalized_minor:
            unified_question_type = normalized_minor
        elif normalized_major:
            unified_question_type = normalized_major
        else:
            unified_question_type = normalized_type or ""

        meta = q.question_metadata if isinstance(q.question_metadata, dict) else {}
        source_document = ""
        filenames = meta.get("filenames")
        if isinstance(filenames, list):
            source_document = " | ".join([str(x).strip() for x in filenames if str(x).strip()])
        if not source_document:
            source_document = str(meta.get("filename") or "").strip()
        if not source_document:
            source_documents = meta.get("source_documents")
            if isinstance(source_documents, list):
                source_document = " | ".join([str(x).strip() for x in source_documents if str(x).strip()])
            elif isinstance(source_documents, str):
                source_document = source_documents.strip()
        if not source_document:
            ids = meta.get("doc_ids") or meta.get("document_ids") or []
            if not isinstance(ids, list):
                ids = [ids] if ids else []
            one_doc_id = meta.get("doc_id")
            if one_doc_id:
                ids.append(one_doc_id)
            names = [document_name_map.get(str(d), "").strip() for d in ids if str(d).strip()]
            names = [n for n in names if n]
            if names:
                source_document = " | ".join(list(dict.fromkeys(names)))
        if not source_document and main_document and main_document.filename:
            source_document = main_document.filename

        persona_profile = ""
        persona_name = str(meta.get("persona_name") or "").strip()
        persona_description = str(meta.get("persona_description") or "").strip()
        if persona_name and persona_description:
            persona_profile = f"{persona_name}：{persona_description}"
        elif persona_name:
            persona_profile = persona_name
        elif persona_description:
            persona_profile = persona_description

        row_data = [
            q.id,
            q.question or "",
            unified_question_type,
            q.expected_answer or "",
            q.answer or "",
            q.context or "",
            source_document,
            persona_profile
        ]

        if latest_eval:
            r = eval_results_map.get(str(q.id))
            metrics_dict = r.metrics if r and isinstance(r.metrics, dict) else {}
            for m in metrics_headers:
                val = metrics_dict.get(m, "")
                row_data.append(str(val) if val is not None else "")

        writer.writerow(row_data)

    csv_content = output.getvalue()
    output.close()

    if latest_eval:
        method_raw = latest_eval.evaluation_method or ""
        if "ragas" in method_raw.lower():
            method_name = "Ragas"
        elif "deepeval" in method_raw.lower():
            method_name = "DeepEval"
        else:
            method_name = method_raw
        filename = f"{(testset.name or 'testset').replace(' ', '_')}({method_name}).csv"
    else:
        filename = f"{(testset.name or 'testset').replace(' ', '_')}.csv"
        
    ascii_filename = "".join(ch if ord(ch) < 128 else "_" for ch in filename)
    encoded_filename = quote(filename)
    headers = {
        "Content-Disposition": f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
    }
    return StreamingResponse(iter([csv_content]), media_type="text/csv; charset=utf-8", headers=headers)
