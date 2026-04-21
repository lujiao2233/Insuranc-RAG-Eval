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


def _run_testset_generation(params: Dict[str, Any], task_id: str) -> None:
    from services.advanced_testset_generator import advanced_testset_generator

    advanced_testset_generator.generate_testset_async(
        params.get("content") or [],
        params.get("params") or {},
        task_id,
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


TASK_HANDLER_MAP = {
    "document_analysis": _run_document_analysis,
    "generate_questions": _run_generate_questions,
    "execute_testset": _run_execute_testset,
    "evaluation": _run_evaluation,
    "testset_generation": _run_testset_generation,
}

TASK_RETRY_PREPARE_MAP = {
    "generate_questions": _prepare_generate_questions_retry,
    "evaluation": _prepare_evaluation_retry,
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
