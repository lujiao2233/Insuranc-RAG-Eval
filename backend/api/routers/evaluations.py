"""评估管理API路由
处理评估任务创建、查询、执行等操作
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import json

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db
from schemas import EvaluationCreate
from models.database import User, Evaluation as EvaluationModel, EvaluationResult as EvaluationResultModel
from models.database import TestSet, Question
from services.task_manager import task_manager
from services.ragas_evaluator import evaluator

router = APIRouter()


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
        task_manager.update_progress(task_id, 0.1, "准备评估数据")
        
        question_data = []
        for q in questions:
            question_data.append({
                "id": q.id,
                "question": q.question,
                "expected_answer": q.expected_answer or "",
                "answer": q.answer or "",
                "context": q.context or "",
                "question_type": q.question_type
            })
        
        task_manager.append_log(task_id, f"使用 {evaluation_method} 引擎进行评估")
        task_manager.update_progress(task_id, 0.2, "开始评估")
        
        run_config = {
            "timeout": 300,
            "max_workers": 4
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
        
        task_manager.update_progress(task_id, 0.8, "保存评估结果")
        task_manager.append_log(task_id, f"评估完成，保存 {len(result.get('individual_results', []))} 个结果")
        
        for idx, individual_result in enumerate(result.get("individual_results", [])):
            question_id = individual_result.get("question_id")
            
            eval_result = EvaluationResultModel(
                evaluation_id=evaluation_id,
                question_id=question_id,
                question_text=individual_result.get("question", ""),
                expected_answer=individual_result.get("expected_answer", ""),
                generated_answer=individual_result.get("generated_answer", ""),
                context=individual_result.get("context", ""),
                metrics=individual_result.get("metrics", {})
            )
            db.add(eval_result)
            
            if question_id:
                question = db.query(Question).filter(Question.id == question_id).first()
                if question and individual_result.get("generated_answer"):
                    question.answer = individual_result.get("generated_answer")
        
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
    query = db.query(EvaluationModel).filter(EvaluationModel.user_id == current_user.id)
    
    if status:
        query = query.filter(EvaluationModel.status == status)
    
    total = query.count()
    evaluations = query.order_by(EvaluationModel.timestamp.desc()).offset(skip).limit(limit).all()
    
    return {
        "items": [
            {
                "id": e.id,
                "testset_id": e.testset_id,
                "evaluation_method": e.evaluation_method,
                "total_questions": e.total_questions,
                "evaluated_questions": e.evaluated_questions,
                "status": e.status,
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
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
    unanswered_count = db.query(Question).filter(
        Question.testset_id == str(evaluation_data.testset_id),
        ((Question.answer.is_(None)) | (Question.answer == ""))
    ).count()
    if unanswered_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"测试集中有 {unanswered_count} 个问题未填充模型答案，无法评估。请先导出并填充后重新上传。"
        )
    
    evaluation = EvaluationModel(
        user_id=current_user.id,
        testset_id=str(evaluation_data.testset_id),
        evaluation_method=evaluation_data.evaluation_method or "ragas_official",
        total_questions=question_count,
        evaluated_questions=0,
        evaluation_metrics=evaluation_data.evaluation_metrics or ["answer_relevance", "faithfulness"],
        eval_config=evaluation_data.eval_config or {},
        status="pending"
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    
    task_id = task_manager.create_task(
        task_type="evaluation",
        params={
            "evaluation_id": evaluation.id,
            "testset_id": str(evaluation_data.testset_id),
            "evaluation_method": evaluation.evaluation_method
        }
    )
    
    from config.settings import settings
    task_manager.start_task(
        task_id,
        run_evaluation_task,
        task_id,
        evaluation.id,
        str(evaluation_data.testset_id),
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
    
    return {
        "evaluation_id": str(evaluation_id),
        "total": total,
        "items": [
            {
                "id": r.id,
                "question_id": r.question_id,
                "question_text": r.question_text,
                "expected_answer": r.expected_answer,
                "generated_answer": r.generated_answer,
                "context": r.context,
                "metrics": r.metrics
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
