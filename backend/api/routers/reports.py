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
            "total_questions": e.total_questions,
            "evaluated_questions": e.evaluated_questions,
            "evaluation_time": e.evaluation_time,
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
    
    return {
        "evaluation_id": str(evaluation_id),
        "quality_metrics": quality_metrics,
        "safety_metrics": safety_metrics,
        "overall_score": overall_metrics.get("overall_score", {})
    }


@router.get("/{evaluation_id}/compare/{other_evaluation_id}")
async def compare_reports(
    evaluation_id: UUID,
    other_evaluation_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """比较两个评估报告"""
    evaluations = []
    
    for eval_id in [evaluation_id, other_evaluation_id]:
        evaluation = db.query(EvaluationModel).filter(
            EvaluationModel.id == str(eval_id),
            EvaluationModel.user_id == current_user.id
        ).first()
        
        if not evaluation:
            raise HTTPException(status_code=404, detail=f"评估报告 {eval_id} 不存在")
        
        testset = db.query(TestSet).filter(TestSet.id == evaluation.testset_id).first()
        
        evaluations.append({
            "evaluation_id": evaluation.id,
            "testset_name": testset.name if testset else "未知测试集",
            "evaluation_method": evaluation.evaluation_method,
            "total_questions": evaluation.total_questions,
            "evaluated_questions": evaluation.evaluated_questions,
            "evaluation_time": evaluation.evaluation_time,
            "timestamp": evaluation.timestamp.isoformat() if evaluation.timestamp else None,
            "overall_metrics": evaluation.overall_metrics or {}
        })
    
    comparison = {
        "evaluations": evaluations,
        "metrics_comparison": {},
        "improvement": {}
    }
    
    metrics_1 = evaluations[0].get("overall_metrics", {})
    metrics_2 = evaluations[1].get("overall_metrics", {})
    
    all_metrics = set(metrics_1.keys()) | set(metrics_2.keys())
    
    for metric in all_metrics:
        if metric == "overall_score":
            continue
        
        data_1 = metrics_1.get(metric, {})
        data_2 = metrics_2.get(metric, {})
        
        if isinstance(data_1, dict) and "mean" in data_1 and isinstance(data_2, dict) and "mean" in data_2:
            mean_1 = data_1.get("mean", 0)
            mean_2 = data_2.get("mean", 0)
            
            comparison["metrics_comparison"][metric] = {
                "evaluation_1": mean_1,
                "evaluation_2": mean_2,
                "difference": mean_2 - mean_1,
                "improved": mean_2 > mean_1
            }
    
    if "overall_score" in metrics_1 and "overall_score" in metrics_2:
        score_1 = metrics_1["overall_score"].get("mean", 0)
        score_2 = metrics_2["overall_score"].get("mean", 0)
        
        comparison["improvement"] = {
            "overall_score_difference": score_2 - score_1,
            "improved": score_2 > score_1,
            "improvement_percentage": ((score_2 - score_1) / score_1 * 100) if score_1 > 0 else 0
        }
    
    return comparison
