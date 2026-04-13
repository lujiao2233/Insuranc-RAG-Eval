"""评估管理API路由
处理评估任务创建、查询、执行等操作
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime
import json
import uuid

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db
from schemas import EvaluationCreate
from models.database import User, Evaluation as EvaluationModel, EvaluationResult as EvaluationResultModel
from models.database import TestSet, Question
from services.task_manager import task_manager
from services.ragas_evaluator import evaluator

router = APIRouter()
EXECUTION_EVAL_METHOD = "testset_execution"


def _short_display_name(name: str, max_len: int = 24) -> str:
    text = str(name or "").strip()
    if not text:
        return "测试集"
    return text if len(text) <= max_len else f"{text[:max_len]}..."


def _next_report_no(db: Session, user_id: str, execution_testset_id: str) -> int:
    all_sets = db.query(TestSet).filter(TestSet.user_id == user_id).all()
    max_no = 0
    for item in all_sets:
        meta = item.testset_metadata if isinstance(item.testset_metadata, dict) else {}
        if str(meta.get("lifecycle_stage") or "").strip().lower() != "report":
            continue
        if str(meta.get("source_testset_id") or "") != execution_testset_id:
            continue
        current_no = int(meta.get("evaluation_no") or 0)
        if current_no > max_no:
            max_no = current_no
    return max_no + 1


def _load_execution_answer_map(db: Session, testset_id: str, user_id: str):
    latest_execution = db.query(EvaluationModel).filter(
        EvaluationModel.testset_id == testset_id,
        EvaluationModel.user_id == user_id,
        EvaluationModel.status == "completed",
        EvaluationModel.evaluation_method == EXECUTION_EVAL_METHOD
    ).order_by(EvaluationModel.timestamp.desc()).first()
    if not latest_execution:
        return {}, None

    rows = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == latest_execution.id
    ).all()
    answer_map: Dict[str, EvaluationResultModel] = {}
    for row in rows:
        if row.question_id:
            answer_map[str(row.question_id)] = row
    return answer_map, str(latest_execution.id)


def _clone_to_report_testset(db: Session, source_testset: TestSet, user_id: str, source_execution_id: Optional[str]) -> TestSet:
    source_meta = source_testset.testset_metadata if isinstance(source_testset.testset_metadata, dict) else {}
    root_testset_id = str(source_meta.get("root_testset_id") or source_testset.id)
    root_name = str(source_meta.get("root_name") or source_testset.name or "测试集")
    execution_no = int(source_meta.get("execution_no") or 1)
    report_no = _next_report_no(db, user_id, str(source_testset.id))
    display_name = f"{_short_display_name(root_name)}#E{execution_no:02d}#R{report_no:02d}"
    report_meta = {
        **source_meta,
        "lifecycle_stage": "report",
        "root_testset_id": root_testset_id,
        "root_name": root_name,
        "execution_no": execution_no,
        "evaluation_no": report_no,
        "display_name": display_name,
        "source_testset_id": str(source_testset.id),
        "source_execution_id": source_execution_id,
        "report_created_at": datetime.now().isoformat()
    }

    cloned = TestSet(
        id=str(uuid.uuid4()),
        user_id=user_id,
        document_id=source_testset.document_id,
        name=display_name,
        description=source_testset.description,
        question_count=source_testset.question_count,
        question_types=source_testset.question_types,
        generation_method=source_testset.generation_method or "qwen_model",
        file_path=source_testset.file_path,
        testset_metadata=report_meta
    )
    db.add(cloned)
    db.flush()

    source_questions = db.query(Question).filter(Question.testset_id == str(source_testset.id)).all()
    for q in source_questions:
        source_meta = q.question_metadata if isinstance(q.question_metadata, dict) else {}
        cloned_meta = {
            **source_meta,
            "source_question_id": str(q.id)
        }
        cloned_q = Question(
            id=str(uuid.uuid4()),
            testset_id=cloned.id,
            question=q.question,
            question_type=q.question_type,
            category_major=q.category_major,
            category_minor=q.category_minor,
            expected_answer=q.expected_answer,
            answer=None,
            context=q.context,
            question_metadata=cloned_meta
        )
        db.add(cloned_q)

    return cloned


def run_evaluation_task(
    task_id: str,
    evaluation_id: str,
    testset_id: str,
    evaluation_method: str,
    evaluation_metrics: List[str],
    db_url: str
):
    """后台任务：执行评估"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        task_manager.update_status(task_id, "running")
        task_manager.append_log(task_id, f"开始评估任务: {evaluation_id}")
        
        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == evaluation_id).first()
        if not evaluation:
            task_manager.fail_task(task_id, "评估记录不存在")
            return
        
        evaluation.status = "running"
        db.commit()
        
        testset = db.query(TestSet).filter(TestSet.id == testset_id).first()
        if not testset:
            evaluation.status = "failed"
            evaluation.error_message = "测试集不存在"
            db.commit()
            task_manager.fail_task(task_id, "测试集不存在")
            return
        
        questions = db.query(Question).filter(Question.testset_id == testset_id).all()
        if not questions:
            evaluation.status = "failed"
            evaluation.error_message = "测试集中没有问题"
            db.commit()
            task_manager.fail_task(task_id, "测试集中没有问题")
            return
        
        task_manager.append_log(task_id, f"加载了 {len(questions)} 个问题")
        def sync_estimated_progress(progress_ratio: float, message: str):
            ratio = max(0.0, min(float(progress_ratio or 0.0), 1.0))
            task_manager.update_progress(task_id, ratio, message)
            try:
                evaluation.evaluated_questions = min(
                    len(questions),
                    max(0, int(round(ratio * len(questions))))
                )
                db.commit()
            except Exception:
                db.rollback()

        sync_estimated_progress(0.1, "准备评估数据")
        execution_answer_map: Dict[str, EvaluationResultModel] = {}
        source_execution_id = None
        if isinstance(evaluation.eval_config, dict):
            source_execution_id = evaluation.eval_config.get("source_execution_id")
        if source_execution_id:
            rows = db.query(EvaluationResultModel).filter(
                EvaluationResultModel.evaluation_id == str(source_execution_id)
            ).all()
            for row in rows:
                if row.question_id:
                    execution_answer_map[str(row.question_id)] = row
        
        question_data = []
        for q in questions:
            source_qid = None
            if isinstance(q.question_metadata, dict):
                source_qid = q.question_metadata.get("source_question_id")
            execution_row = execution_answer_map.get(str(source_qid)) if source_qid else None
            if execution_row is None:
                execution_row = execution_answer_map.get(str(q.id))
            question_data.append({
                "id": q.id,
                "question": q.question,
                "expected_answer": q.expected_answer or "",
                "answer": (execution_row.generated_answer if execution_row else None) or q.answer or "",
                "context": (execution_row.context if execution_row else None) or q.context or "",
                "question_type": q.question_type
            })
        
        task_manager.append_log(task_id, f"使用 {evaluation_method} 引擎进行评估")
        sync_estimated_progress(0.2, "开始评估")
        
        def on_progress(done: int, total: int):
            """评估进行中回调：同步任务进度与DB计数，供前端实时展示。"""
            safe_total = max(1, int(total or 0))
            safe_done = max(0, min(int(done or 0), safe_total))
            progress_ratio = safe_done / safe_total

            task_manager.update_progress(task_id, progress_ratio, f"评估进度: {safe_done}/{safe_total}")
            try:
                evaluation.evaluated_questions = safe_done
                db.commit()
            except Exception:
                db.rollback()

        run_config = {
            "timeout": 300,
            "max_workers": 4,
            "user_id": str(evaluation.user_id) if getattr(evaluation, "user_id", None) else None,
            "db_session": db,
            "progress_callback": on_progress,
        }
        
        result = evaluator.evaluate(
            questions=question_data,
            evaluation_metrics=evaluation_metrics,
            engine=evaluation_method if "deepeval" in evaluation_method.lower() else None,
            run_config=run_config
        )
        
        if result.get("error"):
            evaluation.status = "failed"
            evaluation.error_message = result["error"]
            db.commit()
            task_manager.fail_task(task_id, result["error"])
            return
        
        sync_estimated_progress(0.8, "保存评估结果")
        task_manager.append_log(task_id, f"评估完成，保存 {len(result.get('individual_results', []))} 个结果")
        
        eval_results_to_add = []
        for idx, individual_result in enumerate(result.get("individual_results", [])):
            question_id = individual_result.get("question_id")
            
            eval_result = EvaluationResultModel(
                evaluation_id=evaluation_id,
                question_id=question_id,
                question_text=individual_result.get("question", ""),
                expected_answer=individual_result.get("expected_answer", ""),
                generated_answer=individual_result.get("generated_answer", ""),
                context=individual_result.get("context", ""),
                metrics=individual_result.get("metrics", {}),
                reasons=individual_result.get("reasons", {})
            )
            eval_results_to_add.append(eval_result)
            
        if eval_results_to_add:
            db.add_all(eval_results_to_add)
        
        evaluation.status = "completed"
        evaluation.evaluated_questions = len(result.get("individual_results", []))
        evaluation.overall_metrics = result.get("overall_metrics", {})
        evaluation.evaluation_time = int(result.get("evaluation_time", 0))
        evaluation.evaluation_metrics = evaluation_metrics
        db.commit()
        
        task_manager.finish_task(
            task_id,
            result={"evaluation_id": evaluation_id, "overall_metrics": result.get("overall_metrics", {})},
            message="评估完成"
        )
        task_manager.append_log(task_id, f"评估任务完成，耗时 {result.get('evaluation_time', 0):.2f} 秒")
        
    except Exception as e:
        task_manager.append_log(task_id, f"评估失败: {str(e)}")
        task_manager.fail_task(task_id, str(e))
        
        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == evaluation_id).first()
        if evaluation:
            evaluation.status = "failed"
            evaluation.error_message = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/", response_model=dict)
