"""报告管理API路由
处理评估报告生成、查看、下载等操作
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from uuid import UUID
from datetime import datetime
import os

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db
from models.database import User, Evaluation as EvaluationModel, EvaluationResult as EvaluationResultModel
from models.database import TestSet
from services.report_generator import report_generator

router = APIRouter()


@router.get("/")
async def list_reports(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取报告列表（已完成评估的列表）"""
    query = db.query(EvaluationModel).filter(
        EvaluationModel.user_id == current_user.id,
        EvaluationModel.status == "completed"
    )
    
    total = query.count()
    evaluations = query.order_by(EvaluationModel.timestamp.desc()).offset(skip).limit(limit).all()
    
    reports = []
    for e in evaluations:
        testset = db.query(TestSet).filter(TestSet.id == e.testset_id).first()
        reports.append({
            "evaluation_id": e.id,
            "testset_name": testset.name if testset else "未知测试集",
            "evaluation_method": e.evaluation_method,
            "status": e.status,
            "total_questions": e.total_questions,
            "evaluated_questions": e.evaluated_questions,
            "evaluation_time": e.evaluation_time,
            "created_at": e.timestamp.isoformat() if e.timestamp else None,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            "overall_score": e.overall_metrics.get("overall_score", {}).get("mean", 0) if e.overall_metrics else 0,
            "performance_level": e.overall_metrics.get("overall_score", {}).get("interpretation", "未知") if e.overall_metrics else "未知"
        })
    
    return {
        "items": reports,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/{evaluation_id}")
async def get_report_detail(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取报告详情"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估报告不存在")

    if evaluation.status != "completed":
        raise HTTPException(status_code=400, detail="评估尚未完成，无法下载报告")
    
    testset = db.query(TestSet).filter(TestSet.id == evaluation.testset_id).first()
    
    results = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).all()
    
    individual_results = []
    for r in results:
        individual_results.append({
            "question_id": r.question_id,
            "question": r.question_text,
            "expected_answer": r.expected_answer,
            "generated_answer": r.generated_answer,
            "context": r.context,
            "metrics": r.metrics
        })
    
    return {
        "evaluation_id": evaluation.id,
        "testset_name": testset.name if testset else "未知测试集",
        "testset_id": evaluation.testset_id,
        "evaluation_method": evaluation.evaluation_method,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "evaluation_metrics": evaluation.evaluation_metrics,
        "overall_metrics": evaluation.overall_metrics,
        "individual_results": individual_results,
        "status": evaluation.status
    }


@router.get("/{evaluation_id}/summary")
async def get_report_summary(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取报告摘要"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估报告不存在")
    
    testset = db.query(TestSet).filter(TestSet.id == evaluation.testset_id).first()
    
    evaluation_result = {
        "evaluation_id": evaluation.id,
        "testset_name": testset.name if testset else "未知测试集",
        "evaluation_method": evaluation.evaluation_method,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "overall_metrics": evaluation.overall_metrics or {}
    }
    
    summary = report_generator.generate_results_summary(evaluation_result)
    
    return summary


@router.post("/{evaluation_id}/generate")
async def generate_report(
    evaluation_id: UUID,
    format: str = "html",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """生成评估报告"""
    if format.lower() not in ["pdf", "html"]:
        raise HTTPException(status_code=400, detail="不支持的报告格式，请选择PDF或HTML")
    
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估报告不存在")
    
    if evaluation.status != "completed":
        raise HTTPException(status_code=400, detail="评估尚未完成，无法生成报告")
    
    testset = db.query(TestSet).filter(TestSet.id == evaluation.testset_id).first()
    
    results = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).all()
    
    individual_results = []
    for r in results:
        individual_results.append({
            "question_id": r.question_id,
            "question": r.question_text,
            "expected_answer": r.expected_answer,
            "generated_answer": r.generated_answer,
            "context": r.context,
            "metrics": r.metrics
        })
    
    evaluation_result = {
        "evaluation_id": evaluation.id,
        "testset_name": testset.name if testset else "未知测试集",
        "evaluation_method": evaluation.evaluation_method,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "evaluation_metrics": evaluation.evaluation_metrics or [],
        "overall_metrics": evaluation.overall_metrics or {},
        "individual_results": individual_results
    }
    
    try:
        if format.lower() == "pdf":
            report_path = report_generator.generate_pdf_report(evaluation_result)
        else:
            report_path = report_generator.generate_html_report(evaluation_result)
        
        return {
            "message": "报告生成成功",
            "report_path": report_path,
            "format": format,
            "evaluation_id": str(evaluation_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告生成失败: {str(e)}")


@router.get("/{evaluation_id}/download")
async def download_report(
    evaluation_id: UUID,
    format: str = "html",
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """下载评估报告"""
    if format.lower() not in ["pdf", "html"]:
        raise HTTPException(status_code=400, detail="不支持的报告格式")
    
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估报告不存在")
    
    testset = db.query(TestSet).filter(TestSet.id == evaluation.testset_id).first()
    
    results = db.query(EvaluationResultModel).filter(
        EvaluationResultModel.evaluation_id == str(evaluation_id)
    ).all()
    
    individual_results = []
    for r in results:
        individual_results.append({
            "question_id": r.question_id,
            "question": r.question_text,
            "expected_answer": r.expected_answer,
            "generated_answer": r.generated_answer,
            "context": r.context,
            "metrics": r.metrics
        })
    
    evaluation_result = {
        "evaluation_id": evaluation.id,
        "testset_name": testset.name if testset else "未知测试集",
        "evaluation_method": evaluation.evaluation_method,
        "total_questions": evaluation.total_questions,
        "evaluated_questions": evaluation.evaluated_questions,
        "evaluation_time": evaluation.evaluation_time,
        "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
        "evaluation_metrics": evaluation.evaluation_metrics or [],
        "overall_metrics": evaluation.overall_metrics or {},
        "individual_results": individual_results
    }
    
    try:
        if format.lower() == "pdf":
            report_path = report_generator.generate_pdf_report(evaluation_result)
            media_type = "application/pdf"
        else:
            report_path = report_generator.generate_html_report(evaluation_result)
            media_type = "text/html"
        
        return FileResponse(
            path=report_path,
            media_type=media_type,
            filename=os.path.basename(report_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"报告下载失败: {str(e)}")


@router.get("/{evaluation_id}/metrics")
async def get_evaluation_metrics(
    evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取评估指标详情"""
    evaluation = db.query(EvaluationModel).filter(
        EvaluationModel.id == str(evaluation_id),
        EvaluationModel.user_id == current_user.id
    ).first()
    
    if not evaluation:
        raise HTTPException(status_code=404, detail="评估报告不存在")
    
    overall_metrics = evaluation.overall_metrics or {}
    
    quality_metrics = {}
    safety_metrics = {}
    
    for metric, data in overall_metrics.items():
        if metric == "overall_score":
            continue
        if isinstance(data, dict) and "mean" in data:
            if metric in ["hallucination", "toxicity", "bias"]:
                safety_metrics[metric] = data
            else:
                quality_metrics[metric] = data
    
    flat_metrics = {}
    for metric, data in overall_metrics.items():
        if metric == "overall_score":
            continue
        if isinstance(data, dict) and "mean" in data:
            flat_metrics[metric] = data.get("mean", 0)

    return {
        "evaluation_id": str(evaluation_id),
        "metrics": flat_metrics,
        "quality_metrics": quality_metrics,
        "safety_metrics": safety_metrics,
        "overall_score": overall_metrics.get("overall_score", {})
    }
