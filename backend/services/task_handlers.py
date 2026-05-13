"""持久化任务处理器注册表。"""
import asyncio
from typing import Any, Dict

from config.settings import settings


def _run_document_analysis(params: Dict[str, Any], task_id: str) -> None:
    from services.document_service import DocumentService

    document_id = str(params["document_id"])
    user_id = str(params["user_id"])
    asyncio.run(DocumentService().analyze_document_task(document_id, user_id, task_id))


def _run_generate_questions(params: Dict[str, Any], task_id: str) -> None:
    from api.routers.testsets import _run_generation_task

    _run_generation_task(
        task_id,
        str(params["testset_id"]),
        str(params["user_id"]),
        int(params["num_questions"]),
        params.get("question_types"),
        str(params.get("generation_mode") or "advanced"),
        bool(params.get("enable_safety_robustness", True)),
        float(params.get("multi_doc_ratio", 0.1)),
        params.get("document_ids"),
        params.get("persona_list"),
        distribution_mode=str(params.get("distribution_mode") or "total"),
        questions_per_doc=params.get("questions_per_doc"),
    )


def _run_execute_testset(params: Dict[str, Any], task_id: str) -> None:
    from api.routers.testsets import _run_execution_task

    _run_execution_task(
        task_id,
        str(params["execution_evaluation_id"]),
        str(params["testset_id"]),
        str(params["user_id"]),
        str(params["mobile"]),
        str(params["verify_code"]),
        str(params["bot_id"]),
        api_type=params.get("api_type"),
    )


def _run_evaluation(params: Dict[str, Any], task_id: str) -> None:
    from api.routers.evaluations import run_evaluation_task

    run_evaluation_task(
        task_id,
        str(params["evaluation_id"]),
        str(params["testset_id"]),
        str(params["evaluation_method"]),
        list(params.get("evaluation_metrics") or []),
        str(params.get("db_url") or settings.DATABASE_URL),
    )


def _run_evaluate_conversation(params: Dict[str, Any], task_id: str) -> None:
    from api.routers.evaluations import run_conversation_evaluation_task

    run_conversation_evaluation_task(
        task_id,
        str(params["evaluation_id"]),
        str(params["testset_id"]),
        list(params.get("evaluation_metrics") or []),
        str(params.get("db_url") or settings.DATABASE_URL),
    )


def _run_testset_generation(params: Dict[str, Any], task_id: str) -> None:
    from services.advanced_testset_generator import advanced_testset_generator

    advanced_testset_generator.generate_testset_async(
        params.get("content") or [],
        params.get("params") or {},
        task_id,
    )


def _run_generate_conversation_cases(params: Dict[str, Any], task_id: str) -> None:
    from services.conversation_case_generator import conversation_case_generator
    from services.task_manager import task_manager

    case_ids = conversation_case_generator.generate_cases(
        str(params["testset_id"]),
        int(params.get("num_cases") or 0),
        params.get("turn_range"),
        params.get("case_type_ratio"),
        str(params["user_id"]),
        task_id=task_id,
        document_ids=params.get("document_ids"),
    )
    task_manager.finish_task(
        task_id,
        result={
            "testset_id": str(params["testset_id"]),
            "generated_case_ids": case_ids,
            "generated_case_count": len(case_ids),
        },
        message=f"多轮 case 生成完成，共 {len(case_ids)} 个",
        current_step=len(case_ids),
        total_steps=len(case_ids),
    )


def _run_execute_conversation_testset(params: Dict[str, Any], task_id: str) -> None:
    from services.conversation_executor import conversation_executor

    conversation_executor.execute_testset(
        str(params["testset_id"]),
        str(params["execution_id"]),
        str(params["user_id"]),
        str(params["mobile"]),
        str(params["verify_code"]),
        str(params["bot_id"]),
        task_id=task_id,
        api_type=params.get("api_type"),
    )


def _prepare_generate_questions_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import Question, TestSet

    db = SessionLocal()
    try:
        testset_id = str(params["testset_id"])
        db.query(Question).filter(Question.testset_id == testset_id).delete(synchronize_session=False)
        testset = db.query(TestSet).filter(TestSet.id == testset_id).first()
        if testset:
            testset.question_count = 0
        db.commit()
    finally:
        db.close()