async def list_evaluations(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取评估列表"""
    query = db.query(EvaluationModel).filter(
        EvaluationModel.user_id == current_user.id,
        EvaluationModel.evaluation_method != EXECUTION_EVAL_METHOD
    )
    
    if status:
        query = query.filter(EvaluationModel.status == status)
    
    total = query.count()
    evaluations = query.order_by(EvaluationModel.timestamp.desc()).offset(skip).limit(limit).all()
    testset_ids = {e.testset_id for e in evaluations if e.testset_id}
    testset_name_map = {}
    if testset_ids:
        testsets = db.query(TestSet.id, TestSet.name).filter(TestSet.id.in_(testset_ids)).all()
        testset_name_map = {tid: name for tid, name in testsets}
    
    return {
        "items": [
            {
                "id": e.id,
                "testset_id": e.testset_id,
                "testset_name": testset_name_map.get(e.testset_id, "未知测试集") if e.testset_id else "未知测试集",
                "evaluation_method": e.evaluation_method,
                "total_questions": e.total_questions,
                "evaluated_questions": e.evaluated_questions,
                "status": e.status,
                "timestamp": (e.timestamp or e.created_at).isoformat() if (e.timestamp or e.created_at) else None,
                "created_at": (e.created_at or e.timestamp).isoformat() if (e.created_at or e.timestamp) else None,
                "overall_metrics": e.overall_metrics
            }
            for e in evaluations
        ],
        "total": total,
        "page": skip // limit + 1,
        "size": limit,
        "pages": (total + limit - 1) // limit
    }


@router.get("/{evaluation_id}")
async def get_evaluation(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取特定评估信息"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    
    return {
        "id": evaluation.id,
        "testset_id": evaluation.testset_id,
        "evaluation_method": evaluation.evaluation_method,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "evaluation_metrics": evaluation.evaluation_metrics,
        "overall_metrics": evaluation.overall_metrics,
        "eval_config": evaluation.eval_config,
        "status": evaluation.status,
        "error_message": evaluation.error_message
    }


@router.post("/")
async def create_evaluation(
    evaluation_data: EvaluationCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """创建并启动评估任务"""
    testset = db.query(TestSet).filter(TestSet.id == str(evaluation_data.testset_id)).first()
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    
    question_count = db.query(Question).filter(Question.testset_id == str(evaluation_data.testset_id)).count()
    
    execution_answer_map, source_execution_id = _load_execution_answer_map(
        db,
        str(evaluation_data.testset_id),
        str(current_user.id)
    )
    unanswered_questions = 0
    if source_execution_id:
        questions = db.query(Question).filter(Question.testset_id == str(evaluation_data.testset_id)).all()
        for q in questions:
            row = execution_answer_map.get(str(q.id))
            if not row or not (row.generated_answer or "").strip():
                unanswered_questions += 1
    else:
        unanswered_questions = db.query(Question).filter(
            Question.testset_id == str(evaluation_data.testset_id),
            ((Question.answer.is_(None)) | (Question.answer == ""))
        ).count()
    
    if unanswered_questions > 0:
        raise HTTPException(
            status_code=400,
            detail=f"测试集中有 {unanswered_questions} 个问题缺少可评估答案，无法评估。请先执行测试集生成模型答案。"
        )

    # 评估前生成“报告阶段测试集”，用于报告中心独立展示
    report_testset = _clone_to_report_testset(
        db,
        testset,
        str(current_user.id),
        source_execution_id
    )
    db.commit()
    db.refresh(report_testset)
    
    evaluation = EvaluationModel(
        user_id=current_user.id,
        testset_id=str(report_testset.id),
        evaluation_method=evaluation_data.evaluation_method or "ragas_official",
        total_questions=question_count,
        evaluated_questions=0,
        evaluation_metrics=evaluation_data.evaluation_metrics or ["answer_relevance", "faithfulness"],
        eval_config={
            **(evaluation_data.eval_config or {}),
            **({"source_execution_id": source_execution_id} if source_execution_id else {}),
            "source_testset_id": str(evaluation_data.testset_id),
            "report_testset_id": str(report_testset.id)
        },
        status="pending"
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    
    task_id = task_manager.create_task(
        task_type="evaluation",
        params={
            "evaluation_id": evaluation.id,
            "testset_id": str(report_testset.id),
            "evaluation_method": evaluation.evaluation_method
        }
    )
    
    from config.settings import settings
    task_manager.start_task(
        task_id,
        run_evaluation_task,
        task_id,
        evaluation.id,
        str(report_testset.id),
        evaluation.evaluation_method,
        evaluation.evaluation_metrics or ["answer_relevance", "faithfulness"],
        settings.DATABASE_URL
    )
    
    return {
        "id": evaluation.id,
        "task_id": task_id,
        "status": "pending",
        "message": "评估任务已创建并开始执行"
    }


@router.get("/{evaluation_id}/results")
async def get_evaluation_results(
    evaluation_id: UUID,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取评估结果"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    
    total = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).count()
    
    results = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).offset(skip).limit(limit).all()

    question_ids = [r.question_id for r in results if r.question_id]
    questions_map = {}
    if question_ids:
        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_map = {q.id: q for q in questions}
    
    return {
        "evaluation_id": str(evaluation_id),
        "total": total,
        "items": [
            {
                "id": r.id,
                "question_id": r.question_id,
                "question_text": r.question_text,
                "question_type": questions_map.get(r.question_id).question_type if r.question_id and questions_map.get(r.question_id) else None,
                "category_major": questions_map.get(r.question_id).category_major if r.question_id and questions_map.get(r.question_id) else None,
                "category_minor": questions_map.get(r.question_id).category_minor if r.question_id and questions_map.get(r.question_id) else None,
                "expected_answer": r.expected_answer,
                "generated_answer": r.generated_answer,
                "context": r.context,
                "metrics": r.metrics,
                "reasons": r.reasons
            }
            for r in results
        ]
    }


@router.get("/{evaluation_id}/summary")
async def get_evaluation_summary(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取评估摘要统计"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    
    return {
        "evaluation_id": str(evaluation_id),
        "status": evaluation.status,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "overall_metrics": evaluation.overall_metrics,
        "evaluation_metrics": evaluation.evaluation_metrics
    }


@router.get("/task/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user)
):
    """获取任务状态"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return task


@router.delete("/{evaluation_id}")
async def delete_evaluation(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """删除评估及其结果"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估不存在")
    
    db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).delete()
    
    db.delete(evaluation)
    db.commit()
    
    return {"message": "评估已删除", "id": str(evaluation_id)}
