"""多轮会话执行引擎。"""
from __future__ import annotations

import time
from datetime import datetime
from typing import Any, Dict, List

from config.database import SessionLocal
from models.database import (
    ConversationExecution,
    ConversationTestCase,
    ConversationTurn,
    ConversationTurnResult,
    Evaluation,
    TestSet,
)
from services.api_client import TalkApiClient
from services.task_manager import TaskCancelledError, task_manager
from utils.logger import get_logger

logger = get_logger("conversation_executor")


class MultiTurnConversationExecutor:
    """执行多轮测试集并记录每轮对话结果。"""

    def execute_testset(
        self,
        testset_id: str,
        execution_id: str,
        user_id: str,
        mobile: str,
        verify_code: str,
        bot_id: str,
        task_id: str | None = None,
        api_type: str | None = None,
        skip_answered: bool = False,
    ) -> None:
        db = SessionLocal()
        try:
            task_manager.ensure_not_cancelled(task_id)
            if task_id:
                task_manager.update_status(task_id, "running")

            execution = db.query(ConversationExecution).filter(
                ConversationExecution.id == str(execution_id),
                ConversationExecution.user_id == str(user_id),
            ).first()
            testset = db.query(TestSet).filter(
                TestSet.id == str(testset_id),
                TestSet.user_id == str(user_id),
            ).first()
            if not execution or not testset:
                raise RuntimeError("多轮执行记录或测试集不存在")

            evaluation = None
            if execution.evaluation_id:
                evaluation = db.query(Evaluation).filter(
                    Evaluation.id == str(execution.evaluation_id)
                ).first()

            cases = self._load_cases(db, str(testset_id))
            if not cases:
                raise RuntimeError("该多轮测试集没有 conversation cases，无法执行")

            source_results_for_copy: Dict[str, ConversationTurnResult] = {}
            answered_questions: set[str] | None = None
            if skip_answered:
                source_testset_id = str(
                    (execution.execution_metadata or {}).get("source_testset_id", "")
                )
                if source_testset_id:
                    source_execution = (
                        db.query(ConversationExecution)
                        .filter(
                            ConversationExecution.testset_id == source_testset_id,
                            ConversationExecution.user_id == str(user_id),
                            ConversationExecution.status.in_(["completed", "partial_failed"]),
                        )
                        .order_by(ConversationExecution.finished_at.desc())
                        .first()
                    )
                    if source_execution:
                        source_results = (
                            db.query(ConversationTurnResult)
                            .filter(
                                ConversationTurnResult.execution_id == str(source_execution.id),
                                ConversationTurnResult.generated_answer.isnot(None),
                                ConversationTurnResult.generated_answer != "",
                            )
                            .all()
                        )
                        answered_questions = {
                            str(
                                (r.request_payload or {}).get("msg", "")
                            ).strip()
                            for r in source_results
                        }
                        answered_questions.discard("")
                        for r in source_results:
                            source_results_for_copy[str(r.turn_id)] = r

            cases_to_skip: set[str] = set()
            if skip_answered and answered_questions:
                for case in cases:
                    turns = case.turns or []
                    if turns and all(
                        (t.question or "").strip() in answered_questions for t in turns
                    ):
                        cases_to_skip.add(str(case.id))
                skipped_count = len(cases_to_skip)
                if skipped_count > 0 and task_id:
                    task_manager.append_log(
                        task_id,
                        f"补执行模式：跳过 {skipped_count} 个全部轮次已有答案的 case",
                    )
                elif skip_answered and task_id:
                    task_manager.append_log(
                        task_id,
                        "补执行模式：未找到可完整跳过的 case，将执行全部 case",
                    )

            total_steps = sum(len(case.turns or []) for case in cases)
            started_at = datetime.now()
            execution.status = "running"
            execution.started_at = started_at
            execution.execution_metadata = {
                **(execution.execution_metadata or {}),
                "source": "talk_api",
                "bot_id": bot_id,
                "case_count": len(cases),
                "total_steps": total_steps,
                "started_at": started_at.isoformat(),
            }
            if evaluation:
                evaluation.status = "running"
                evaluation.evaluated_questions = 0
                evaluation.total_questions = total_steps
                evaluation.timestamp = started_at
            db.commit()

            if task_id:
                task_manager.append_log(task_id, f"正在初始化多轮执行客户端 (手机号: {mobile}, BOT_ID: {bot_id}, API路径: {api_type or 'default'})...")

            client = TalkApiClient(mobile=mobile, bot_id=bot_id, api_type=api_type)
            login_resp = client.phone_login(verify_code)
            if not login_resp.get("success"):
                raise RuntimeError(f"登录失败: {login_resp}")
            if task_id:
                task_manager.append_log(task_id, "多轮执行客户端登录成功")

            processed_turns = 0
            completed_cases = 0
            partial_failed_cases = 0
            failed_cases = 0

            for case_index, case in enumerate(cases, start=1):
                task_manager.ensure_not_cancelled(task_id)

                if skip_answered and str(case.id) in cases_to_skip:
                    case_turns = sorted(case.turns or [], key=lambda t: t.turn_index or 0)
                    for src_turn in case_turns:
                        turn_meta = src_turn.turn_metadata if isinstance(src_turn.turn_metadata, dict) else {}
                        source_turn_id = str(turn_meta.get("source_turn_id", ""))
                        src_result = source_results_for_copy.get(source_turn_id) if source_turn_id else None
                        if src_result:
                            copied = ConversationTurnResult(
                                execution_id=str(execution.id),
                                case_id=str(case.id),
                                turn_id=str(src_turn.id),
                                session_id_before=src_result.session_id_before,
                                session_id_after=src_result.session_id_after,
                                request_payload=src_result.request_payload,
                                response_payload=src_result.response_payload,
                                generated_answer=src_result.generated_answer or "",
                                refs=src_result.refs or "",
                                turn_status=src_result.turn_status or "ok",
                                execution_time_ms=src_result.execution_time_ms or 0,
                            )
                            db.add(copied)
                        else:
                            copied = ConversationTurnResult(
                                execution_id=str(execution.id),
                                case_id=str(case.id),
                                turn_id=str(src_turn.id),
                                generated_answer="",
                                refs="",
                                turn_status="skipped",
                                execution_time_ms=0,
                            )
                            db.add(copied)
                    db.commit()
                    processed_turns += len(case_turns)
                    completed_cases += 1
                    if evaluation:
                        evaluation.evaluated_questions = processed_turns
                        db.commit()
                    self._update_case_execution_metadata(
                        db,
                        case,
                        execution_id=str(execution.id),
                        case_status="ok",
                        executed_turns=len(case_turns),
                        last_session_id="",
                    )
                    if task_id:
                        task_manager.append_log(
                            task_id,
                            f"跳过 Case {case_index}/{len(cases)} (全部轮次已有答案，已复制 {len(case_turns)} 个结果)",
                        )
                    continue

                case_status = "ok"
                current_session_id = ""
                executed_turns = 0
                ordered_turns = sorted(case.turns or [], key=lambda item: item.turn_index or 0)
                if task_id:
                    task_manager.append_log(
                        task_id,
                        f"开始执行 Case {case_index}/{len(cases)}: {case.id} ({case.case_type})",
                    )

                for turn_index, turn in enumerate(ordered_turns, start=1):
                    task_manager.ensure_not_cancelled(task_id)

                    if task_id:
                        task_manager.update_progress(
                            task_id,
                            processed_turns / max(total_steps, 1),
                            f"正在执行 Case {case_index}/{len(cases)} Turn {turn_index}/{len(ordered_turns)}",
                            current_step=processed_turns,
                            total_steps=total_steps,
                            context_info={
                                "current_case": case_index,
                                "current_turn": turn_index,
                                "total_cases": len(cases),
                                "session_id": current_session_id,
                            },
                        )
                        task_manager.append_log(
                            task_id,
                            f"提问 Case {case_index}/{len(cases)} Turn {turn_index}/{len(ordered_turns)}: {turn.question}",
                        )

                    session_id_before = current_session_id
                    is_new_dialog = turn_index == 1 or not current_session_id
                    started_turn_at = time.perf_counter()
                    try:
                        detail = client.chat_with_session_details(
                            turn.question or "",
                            session_id=current_session_id,
                            new_dialog=is_new_dialog,
                            listen_seconds=120.0,
                            max_retries=1,
                        )
                        session_id_after = str(detail.get("session_id") or current_session_id or "").strip()
                        if turn_index == 1 and not session_id_after:
                            raise RuntimeError("首轮响应未返回 sessionId")

                        turn_status = str(detail.get("status") or "failed").strip() or "failed"
                        current_session_id = session_id_after or current_session_id
                        executed_turns += 1
                        processed_turns += 1

                        result_row = ConversationTurnResult(
                            execution_id=str(execution.id),
                            case_id=str(case.id),
                            turn_id=str(turn.id),
                            session_id_before=session_id_before or None,
                            session_id_after=session_id_after or None,
                            request_payload=detail.get("request_payload"),
                            response_payload=detail.get("response_payload"),
                            generated_answer=str(detail.get("answer") or ""),
                            refs=str(detail.get("refs") or ""),
                            turn_status=turn_status,
                            execution_time_ms=int((time.perf_counter() - started_turn_at) * 1000),
                        )
                        db.add(result_row)
                        if evaluation:
                            evaluation.evaluated_questions = processed_turns
                        db.commit()

                        if turn_status != "ok":
                            case_status = "partial_failed"
                        if task_id:
                            task_manager.append_log(
                                task_id,
                                f"收到回答 Case {case_index}/{len(cases)} Turn {turn_index}/{len(ordered_turns)} (状态: {turn_status}, session: {session_id_after or 'missing'})",
                            )
                    except Exception as exc:
                        processed_turns += 1
                        case_status = "failed"
                        db.rollback()
                        failure_row = ConversationTurnResult(
                            execution_id=str(execution.id),
                            case_id=str(case.id),
                            turn_id=str(turn.id),
                            session_id_before=session_id_before or None,
                            session_id_after=None,
                            request_payload={
                                "botId": bot_id,
                                "visitorBizId": mobile,
                                "userType": client.user_type,
                                "sessionId": session_id_before or "",
                                "newDialog": is_new_dialog,
                                "msg": turn.question or "",
                            },
                            response_payload={"error": str(exc)},
                            generated_answer="",
                            refs="",
                            turn_status="failed",
                            execution_time_ms=int((time.perf_counter() - started_turn_at) * 1000),
                        )
                        db.add(failure_row)
                        if evaluation:
                            evaluation.evaluated_questions = processed_turns
                        db.commit()
                        logger.warning(
                            "多轮执行失败: execution=%s case=%s turn=%s error=%s",
                            execution.id,
                            case.id,
                            turn.id,
                            exc,
                        )
                        if task_id:
                            task_manager.append_log(
                                task_id,
                                f"Case {case_index}/{len(cases)} Turn {turn_index}/{len(ordered_turns)} 执行失败: {exc}",
                            )
                        break

                self._update_case_execution_metadata(
                    db,
                    case,
                    execution_id=str(execution.id),
                    case_status=case_status,
                    executed_turns=executed_turns,
                    last_session_id=current_session_id,
                )
                if case_status == "ok":
                    completed_cases += 1
                elif case_status == "partial_failed":
                    partial_failed_cases += 1
                else:
                    failed_cases += 1

            finished_at = datetime.now()
            if completed_cases == 0 and partial_failed_cases == 0:
                execution.status = "failed"
                final_message = f"多轮执行失败，{failed_cases} 个 case 全部失败"
            elif failed_cases > 0 or partial_failed_cases > 0:
                execution.status = "partial_failed"
                final_message = (
                    f"多轮执行完成，但存在部分失败：成功 {completed_cases}，"
                    f"部分失败 {partial_failed_cases}，失败 {failed_cases}"
                )
            else:
                execution.status = "completed"
                final_message = f"多轮执行完成，共成功执行 {completed_cases} 个 case"

            execution.finished_at = finished_at
            execution.execution_metadata = {
                **(execution.execution_metadata or {}),
                "completed_cases": completed_cases,
                "partial_failed_cases": partial_failed_cases,
                "failed_cases": failed_cases,
                "processed_turns": processed_turns,
                "finished_at": finished_at.isoformat(),
            }
            if evaluation:
                evaluation.total_questions = total_steps
                evaluation.evaluated_questions = processed_turns
                evaluation.evaluation_time = int((finished_at - started_at).total_seconds())
                evaluation.timestamp = finished_at
                if execution.status == "failed":
                    evaluation.status = "failed"
                    evaluation.error_message = final_message
                else:
                    evaluation.status = "completed"
                    evaluation.error_message = None if execution.status == "completed" else final_message
            db.commit()

            if execution.status == "failed":
                if task_id:
                    task_manager.fail_task(task_id, final_message)
                    task_manager.append_log(task_id, final_message)
            else:
                if task_id:
                    task_manager.update_progress(
                        task_id,
                        1.0,
                        final_message,
                        current_step=processed_turns,
                        total_steps=total_steps,
                        context_info={
                            "current_case": len(cases),
                            "current_turn": 0,
                            "total_cases": len(cases),
                            "session_id": "",
                        },
                    )
                    task_manager.finish_task(
                        task_id,
                        result={
                            "execution_id": str(execution.id),
                            "evaluation_id": str(execution.evaluation_id or ""),
                            "processed_turns": processed_turns,
                            "completed_cases": completed_cases,
                            "partial_failed_cases": partial_failed_cases,
                            "failed_cases": failed_cases,
                            "status": execution.status,
                        },
                        message=final_message,
                        current_step=processed_turns,
                        total_steps=total_steps,
                        context_info={
                            "current_case": len(cases),
                            "current_turn": 0,
                            "total_cases": len(cases),
                            "session_id": "",
                        },
                    )
                    task_manager.append_log(task_id, "多轮执行任务结束")
        except TaskCancelledError:
            db.rollback()
            self._mark_execution_cancelled(db, execution_id)
            if task_id:
                task_manager.mark_cancelled(task_id, "多轮执行已取消")
                task_manager.append_log(task_id, "任务已取消，停止多轮执行")
        except Exception as exc:
            db.rollback()
            self._mark_execution_failed(db, execution_id, str(exc))
            if task_id:
                task_manager.fail_task(task_id, str(exc))
                task_manager.append_log(task_id, f"多轮执行任务失败: {exc}")
            raise
        finally:
            db.close()

    def _load_cases(self, db, testset_id: str) -> List[ConversationTestCase]:
        cases = db.query(ConversationTestCase).filter(
            ConversationTestCase.testset_id == str(testset_id)
        ).all()
        return sorted(
            cases,
            key=lambda item: (
                item.created_at or datetime.min,
                str(item.id or ""),
            ),
        )

    def _update_case_execution_metadata(
        self,
        db,
        case: ConversationTestCase,
        *,
        execution_id: str,
        case_status: str,
        executed_turns: int,
        last_session_id: str,
    ) -> None:
        metadata = dict(case.case_metadata or {})
        metadata["last_execution"] = {
            "execution_id": execution_id,
            "status": case_status,
            "executed_turns": executed_turns,
            "last_session_id": last_session_id or "",
            "updated_at": datetime.now().isoformat(),
        }
        case.case_metadata = metadata
        case.turn_count = max(int(case.turn_count or 0), executed_turns)
        db.commit()

    def _mark_execution_cancelled(self, db, execution_id: str) -> None:
        execution = db.query(ConversationExecution).filter(
            ConversationExecution.id == str(execution_id)
        ).first()
        if not execution:
            db.rollback()
            return
        execution.status = "cancelled"
        execution.finished_at = datetime.now()
        if execution.evaluation_id:
            evaluation = db.query(Evaluation).filter(Evaluation.id == str(execution.evaluation_id)).first()
            if evaluation:
                evaluation.status = "failed"
                evaluation.error_message = "任务已取消"
        db.commit()

    def _mark_execution_failed(self, db, execution_id: str, error: str) -> None:
        execution = db.query(ConversationExecution).filter(
            ConversationExecution.id == str(execution_id)
        ).first()
        if not execution:
            db.rollback()
            return
        execution.status = "failed"
        execution.finished_at = datetime.now()
        execution.execution_metadata = {
            **(execution.execution_metadata or {}),
            "error": str(error or ""),
        }
        if execution.evaluation_id:
            evaluation = db.query(Evaluation).filter(Evaluation.id == str(execution.evaluation_id)).first()
            if evaluation:
                evaluation.status = "failed"
                evaluation.error_message = str(error or "")
        db.commit()


conversation_executor = MultiTurnConversationExecutor()


__all__ = [
    "MultiTurnConversationExecutor",
    "conversation_executor",
]
