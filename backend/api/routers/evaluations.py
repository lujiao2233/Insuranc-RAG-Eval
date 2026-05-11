"""评估管理API路由
处理评估任务创建、查询、执行等操作
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json
import uuid
from pydantic import BaseModel

from api.dependencies import get_current_user, get_current_active_user
from config.database import get_db
from schemas import EvaluationCreate
from models.database import User, Evaluation as EvaluationModel, EvaluationResult as EvaluationResultModel
from models.database import (
    TestSet,
    Question,
    ConversationExecution,
    ConversationTestCase,
    ConversationTurn,
    ConversationTurnResult,
)
from config.settings import settings
from services.task_manager import task_manager, TaskCancelledError
from services.ragas_evaluator import evaluator
from services.config_service import ConfigService

router = APIRouter()
EXECUTION_EVAL_METHOD = "testset_execution"
CONVERSATION_EVAL_METHOD = "deepeval_conversation"


class ConversationEvaluationCreateRequest(BaseModel):
    testset_id: str
    evaluation_metrics: Optional[List[str]] = None


def _default_metrics_for_method(evaluation_method: Optional[str]) -> List[str]:
    method = (evaluation_method or "").strip().lower()
    if "deepeval" in method:
        return [
            "answer_relevance",
            "context_relevance",
            "context_precision",
            "faithfulness",
            "answer_correctness",
            "toxicity",
            "bias",
        ]
    return [
        "answer_relevance",
        "context_relevance",
        "context_precision",
        "faithfulness",
        "answer_correctness",
    ]


def _configured_metrics_for_method(config_service: ConfigService, user_id: str, evaluation_method: Optional[str]) -> List[str]:
    method = (evaluation_method or "").strip().lower()
    if "deepeval" in method:
        config_key = "evaluation.deepeval_metrics"
        supported_metrics = {
            "answer_relevance",
            "context_relevance",
            "context_precision",
            "faithfulness",
            "answer_correctness",
            "toxicity",
            "bias",
            "hallucination",
        }
    else:
        config_key = "evaluation.ragas_metrics"
        supported_metrics = {
            "answer_relevance",
            "context_relevance",
            "context_precision",
            "faithfulness",
            "answer_correctness",
            "answer_similarity",
        }

    configured = config_service.get_config_value(
        user_id,
        config_key,
        _default_metrics_for_method(evaluation_method)
    )
    if not isinstance(configured, list):
        configured = _default_metrics_for_method(evaluation_method)

    normalized: List[str] = []
    seen = set()
    for metric in configured:
        key = str(metric or "").strip()
        if not key or key not in supported_metrics or key in seen:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def _normalize_conversation_metrics(requested_metrics: Optional[List[str]]) -> List[str]:
    from services.ragas_evaluator import CONVERSATION_METRIC_ALIASES

    metrics = requested_metrics or []
    normalized: List[str] = []
    seen = set()
    for metric in metrics:
        raw = str(metric or "").strip()
        if not raw:
            continue
        matched = None
        for canonical_name, aliases in CONVERSATION_METRIC_ALIASES.items():
            if raw == canonical_name or raw in aliases:
                matched = canonical_name
                break
        if matched and matched not in seen:
            seen.add(matched)
            normalized.append(matched)
    return normalized


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


def _clone_conversation_to_report_testset(
    db: Session,
    source_testset: TestSet,
    user_id: str,
    source_execution_id: str,
) -> TestSet:
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
        "source_execution_id": str(source_execution_id),
        "report_created_at": datetime.now().isoformat(),
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
        conversation_mode="multi_turn",
        file_path=source_testset.file_path,
        testset_metadata=report_meta,
    )
    db.add(cloned)
    db.flush()

    source_cases = db.query(ConversationTestCase).filter(
        ConversationTestCase.testset_id == str(source_testset.id)
    ).all()
    for source_case in source_cases:
        case_meta = dict(source_case.case_metadata or {})
        case_meta["source_case_id"] = str(source_case.id)
        cloned_case = ConversationTestCase(
            id=str(uuid.uuid4()),
            testset_id=str(cloned.id),
            case_type=source_case.case_type,
            anchor_chunk_id=source_case.anchor_chunk_id,
            support_chunk_ids=list(source_case.support_chunk_ids or []),
            evaluation_criteria=source_case.evaluation_criteria,
            turn_count=source_case.turn_count,
            case_metadata=case_meta,
        )
        db.add(cloned_case)
        db.flush()

        source_turns = db.query(ConversationTurn).filter(
            ConversationTurn.case_id == str(source_case.id)
        ).order_by(ConversationTurn.turn_index.asc()).all()
        for source_turn in source_turns:
            turn_meta = dict(source_turn.turn_metadata or {})
            turn_meta["source_turn_id"] = str(source_turn.id)
            cloned_turn = ConversationTurn(
                id=str(uuid.uuid4()),
                case_id=str(cloned_case.id),
                turn_index=source_turn.turn_index,
                question=source_turn.question,
                expected_answer=source_turn.expected_answer,
                dependency_type=source_turn.dependency_type,
                context_hint=source_turn.context_hint,
                turn_metadata=turn_meta,
            )
            db.add(cloned_turn)

    return cloned


def _load_latest_conversation_execution(
    db: Session,
    testset_id: str,
    user_id: str,
) -> Optional[ConversationExecution]:
    return db.query(ConversationExecution).filter(
        ConversationExecution.testset_id == str(testset_id),
        ConversationExecution.user_id == str(user_id),
        ConversationExecution.status.in_(["completed", "partial_failed"]),
    ).order_by(ConversationExecution.finished_at.desc(), ConversationExecution.created_at.desc()).first()


def _build_conversation_cases_for_evaluation(
    db: Session,
    report_testset_id: str,
    source_execution_id: str,
) -> List[Dict[str, Any]]:
    cases = db.query(ConversationTestCase).filter(
        ConversationTestCase.testset_id == str(report_testset_id)
    ).all()
    turn_results = db.query(ConversationTurnResult).filter(
        ConversationTurnResult.execution_id == str(source_execution_id)
    ).all()
    source_turn_result_map = {
        str(item.turn_id): item
        for item in turn_results
        if item.turn_id
    }

    payloads: List[Dict[str, Any]] = []
    for case in cases:
        turns = db.query(ConversationTurn).filter(
            ConversationTurn.case_id == str(case.id)
        ).order_by(ConversationTurn.turn_index.asc()).all()
        turn_payloads: List[Dict[str, Any]] = []
        for turn in turns:
            turn_meta = turn.turn_metadata if isinstance(turn.turn_metadata, dict) else {}
            source_turn_id = str(turn_meta.get("source_turn_id") or turn.id or "")
            turn_result = source_turn_result_map.get(source_turn_id)
            turn_payloads.append(
                {
                    "turn_id": str(turn.id),
                    "turn_index": int(turn.turn_index or 0),
                    "question": turn.question or "",
                    "expected_answer": turn.expected_answer or "",
                    "generated_answer": (turn_result.generated_answer or "") if turn_result else "",
                    "dependency_type": turn.dependency_type or "",
                    "context_hint": turn.context_hint or "",
                    "refs": (turn_result.refs or "") if turn_result else "",
                    "session_id_before": (turn_result.session_id_before or "") if turn_result else "",
                    "session_id_after": (turn_result.session_id_after or "") if turn_result else "",
                }
            )
        payloads.append(
            {
                "case_id": str(case.id),
                "case_type": case.case_type or "",
                "evaluation_criteria": case.evaluation_criteria or "",
                "turns": turn_payloads,
            }
        )
    return payloads


def _parse_turn_context_payload(raw_context: Optional[str]) -> Dict[str, Any]:
    text = str(raw_context or "").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _serialize_evaluation_result_row(
    row: EvaluationResultModel,
    question: Optional[Question] = None,
) -> Dict[str, Any]:
    payload = {
        "id": row.id,
        "question_id": row.question_id,
        "case_id": row.case_id,
        "turn_id": row.turn_id,
        "question_text": row.question_text,
        "question_type": question.question_type if question else None,
        "category_major": question.category_major if question else None,
        "category_minor": question.category_minor if question else None,
        "expected_answer": row.expected_answer,
        "generated_answer": row.generated_answer,
        "context": row.context,
        "metrics": row.metrics,
        "reasons": row.reasons,
    }
    if row.turn_id:
        payload["context_payload"] = _parse_turn_context_payload(row.context)
    return payload


def _build_conversation_result_groups(
    rows: List[EvaluationResultModel],
) -> List[Dict[str, Any]]:
    case_row_map: Dict[str, EvaluationResultModel] = {}
    turn_rows_map: Dict[str, List[EvaluationResultModel]] = {}
    case_order: List[str] = []

    for row in rows:
        case_id = str(row.case_id or "")
        if not case_id:
            continue
        if case_id not in case_order:
            case_order.append(case_id)
        if row.turn_id:
            turn_rows_map.setdefault(case_id, []).append(row)
        else:
            case_row_map[case_id] = row

    groups: List[Dict[str, Any]] = []
    for case_id in case_order:
        case_row = case_row_map.get(case_id)
        turn_rows = sorted(
            turn_rows_map.get(case_id, []),
            key=lambda item: (
                int(_parse_turn_context_payload(item.context).get("turn_index") or 0),
                str(item.turn_id or ""),
            ),
        )
        turns: List[Dict[str, Any]] = []
        for row in turn_rows:
            context_payload = _parse_turn_context_payload(row.context)
            turns.append(
                {
                    "id": row.id,
                    "turn_id": row.turn_id,
                    "question_text": row.question_text,
                    "expected_answer": row.expected_answer,
                    "generated_answer": row.generated_answer,
                    "metrics": row.metrics or {},
                    "reasons": row.reasons or {},
                    "context_payload": context_payload,
                    "turn_index": int(context_payload.get("turn_index") or 0),
                    "dependency_type": context_payload.get("dependency_type"),
                    "context_hint": context_payload.get("context_hint"),
                    "session_id_before": context_payload.get("session_id_before"),
                    "session_id_after": context_payload.get("session_id_after"),
                }
            )

        groups.append(
            {
                "case_id": case_id,
                "case_result_id": case_row.id if case_row else None,
                "case_metrics": (case_row.metrics or {}) if case_row else {},
                "case_reasons": (case_row.reasons or {}) if case_row else {},
                "case_context": case_row.context if case_row else None,
                "case_title": case_row.question_text if case_row else "",
                "turns": turns,
                "turn_count": len(turns),
            }
        )
    return groups


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
        task_manager.ensure_not_cancelled(task_id)
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
            task_manager.ensure_not_cancelled(task_id)
            ratio = max(0.0, min(float(progress_ratio or 0.0), 1.0))
            estimated_done = min(
                len(questions),
                max(0, int(round(ratio * len(questions))))
            )
            task_manager.update_progress(
                task_id,
                ratio,
                message,
                current_step=estimated_done,
                total_steps=len(questions),
            )
            try:
                evaluation.evaluated_questions = estimated_done
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
            task_manager.ensure_not_cancelled(task_id)
            safe_total = max(1, int(total or 0))
            safe_done = max(0, min(int(done or 0), safe_total))
            progress_ratio = safe_done / safe_total

            task_manager.update_progress(
                task_id,
                progress_ratio,
                f"评估进度: {safe_done}/{safe_total}",
                current_step=safe_done,
                total_steps=safe_total,
            )
            try:
                evaluation.evaluated_questions = safe_done
                db.commit()
            except Exception:
                db.rollback()

        run_config = {
            "timeout": 600,
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
        task_manager.ensure_not_cancelled(task_id)
        
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
            message="评估完成",
            current_step=len(result.get("individual_results", [])),
            total_steps=len(questions),
        )
        task_manager.append_log(task_id, f"评估任务完成，耗时 {result.get('evaluation_time', 0):.2f} 秒")
        
    except TaskCancelledError:
        task_manager.append_log(task_id, "评估任务已取消")
        task_manager.mark_cancelled(task_id, "评估任务已取消")
        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == evaluation_id).first()
        if evaluation:
            evaluation.status = "failed"
            evaluation.error_message = "任务已取消"
            db.commit()
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


def run_conversation_evaluation_task(
    task_id: str,
    evaluation_id: str,
    testset_id: str,
    evaluation_metrics: List[str],
    db_url: str,
) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        task_manager.ensure_not_cancelled(task_id)
        task_manager.update_status(task_id, "running")
        task_manager.append_log(task_id, f"开始多轮评估任务: {evaluation_id}")

        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == str(evaluation_id)).first()
        if not evaluation:
            task_manager.fail_task(task_id, "评估记录不存在")
            return

        evaluation.status = "running"
        db.commit()

        testset = db.query(TestSet).filter(TestSet.id == str(testset_id)).first()
        if not testset:
            evaluation.status = "failed"
            evaluation.error_message = "测试集不存在"
            db.commit()
            task_manager.fail_task(task_id, "测试集不存在")
            return

        eval_config = evaluation.eval_config if isinstance(evaluation.eval_config, dict) else {}
        source_execution_id = str(eval_config.get("source_execution_id") or "").strip()
        if not source_execution_id:
            raise RuntimeError("多轮评估缺少 source_execution_id")

        cases_payload = _build_conversation_cases_for_evaluation(
            db,
            str(testset_id),
            source_execution_id,
        )
        if not cases_payload:
            raise RuntimeError("测试集中没有可评估的多轮 case")

        task_manager.append_log(task_id, f"加载了 {len(cases_payload)} 个多轮 case")

        def on_progress(done: int, total: int):
            task_manager.ensure_not_cancelled(task_id)
            safe_total = max(1, int(total or 0))
            safe_done = max(0, min(int(done or 0), safe_total))
            ratio = safe_done / safe_total
            task_manager.update_progress(
                task_id,
                ratio,
                f"多轮评估进度: {safe_done}/{safe_total}",
                current_step=safe_done,
                total_steps=safe_total,
            )
            try:
                evaluation.evaluated_questions = safe_done
                db.commit()
            except Exception:
                db.rollback()

        run_config = {
            "timeout": 600,
            "max_workers": 4,
            "user_id": str(evaluation.user_id) if getattr(evaluation, "user_id", None) else None,
            "db_session": db,
            "progress_callback": on_progress,
        }

        result = evaluator.evaluate_conversations(
            cases=cases_payload,
            evaluation_metrics=evaluation_metrics,
            run_config=run_config,
        )
        task_manager.ensure_not_cancelled(task_id)

        if result.get("error"):
            evaluation.status = "failed"
            evaluation.error_message = result["error"]
            db.commit()
            task_manager.fail_task(task_id, result["error"])
            return

        case_results = result.get("case_results") or []
        turn_results = result.get("turn_results") or []
        task_manager.append_log(
            task_id,
            f"多轮评估完成，准备保存 case 结果 {len(case_results)} 条，turn 结果 {len(turn_results)} 条",
        )

        rows_to_add: List[EvaluationResultModel] = []
        turn_case_map = {
            (str(turn.get("case_id") or ""), str(turn.get("turn_id") or "")): turn
            for turn in turn_results
        }
        for case_row in case_results:
            rows_to_add.append(
                EvaluationResultModel(
                    evaluation_id=str(evaluation_id),
                    case_id=str(case_row.get("case_id") or ""),
                    turn_id=None,
                    question_id=None,
                    question_text=f"Conversation Case: {case_row.get('case_type') or ''}",
                    expected_answer="",
                    generated_answer="",
                    context=case_row.get("evaluation_criteria", ""),
                    metrics=case_row.get("metrics", {}),
                    reasons=case_row.get("reasons", {}),
                )
            )

        for case_payload in cases_payload:
            for turn in case_payload.get("turns") or []:
                turn_row = turn_case_map.get(
                    (str(case_payload.get("case_id") or ""), str(turn.get("turn_id") or ""))
                )
                if not turn_row:
                    continue
                rows_to_add.append(
                    EvaluationResultModel(
                        evaluation_id=str(evaluation_id),
                        case_id=str(case_payload.get("case_id") or ""),
                        turn_id=str(turn.get("turn_id") or ""),
                        question_id=None,
                        question_text=str(turn.get("question") or ""),
                        expected_answer=str(turn.get("expected_answer") or ""),
                        generated_answer=str(turn.get("generated_answer") or ""),
                        context=json.dumps(
                            {
                                "turn_index": turn.get("turn_index", 0),
                                "dependency_type": turn.get("dependency_type", ""),
                                "context_hint": turn.get("context_hint", ""),
                                "session_id_before": turn.get("session_id_before", ""),
                                "session_id_after": turn.get("session_id_after", ""),
                            },
                            ensure_ascii=False,
                        ),
                        metrics=turn_row.get("metrics", {}),
                        reasons=turn_row.get("reasons", {}),
                    )
                )

        if rows_to_add:
            db.add_all(rows_to_add)

        evaluation.status = "completed"
        evaluation.evaluation_mode = CONVERSATION_EVAL_METHOD
        evaluation.total_questions = len(case_results)
        evaluation.evaluated_questions = len(case_results)
        evaluation.overall_metrics = result.get("overall_metrics", {})
        evaluation.evaluation_time = int(result.get("evaluation_time", 0))
        evaluation.evaluation_metrics = evaluation_metrics
        db.commit()

        task_manager.finish_task(
            task_id,
            result={
                "evaluation_id": evaluation_id,
                "overall_metrics": result.get("overall_metrics", {}),
                "case_result_count": len(case_results),
                "turn_result_count": len(turn_results),
            },
            message="多轮评估完成",
            current_step=len(case_results),
            total_steps=len(case_results),
        )
        task_manager.append_log(task_id, f"多轮评估任务完成，耗时 {result.get('evaluation_time', 0):.2f} 秒")

    except TaskCancelledError:
        task_manager.append_log(task_id, "多轮评估任务已取消")
        task_manager.mark_cancelled(task_id, "多轮评估任务已取消")
        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == str(evaluation_id)).first()
        if evaluation:
            evaluation.status = "failed"
            evaluation.error_message = "任务已取消"
            db.commit()
    except Exception as exc:
        task_manager.append_log(task_id, f"多轮评估失败: {str(exc)}")
        task_manager.fail_task(task_id, str(exc))
        evaluation = db.query(EvaluationModel).filter(EvaluationModel.id == str(evaluation_id)).first()
        if evaluation:
            evaluation.status = "failed"
            evaluation.error_message = str(exc)
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
                "evaluation_mode": e.evaluation_mode,
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
        "evaluation_mode": evaluation.evaluation_mode,
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
    config_service = ConfigService(db)
    allowed_metrics = _configured_metrics_for_method(
        config_service,
        str(current_user.id),
        evaluation_data.evaluation_method
    )
    if not allowed_metrics:
        raise HTTPException(status_code=400, detail="当前评估方法未配置可用指标，请先在系统配置中勾选并保存")

    requested_metrics = evaluation_data.evaluation_metrics or allowed_metrics
    selected_metrics: List[str] = []
    invalid_metrics: List[str] = []
    seen = set()
    for metric in requested_metrics:
        key = str(metric or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        if key in allowed_metrics:
            selected_metrics.append(key)
        else:
            invalid_metrics.append(key)
    if invalid_metrics:
        raise HTTPException(
            status_code=400,
            detail=f"以下评估指标未在系统配置中启用: {', '.join(invalid_metrics)}"
        )
    if not selected_metrics:
        raise HTTPException(status_code=400, detail="请至少选择一个已启用的评估指标")

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
        if testset.generation_method == "csv_import":
            raise HTTPException(
                status_code=400,
                detail=f"测试集中有 {unanswered_questions} 个问题缺少模型答案，无法评估。如果是CSV导入的测试集，请确保所有问题的'模型答案'列都有内容。"
            )
        else:
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
        evaluation_metrics=selected_metrics,
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
    
    task_id = task_manager.submit_task(
        task_type="evaluation",
        params={
            "evaluation_id": evaluation.id,
            "testset_id": str(report_testset.id),
            "evaluation_method": evaluation.evaluation_method,
            "evaluation_metrics": evaluation.evaluation_metrics or _default_metrics_for_method(evaluation.evaluation_method),
            "db_url": settings.DATABASE_URL,
        }
    )
    
    return {
        "id": evaluation.id,
        "task_id": task_id,
        "status": "pending",
        "message": "评估任务已创建并开始执行"
    }


@router.post("/conversation")
async def create_conversation_evaluation(
    evaluation_data: ConversationEvaluationCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    testset = db.query(TestSet).filter(
        TestSet.id == str(evaluation_data.testset_id),
        TestSet.user_id == current_user.id
    ).first()
    if not testset:
        raise HTTPException(status_code=404, detail="测试集不存在")
    if str(testset.conversation_mode or "single_turn").strip() != "multi_turn":
        raise HTTPException(status_code=400, detail="当前测试集不是多轮模式")

    latest_execution = _load_latest_conversation_execution(
        db,
        str(testset.id),
        str(current_user.id),
    )
    if not latest_execution:
        raise HTTPException(status_code=400, detail="当前多轮测试集没有可用执行结果，无法评估")

    case_count = db.query(ConversationTestCase).filter(
        ConversationTestCase.testset_id == str(testset.id)
    ).count()
    if case_count <= 0:
        raise HTTPException(status_code=400, detail="当前测试集没有多轮 case，无法评估")

    source_results = db.query(ConversationTurnResult).filter(
        ConversationTurnResult.execution_id == str(latest_execution.id)
    ).all()
    if not source_results:
        raise HTTPException(status_code=400, detail="当前多轮测试集没有执行轮次结果，无法评估")
    missing_answers = sum(1 for item in source_results if not (item.generated_answer or "").strip())
    if missing_answers > 0:
        raise HTTPException(status_code=400, detail=f"执行结果中仍有 {missing_answers} 个 turn 缺少模型回答，无法评估")

    selected_metrics = _normalize_conversation_metrics(evaluation_data.evaluation_metrics)
    if not selected_metrics:
        selected_metrics = [
            "knowledge_retention",
            "conversation_relevancy",
            "conversation_completeness",
            "role_adherence",
        ]

    report_testset = _clone_conversation_to_report_testset(
        db,
        testset,
        str(current_user.id),
        str(latest_execution.id),
    )
    db.commit()
    db.refresh(report_testset)

    evaluation = EvaluationModel(
        user_id=current_user.id,
        testset_id=str(report_testset.id),
        evaluation_method=CONVERSATION_EVAL_METHOD,
        evaluation_mode=CONVERSATION_EVAL_METHOD,
        total_questions=case_count,
        evaluated_questions=0,
        evaluation_metrics=selected_metrics,
        eval_config={
            "source_execution_id": str(latest_execution.id),
            "source_testset_id": str(testset.id),
            "report_testset_id": str(report_testset.id),
            "conversation_evaluation": True,
        },
        status="pending",
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    task_id = task_manager.submit_task(
        task_type="evaluate_conversation",
        params={
            "evaluation_id": str(evaluation.id),
            "testset_id": str(report_testset.id),
            "evaluation_metrics": selected_metrics,
            "db_url": settings.DATABASE_URL,
        }
    )

    return {
        "id": evaluation.id,
        "task_id": task_id,
        "status": "pending",
        "message": "多轮评估任务已创建并开始执行"
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
    questions_map: Dict[str, Question] = {}
    if question_ids:
        questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_map = {q.id: q for q in questions}

    items = [
        _serialize_evaluation_result_row(
            r,
            questions_map.get(r.question_id) if r.question_id else None,
        )
        for r in results
    ]
    response: Dict[str, Any] = {
        "evaluation_id": str(evaluation_id),
        "total": total,
        "items": items,
    }

    if str(evaluation.evaluation_mode or "").strip() == CONVERSATION_EVAL_METHOD:
        response["conversation_results"] = _build_conversation_result_groups(results)
    
    return response


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