def _prepare_generate_conversation_cases_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import (
        ConversationTestCase,
        ConversationTurn,
        ConversationTurnResult,
        TestSet,
    )

    db = SessionLocal()
    try:
        testset_id = str(params["testset_id"])
        case_ids = [
            item[0]
            for item in db.query(ConversationTestCase.id).filter(
                ConversationTestCase.testset_id == testset_id
            ).all()
        ]
        if case_ids:
            db.query(ConversationTurnResult).filter(
                ConversationTurnResult.case_id.in_(case_ids)
            ).delete(synchronize_session=False)
            db.query(ConversationTurn).filter(
                ConversationTurn.case_id.in_(case_ids)
            ).delete(synchronize_session=False)
            db.query(ConversationTestCase).filter(
                ConversationTestCase.testset_id == testset_id
            ).delete(synchronize_session=False)

        testset = db.query(TestSet).filter(TestSet.id == testset_id).first()
        if testset:
            testset.question_count = 0
            metadata = dict(testset.testset_metadata or {})
            metadata.pop("conversation_quality_report", None)
            testset.testset_metadata = metadata or None
        db.commit()
    finally:
        db.close()


def _prepare_evaluation_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import Evaluation, EvaluationResult

    db = SessionLocal()
    try:
        evaluation_id = str(params["evaluation_id"])
        db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_id == evaluation_id
        ).delete(synchronize_session=False)
        evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if evaluation:
            evaluation.status = "pending"
            evaluation.error_message = None
            evaluation.evaluated_questions = 0
            evaluation.overall_metrics = None
            evaluation.evaluation_time = None
        db.commit()
    finally:
        db.close()


def _prepare_evaluate_conversation_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import Evaluation, EvaluationResult

    db = SessionLocal()
    try:
        evaluation_id = str(params["evaluation_id"])
        db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_id == evaluation_id
        ).delete(synchronize_session=False)
        evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if evaluation:
            evaluation.status = "pending"
            evaluation.error_message = None
            evaluation.evaluated_questions = 0
            evaluation.overall_metrics = None
            evaluation.evaluation_time = None
        db.commit()
    finally:
        db.close()


def _prepare_execute_testset_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import Evaluation, EvaluationResult

    db = SessionLocal()
    try:
        evaluation_id = str(params["execution_evaluation_id"])
        db.query(EvaluationResult).filter(
            EvaluationResult.evaluation_id == evaluation_id
        ).delete(synchronize_session=False)
        evaluation = db.query(Evaluation).filter(Evaluation.id == evaluation_id).first()
        if evaluation:
            evaluation.status = "pending"
            evaluation.error_message = None
            evaluation.evaluated_questions = 0
            evaluation.evaluation_time = None
        db.commit()
    finally:
        db.close()


def _prepare_execute_conversation_retry(params: Dict[str, Any]) -> None:
    from config.database import SessionLocal
    from models.database import ConversationExecution, ConversationTurnResult, Evaluation

    db = SessionLocal()
    try:
        execution_id = str(params["execution_id"])
        db.query(ConversationTurnResult).filter(
            ConversationTurnResult.execution_id == execution_id
        ).delete(synchronize_session=False)
        execution = db.query(ConversationExecution).filter(
            ConversationExecution.id == execution_id
        ).first()
        if execution:
            execution.status = "pending"
            execution.started_at = None
            execution.finished_at = None
            execution.execution_metadata = {
                **(execution.execution_metadata or {}),
                "retry_prepared_at": None,
            }
            if execution.evaluation_id:
                evaluation = db.query(Evaluation).filter(
                    Evaluation.id == str(execution.evaluation_id)
                ).first()
                if evaluation:
                    evaluation.status = "pending"
                    evaluation.error_message = None
                    evaluation.evaluated_questions = 0
                    evaluation.evaluation_time = None
        db.commit()
    finally:
        db.close()


TASK_HANDLER_MAP = {
    "document_analysis": _run_document_analysis,
    "generate_questions": _run_generate_questions,
    "generate_conversation_cases": _run_generate_conversation_cases,
    "execute_conversation_testset": _run_execute_conversation_testset,
    "execute_testset": _run_execute_testset,
    "evaluation": _run_evaluation,
    "evaluate_conversation": _run_evaluate_conversation,
    "testset_generation": _run_testset_generation,
}

TASK_RETRY_PREPARE_MAP = {
    "generate_questions": _prepare_generate_questions_retry,
    "generate_conversation_cases": _prepare_generate_conversation_cases_retry,
    "execute_conversation_testset": _prepare_execute_conversation_retry,
    "evaluation": _prepare_evaluation_retry,
    "evaluate_conversation": _prepare_evaluate_conversation_retry,
    "execute_testset": _prepare_execute_testset_retry,
}


def run_task_handler(task_type: str, params: Dict[str, Any], task_id: str) -> None:
    handler = TASK_HANDLER_MAP.get(str(task_type or "").strip())
    if handler is None:
        raise RuntimeError(f"未注册的任务类型: {task_type}")
    handler(params, task_id)


def prepare_task_for_retry(task_type: str, params: Dict[str, Any]) -> None:
    handler = TASK_RETRY_PREPARE_MAP.get(str(task_type or "").strip())
    if handler is None:
        return
    handler(params)
