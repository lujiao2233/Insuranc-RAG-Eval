"""多轮会话 case 生成主服务。"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config.database import SessionLocal
from models.database import ConversationTestCase, ConversationTurn, Document, DocumentChunk, TestSet
from services.conversation_case_schema import (
    ConversationDependencyType,
    ConversationCaseSchema,
    get_case_schema_errors,
)
from services.conversation_chunk_selector import ChunkCluster, conversation_chunk_selector
from services.conversation_prompt_templates import (
    PROMPT_MULTI_TURN_CASE_GENERATION,
    PROMPT_MULTI_TURN_CASE_REPAIR,
    PROMPT_TURN_DEPENDENCY_HINT,
)
from services.llm_service import get_llm_service
from services.task_manager import task_manager
from utils.logger import get_logger

logger = get_logger("conversation_case_generator")


class ConversationCaseGenerator:
    """多轮会话 case 生成服务。"""

    def _get_concurrency_config(self, user_id: str) -> int:
        """从系统配置获取并发生成数"""
        default_concurrency = 3
        if not user_id:
            return default_concurrency
        
        db = None
        try:
            from config.database import SessionLocal
            from services.config_service import ConfigService
            
            db = SessionLocal()
            cs = ConfigService(db)
            conc_str = cs.get_config_value(user_id, "generation.concurrency", str(default_concurrency))
            try:
                concurrency = max(1, min(10, int(float(conc_str))))
            except (ValueError, TypeError):
                concurrency = default_concurrency
            return concurrency
        except Exception as e:
            logger.warning(f"获取并发配置失败，使用默认值: {e}")
            return default_concurrency
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass

    def generate_cases(
        self,
        testset_id: str,
        num_cases: int,
        turn_range: Any,
        case_type_ratio: Optional[Dict[str, float]],
        user_id: str,
        task_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
    ) -> List[str]:
        db = SessionLocal()
        try:
            testset = self._get_testset(db, testset_id, user_id)
            llm_service = get_llm_service(user_id=user_id, db=db)
            target_documents = self._load_target_documents(db, testset, user_id, document_ids)
            chunk_payloads = self._load_chunk_payloads(db, target_documents)

            min_turns, max_turns = self._parse_turn_range(turn_range)
            requested_cases = max(int(num_cases or 0), 0)
            if requested_cases <= 0:
                return []

            self._check_cancelled(task_id)
            self._update_progress(
                task_id,
                0.05,
                "正在准备多轮 case 生成素材...",
                current_step=0,
                total_steps=requested_cases,
                context_info={
                    "current_case": 0,
                    "current_turn": 0,
                    "total_cases": requested_cases,
                    "session_id": "",
                },
            )

            clusters = conversation_chunk_selector.select_chunks_for_case(
                chunk_payloads,
                {
                    "num_cases": requested_cases,
                    "case_type_ratio": case_type_ratio,
                },
            )
            if not clusters:
                raise RuntimeError("未能从现有切片中构造可用的多轮 case 素材")

            self._append_log(task_id, f"已选择 {len(clusters)} 个切片簇用于多轮 case 生成")
            total_steps = len(clusters)
            generated_cases: List[Dict[str, Any]] = []
            skipped_case_count = 0

            # 获取并发配置
            concurrency = self._get_concurrency_config(user_id)
            logger.info(f"多轮 case 并发生成启动: 总计划={total_steps}个, 并发数={concurrency}")

            import threading
            from concurrent.futures import ThreadPoolExecutor, as_completed
            
            _progress_lock = threading.Lock()
            _completed_count = 0

            def _generate_one_case(index: int, cluster: ChunkCluster) -> Optional[Dict[str, Any]]:
                """生成单个case（并发安全）"""
                nonlocal _completed_count
                
                self._check_cancelled(task_id)
                
                with _progress_lock:
                    _completed_count += 1
                    current_count = _completed_count
                
                self._update_progress(
                    task_id,
                    min(0.1 + (current_count - 1) / max(total_steps, 1) * 0.8, 0.95),
                    f"正在生成第 {current_count}/{total_steps} 个多轮 case",
                    current_step=current_count - 1,
                    total_steps=total_steps,
                    context_info={
                        "current_case": current_count,
                        "current_turn": 0,
                        "total_cases": total_steps,
                        "session_id": "",
                    },
                )
                self._append_log(
                    task_id,
                    f"生成 case {current_count}/{total_steps}: type={cluster.case_type}, anchor={cluster.anchor_chunk.get('id')}",
                )

                try:
                    case_dict = self._generate_case_dict(
                        llm_service=llm_service,
                        cluster=cluster,
                        min_turns=min_turns,
                        max_turns=max_turns,
                    )
                    return {
                        "cluster": cluster,
                        "case_dict": case_dict,
                    }
                except Exception as exc:
                    self._append_log(
                        task_id,
                        f"跳过 case {current_count}/{total_steps}: {exc}",
                    )
                    logger.warning(
                        "多轮 case 生成失败，已跳过该 case: index=%s/%s, type=%s, anchor=%s, error=%s",
                        current_count,
                        total_steps,
                        cluster.case_type,
                        cluster.anchor_chunk.get("id"),
                        exc,
                    )
                    return None

            # 并发生成
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                _future_to_idx = {
                    executor.submit(_generate_one_case, index, cluster): index
                    for index, cluster in enumerate(clusters, start=1)
                }
                for _future in as_completed(_future_to_idx):
                    _idx = _future_to_idx[_future]
                    try:
                        _result = _future.result()
                        if _result is not None:
                            generated_cases.append(_result)
                    except Exception as e:
                        skipped_case_count += 1
                        logger.error(f"多轮 case 并发生成异常: idx={_idx}, error={e}")

            self._check_cancelled(task_id)
            if not generated_cases:
                raise RuntimeError("多轮 case 生成失败：所有 case 在生成或自检阶段均未通过")

            self._update_progress(
                task_id,
                0.96,
                "正在校验并修复多轮 case 结构...",
                current_step=total_steps,
                total_steps=total_steps,
                context_info={
                    "current_case": total_steps,
                    "current_turn": 0,
                    "total_cases": total_steps,
                    "session_id": "",
                },
            )

            validated_cases, quality_report = self.validate_and_fix_cases(
                generated_cases=generated_cases,
                llm_service=llm_service,
                min_turns=min_turns,
                max_turns=max_turns,
                task_id=task_id,
            )
            quality_report["requested_case_count"] = requested_cases
            quality_report["generation_skipped_case_count"] = skipped_case_count
            if not validated_cases:
                raise RuntimeError("多轮 case 生成失败：所有已生成 case 在修复或复检阶段均未通过")
            self._append_log(
                task_id,
                "质量检查完成: "
                + f"有效 case {quality_report['valid_case_count']}，"
                + f"低质量 case {quality_report['low_quality_case_count']}，"
                + f"跳过 case {quality_report['skipped_case_count'] + skipped_case_count}，"
                + f"总轮数 {quality_report['total_turn_count']}",
            )

            case_ids: List[str] = []
            for item in validated_cases:
                schema = self._validate_case_dict(item["case_dict"])
                case_id = self._persist_case(
                    db,
                    testset_id,
                    item["cluster"],
                    schema,
                    quality_info=item["quality_info"],
                )
                case_ids.append(case_id)
            db.commit()

            final_cases = db.query(ConversationTestCase).filter(
                ConversationTestCase.testset_id == testset_id
            ).all()
            final_case_ids = [str(c.id) for c in final_cases]
            final_turn_count = db.query(ConversationTurn).filter(
                ConversationTurn.case_id.in_(final_case_ids)
            ).count() if final_case_ids else 0
            testset.question_count = final_turn_count
            testset.conversation_mode = "multi_turn"
            testset.testset_metadata = {
                **(testset.testset_metadata or {}),
                "conversation_quality_report": quality_report,
                "conversation_case_count": len(final_cases),
            }
            db.commit()

            self._update_progress(
                task_id,
                1.0,
                f"多轮 case 生成完成，共 {len(case_ids)} 个",
                current_step=len(case_ids),
                total_steps=total_steps,
                context_info={
                    "current_case": len(case_ids),
                    "current_turn": 0,
                    "total_cases": total_steps,
                    "session_id": "",
                },
            )
            return case_ids
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def _get_testset(self, db, testset_id: str, user_id: str) -> TestSet:
        testset = db.query(TestSet).filter(
            TestSet.id == str(testset_id),
            TestSet.user_id == str(user_id),
        ).first()
        if not testset:
            raise RuntimeError("测试集不存在或无权限")
        return testset

    def _load_target_documents(
        self,
        db,
        testset: TestSet,
        user_id: str,
        document_ids: Optional[List[str]],
    ) -> List[Document]:
        target_ids: List[str] = []
        if testset.document_id:
            target_ids.append(str(testset.document_id))
        for document_id in document_ids or []:
            if document_id and document_id not in target_ids:
                target_ids.append(str(document_id))
        if not target_ids:
            raise RuntimeError("测试集未关联可用文档，请先指定 document_ids")

        documents = db.query(Document).filter(
            Document.id.in_(target_ids),
            Document.user_id == str(user_id),
        ).all()
        document_map = {str(item.id): item for item in documents}
        if len(document_map) != len(target_ids):
            raise RuntimeError("存在无权限或不存在的文档")
        return [document_map[item] for item in target_ids]

    def _load_chunk_payloads(self, db, documents: Iterable[Document]) -> List[Dict[str, Any]]:
        payloads: List[Dict[str, Any]] = []
        for document in documents:
            chunks = db.query(DocumentChunk).filter(
                DocumentChunk.document_id == document.id
            ).order_by(DocumentChunk.sequence_number.asc()).all()
            if not chunks:
                if not document.is_analyzed:
                    raise RuntimeError(f"文档尚未分析：{document.filename}")
                raise RuntimeError(f"文档缺少切片数据，请重新分析：{document.filename}")
            for chunk in chunks:
                payloads.append(
                    {
                        "content": chunk.content,
                        "doc_id": str(document.id),
                        "filename": document.filename,
                        "chunk_id": str(chunk.id),
                        "metadata": chunk.chunk_metadata or {},
                        "entities": chunk.entities or [],
                        "sequence_number": chunk.sequence_number,
                        "start_char": chunk.start_char,
                        "end_char": chunk.end_char,
                    }
                )
        if not payloads:
            raise RuntimeError("未获取到可用于生成多轮 case 的切片")
        return payloads

    def _parse_turn_range(self, turn_range: Any) -> Tuple[int, int]:
        default = (3, 5)
        if isinstance(turn_range, dict):
            min_turns = turn_range.get("min") or turn_range.get("start")
            max_turns = turn_range.get("max") or turn_range.get("end")
        elif isinstance(turn_range, (list, tuple)) and len(turn_range) >= 2:
            min_turns, max_turns = turn_range[0], turn_range[1]
        else:
            return default
        try:
            min_value = max(int(min_turns), 3)
            max_value = min(int(max_turns), 5)
        except Exception:
            return default
        if min_value > max_value:
            min_value, max_value = max_value, min_value
        return min_value, max_value

    def _generate_case_dict(
        self,
        llm_service: Any,
        cluster: ChunkCluster,
        min_turns: int,
        max_turns: int,
    ) -> Dict[str, Any]:
        last_errors: List[str] = []
        feedback = ""
        for attempt in range(3):
            case_prompt = (
                self._build_case_prompt(cluster, min_turns, max_turns)
                if not feedback
                else self._build_case_repair_prompt(cluster, min_turns, max_turns, feedback)
            )
            raw_text = asyncio.run(
                llm_service.generate_text(
                    case_prompt,
                    temperature=0.3,
                    module_name="conversation_case_generation",
                )
            )
            case_dict = self._extract_json_object(raw_text)
            if not isinstance(case_dict, dict):
                last_errors = ["LLM 未返回合法 JSON 对象"]
                continue

            merged_case = dict(case_dict)
            merged_case["case_type"] = cluster.case_type

            dependency_result = self._generate_dependency_hints(llm_service, merged_case.get("turns") or [])
            if dependency_result:
                merged_case["turns"] = self._merge_turn_dependency_hints(
                    merged_case.get("turns") or [],
                    dependency_result,
                )
            merged_case["turns"], _ = self._normalize_turn_dependency_fields(
                merged_case.get("turns") or [],
                cluster,
            )

            errors = get_case_schema_errors(merged_case)
            if not errors:
                passed, reason = self._self_check_case(llm_service, cluster, merged_case)
                if passed:
                    return merged_case
                feedback = reason or "多轮 case 自检未通过"
                last_errors = [feedback]
                continue
            last_errors = errors
            if isinstance(merged_case.get("turns"), list) and merged_case.get("turns"):
                feedback = "; ".join(errors)

        raise RuntimeError(f"多轮 case 生成失败: {'; '.join(last_errors) if last_errors else '未知错误'}")

    def _build_case_prompt(self, cluster: ChunkCluster, min_turns: int, max_turns: int) -> str:
        anchor = self._format_chunk(cluster.anchor_chunk)
        supports = [
            self._format_chunk(chunk)
            for chunk in cluster.support_chunks
        ]
        support_text = "\n\n".join(
            f"[support_chunk_{index + 1}]\n{value}" for index, value in enumerate(supports)
        ) or "无"
        cluster_meta = json.dumps(cluster.cluster_metadata or {}, ensure_ascii=False, indent=2)
        return (
            PROMPT_MULTI_TURN_CASE_GENERATION.strip()
            + "\n\n"
            + f"本次指定的 case_type: {cluster.case_type}\n"
            + f"允许轮数范围: {min_turns}-{max_turns}\n"
            + "切片簇元数据：\n"
            + cluster_meta
            + "\n\n"
            + "[anchor_chunk]\n"
            + anchor
            + "\n\n"
            + "[support_chunks]\n"
            + support_text
        )

    def _build_case_repair_prompt(
        self,
        cluster: ChunkCluster,
        min_turns: int,
        max_turns: int,
        feedback: str,
    ) -> str:
        anchor = self._format_chunk(cluster.anchor_chunk)
        supports = [
            self._format_chunk(chunk)
            for chunk in cluster.support_chunks
        ]
        support_text = "\n\n".join(
            f"[support_chunk_{index + 1}]\n{value}" for index, value in enumerate(supports)
        ) or "无"
        return (
            PROMPT_MULTI_TURN_CASE_REPAIR.strip()
            + "\n\n"
            + f"本次指定的 case_type: {cluster.case_type}\n"
            + f"允许轮数范围: {min_turns}-{max_turns}\n"
            + "审核失败原因：\n"
            + feedback
            + "\n\n[anchor_chunk]\n"
            + anchor
            + "\n\n[support_chunks]\n"
            + support_text
        )

    def _generate_dependency_hints(
        self,
        llm_service: Any,
        turns: List[Dict[str, Any]],
    ) -> Optional[List[Dict[str, Any]]]:
        if not turns:
            return None
        prompt = (
            PROMPT_TURN_DEPENDENCY_HINT.strip()
            + "\n\n待标注 turns:\n"
            + json.dumps(turns, ensure_ascii=False, indent=2)
        )
        try:
            raw_text = asyncio.run(
                llm_service.generate_text(
                    prompt,
                    temperature=0.0,
                    module_name="conversation_dependency_hint",
                )
            )
        except Exception as exc:
            logger.warning(f"生成 dependency hint 失败，保留原结果: {exc}")
            return None

        parsed = self._extract_json_object(raw_text)
        if not isinstance(parsed, dict):
            return None
        hint_turns = parsed.get("turns")
        if not isinstance(hint_turns, list):
            return None
        return [item for item in hint_turns if isinstance(item, dict)]

    def _merge_turn_dependency_hints(
        self,
        original_turns: List[Dict[str, Any]],
        hint_turns: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        hint_map = {}
        for item in hint_turns:
            try:
                hint_map[int(item.get("turn_index"))] = item
            except Exception:
                continue

        merged: List[Dict[str, Any]] = []
        for item in original_turns:
            turn = dict(item)
            try:
                turn_index = int(turn.get("turn_index"))
            except Exception:
                merged.append(turn)
                continue
            hint = hint_map.get(turn_index)
            if hint:
                if hint.get("dependency_type"):
                    turn["dependency_type"] = hint["dependency_type"]
                if hint.get("context_hint") is not None:
                    turn["context_hint"] = hint["context_hint"]
                if hint.get("depends_on_turns") is not None:
                    turn["depends_on_turns"] = hint["depends_on_turns"]
                if hint.get("question_state_refs") is not None:
                    turn["question_state_refs"] = hint["question_state_refs"]
                if hint.get("evidence_chunk_ids") is not None:
                    turn["evidence_chunk_ids"] = hint["evidence_chunk_ids"]
            merged.append(turn)
        return merged

    def _get_available_chunk_ids(self, cluster: ChunkCluster) -> List[str]:
        chunk_ids: List[str] = []
        for chunk in [cluster.anchor_chunk] + list(cluster.support_chunks):
            chunk_id = str(chunk.get("id") or "").strip()
            if chunk_id and chunk_id not in chunk_ids:
                chunk_ids.append(chunk_id)
        return chunk_ids

    def _normalize_depends_on_turns(
        self,
        value: Any,
        current_turn_index: int,
    ) -> List[int]:
        if not isinstance(value, list):
            return []
        normalized: List[int] = []
        for item in value:
            try:
                turn_index = int(item)
            except Exception:
                continue
            if 1 <= turn_index < current_turn_index and turn_index not in normalized:
                normalized.append(turn_index)
        return normalized

    def _normalize_string_list(self, value: Any) -> List[str]:
        if not isinstance(value, list):
            return []
        normalized: List[str] = []
        for item in value:
            text = str(item or "").strip()
            if text and text not in normalized:
                normalized.append(text)
        return normalized

    def _normalize_evidence_chunk_ids(
        self,
        value: Any,
        available_chunk_ids: List[str],
    ) -> Tuple[List[str], bool]:
        if not isinstance(value, list):
            return [], True
        normalized: List[str] = []
        allowed = set(available_chunk_ids)
        for item in value:
            chunk_id = str(item or "").strip()
            if chunk_id and chunk_id in allowed and chunk_id not in normalized:
                normalized.append(chunk_id)
        return normalized, not normalized

    def _normalize_turn_dependency_fields(
        self,
        turns: List[Dict[str, Any]],
        cluster: ChunkCluster,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        quality_flags: List[str] = []
        available_chunk_ids = self._get_available_chunk_ids(cluster)
        default_evidence_chunk_ids = available_chunk_ids[:1]
        valid_dependency_types = {item.value for item in ConversationDependencyType}
        normalized_turns: List[Dict[str, Any]] = []

        for turn_index, raw_turn in enumerate(turns, start=1):
            turn = dict(raw_turn)
            turn["turn_index"] = turn_index

            dependency_type = str(turn.get("dependency_type") or "").strip()
            context_hint = str(turn.get("context_hint") or "").strip()
            depends_on_turns = self._normalize_depends_on_turns(
                turn.get("depends_on_turns"),
                turn_index,
            )
            question_state_refs = self._normalize_string_list(turn.get("question_state_refs"))
            evidence_chunk_ids, missing_evidence = self._normalize_evidence_chunk_ids(
                turn.get("evidence_chunk_ids"),
                available_chunk_ids,
            )

            if turn_index == 1:
                turn["dependency_type"] = ConversationDependencyType.none.value
                turn["context_hint"] = context_hint
                turn["depends_on_turns"] = []
                turn["question_state_refs"] = []
            else:
                if dependency_type not in valid_dependency_types or dependency_type == ConversationDependencyType.none.value:
                    turn["dependency_type"] = ConversationDependencyType.contextual.value
                    quality_flags.append("weak_dependency")
                else:
                    turn["dependency_type"] = dependency_type

                if not context_hint:
                    context_hint = "依赖前文已建立的问题语境"
                    quality_flags.append("weak_dependency")
                turn["context_hint"] = context_hint

                if not depends_on_turns:
                    depends_on_turns = [turn_index - 1]
                    quality_flags.append("weak_dependency")
                turn["depends_on_turns"] = depends_on_turns

                if not question_state_refs:
                    question_state_refs = [context_hint]
                    quality_flags.append("weak_dependency")
                turn["question_state_refs"] = question_state_refs

            if missing_evidence:
                quality_flags.append("missing_evidence_chunk_ids")
            turn["evidence_chunk_ids"] = evidence_chunk_ids or list(default_evidence_chunk_ids)
            normalized_turns.append(turn)

        return normalized_turns, quality_flags

    def _validate_case_dict(self, case_dict: Dict[str, Any]) -> ConversationCaseSchema:
        errors = get_case_schema_errors(case_dict)
        if errors:
            raise RuntimeError("case schema 校验失败: " + "; ".join(errors))
        return ConversationCaseSchema.model_validate(case_dict)

    def _extract_core_entity_name(self, cluster: ChunkCluster) -> str:
        candidates: List[str] = []
        for chunk in [cluster.anchor_chunk] + list(cluster.support_chunks):
            meta = chunk.get("chunk_metadata") or {}
            product_name = str(meta.get("product_name") or "").strip()
            if product_name:
                candidates.append(product_name)
            product_entities = meta.get("product_entities")
            if isinstance(product_entities, list):
                candidates.extend(str(item).strip() for item in product_entities if str(item).strip())
            elif isinstance(product_entities, str) and product_entities.strip():
                candidates.append(product_entities.strip())
        return candidates[0] if candidates else ""

    def _build_case_reference_text(self, cluster: ChunkCluster) -> str:
        sections: List[str] = []
        for index, chunk in enumerate([cluster.anchor_chunk] + list(cluster.support_chunks)):
            role = "anchor_chunk" if index == 0 else f"support_chunk_{index}"
            formatted_chunk = self._format_chunk(chunk)
            sections.append(f"[{role}]\n{formatted_chunk}")
        return "\n\n".join(sections)

    def _self_check_case(
        self,
        llm_service: Any,
        cluster: ChunkCluster,
        case_dict: Dict[str, Any],
    ) -> Tuple[bool, str]:
        turns = [dict(item) for item in (case_dict.get("turns") or []) if isinstance(item, dict)]
        if not turns:
            return False, "多轮 case 缺少有效 turns"

        reference_text = self._build_case_reference_text(cluster)
        core_entity = self._extract_core_entity_name(cluster)

        for index, turn in enumerate(turns, start=1):
            prompt = f"""
请作为一位多轮会话测试集审核员，对以下某一轮问答进行联合审核（事实一致性 + 多轮依赖合理性 + 表达规范 + 实体锚点）。
审核目标优先服务于 4 个指标：Knowledge Retention、Conversation Relevancy、Conversation Completeness、Role Adherence。

【参考材料】
{reference_text[:5000]}

【case 类型】
{case_dict.get("case_type") or cluster.case_type}

【前文对话】
{json.dumps(turns[: index - 1], ensure_ascii=False, indent=2) if index > 1 else "无"}

【当前轮次】
轮次：{index}
问题：{str(turn.get("question") or "").strip()}
答案：{str(turn.get("expected_answer") or "").strip()}
依赖类型：{str(turn.get("dependency_type") or "").strip()}
上下文提示：{str(turn.get("context_hint") or "").strip()}
依赖轮次：{json.dumps(turn.get("depends_on_turns") or [], ensure_ascii=False)}
继承的问题要素：{json.dumps(turn.get("question_state_refs") or [], ensure_ascii=False)}
证据切片：{json.dumps(turn.get("evidence_chunk_ids") or [], ensure_ascii=False)}
核心实体（可为空）：{core_entity or "未知"}

【检查项一：事实一致性（hallucination_pass）】
1. 当前轮答案中的核心结论和关键事实必须能在参考材料中找到依据，或可被清晰推断。
2. 答案必须以【正文】为直接依据，【背景信息】只用于实体锚定和语境补充，不得把【背景信息】本身当作答案证据。
3. 允许简要概括和措辞改写，但不得新增参考材料中不存在的关键事实（金额、比例、期限、规则名称、主体名称、所需材料、流程节点）。
4. 若答案引入了参考材料未出现的关键事实，或与材料冲突，判不通过。

【检查项二：多轮依赖合理性（dependency_pass）】
1. 第 1 轮必须可以仅依据参考材料直接作答，不能依赖并不存在的前文。
2. 第 2 轮及之后必须与前文问题链有真实关联，重点看是否继承了前文已提出的对象、条件、范围、主题、比较维度或指代对象。
3. 依赖应建立在前文问题链和当前切片证据上，不要把 expected_answer 的措辞或表述方式当作依赖依据。
4. depends_on_turns、question_state_refs 与当前问题内容应基本一致；如果标注与真实依赖明显不符，判不通过。
5. 依赖前文后仍然不能引入参考材料中不存在的新事实。
6. single_chunk_deep 类型下，后续轮必须围绕同一主题深化，不能从当前切片跳转到未出现的新章节主题。

【检查项三：规范与实体锚点（relevance_pass）】
1. 问题中禁止出现来源视角词：根据材料、上述材料、文档中提到、材料A、材料B、该文档指出。
2. 如果问题涉及具体产品、合同、保障责任、规则对象，必须使用参考材料中明确出现的实体名称；不要使用“这个产品/该方案/它”等模糊代词作为首次指代。
3. 允许在多轮对话中引用前文已明确的对象，但不得把“刚才提到的材料/上文材料”作为指代对象。

【输出要求】
请只输出 JSON：
{{
  "pass": true/false,
  "hallucination_pass": true/false,
  "dependency_pass": true/false,
  "relevance_pass": true/false,
  "reason": "简短理由"
}}
""".strip()
            try:
                raw_text = asyncio.run(
                    llm_service.generate_text(
                        prompt,
                        temperature=0.0,
                        module_name="conversation_case_self_check",
                    )
                )
                parsed = self._extract_json_object(raw_text)
                if not isinstance(parsed, dict):
                    continue
                hallucination_pass = bool(parsed.get("hallucination_pass", True))
                dependency_pass = bool(parsed.get("dependency_pass", True))
                relevance_pass = bool(parsed.get("relevance_pass", True))
                passed = bool(parsed.get("pass", False))
                reason = str(parsed.get("reason") or "").strip()
                if not (passed and hallucination_pass and dependency_pass and relevance_pass):
                    return False, f"第 {index} 轮未通过自检: {reason or '事实一致性/依赖/实体锚点检查失败'}"
            except Exception as exc:
                logger.warning(f"多轮 case 自检失败，默认放行该轮: {exc}")
                continue
        return True, ""

    def _persist_case(
        self,
        db,
        testset_id: str,
        cluster: ChunkCluster,
        schema: ConversationCaseSchema,
        quality_info: Optional[Dict[str, Any]] = None,
    ) -> str:
        case = ConversationTestCase(
            testset_id=str(testset_id),
            case_type=schema.case_type.value,
            anchor_chunk_id=cluster.anchor_chunk.get("id") or None,
            support_chunk_ids=[item.get("id") for item in cluster.support_chunks if item.get("id")],
            evaluation_criteria=schema.evaluation_criteria,
            turn_count=len(schema.turns),
            case_metadata={
                "cluster_score": cluster.score,
                "cluster_metadata": cluster.cluster_metadata,
                "anchor_document_id": cluster.anchor_chunk.get("document_id"),
                "support_document_ids": [
                    item.get("document_id") for item in cluster.support_chunks if item.get("document_id")
                ],
                "source_filenames": list(
                    {
                        value for value in [cluster.anchor_chunk.get("filename")] + [item.get("filename") for item in cluster.support_chunks]
                        if value
                    }
                ),
                "quality_info": quality_info or {
                    "is_low_quality": False,
                    "quality_flags": [],
                },
            },
        )
        db.add(case)
        db.flush()

        for turn_schema in schema.turns:
            turn = ConversationTurn(
                case_id=case.id,
                turn_index=turn_schema.turn_index,
                question=turn_schema.question,
                expected_answer=turn_schema.expected_answer,
                dependency_type=turn_schema.dependency_type.value,
                context_hint=turn_schema.context_hint,
                turn_metadata={
                    "depends_on_turns": list(turn_schema.depends_on_turns),
                    "question_state_refs": list(turn_schema.question_state_refs),
                    "evidence_chunk_ids": list(turn_schema.evidence_chunk_ids),
                },
            )
            db.add(turn)
        db.flush()
        return str(case.id)

    def _build_bg_lines(self, meta: Dict[str, Any]) -> List[str]:
        lines: List[str] = []
        field_map = [
            ("product_name", "产品"),
            ("product_entities", "相关产品实体"),
            ("doc_type", "文档类型"),
            ("purpose_summary", "文档用途"),
            ("section_level", "章节层级"),
            ("section_title", "章节"),
            ("breadcrumb_path", "章节路径"),
            ("knowledge_type", "知识类型"),
            ("section_summary", "摘要"),
            ("key_terms", "关键术语"),
            ("channel", "渠道"),
            ("section_tags", "章节标签"),
        ]
        for key, label in field_map:
            value = meta.get(key)
            if value is None or value == "":
                continue
            if isinstance(value, list):
                if not value:
                    continue
                value = "、".join(str(v) for v in value if v is not None and str(v).strip())
                if not value:
                    continue
            lines.append(f"{label}: {value}")
        return lines

    def _format_chunk(self, chunk: Dict[str, Any]) -> str:
        meta = chunk.get("chunk_metadata") or {}
        header_lines = [
            f"chunk_id: {chunk.get('id') or ''}",
            f"document_id: {chunk.get('document_id') or ''}",
            f"filename: {chunk.get('filename') or ''}",
            f"sequence_number: {chunk.get('sequence_number') or ''}",
        ]
        entities = chunk.get("entities") or []
        if entities:
            if isinstance(entities, list):
                header_lines.append(
                    "entities: " + "、".join(str(item).strip() for item in entities if str(item).strip())
                )
            else:
                header_lines.append(f"entities: {entities}")

        bg_lines = self._build_bg_lines(meta)
        content = str(chunk.get("content") or "").strip()
        text_parts = ["\n".join(header_lines)]
        if bg_lines:
            text_parts.append("【背景信息】\n" + "\n".join(bg_lines))
        text_parts.append("【正文】\n" + content)
        return "\n\n".join(part for part in text_parts if part.strip())

    def _extract_json_object(self, raw_text: str) -> Optional[Dict[str, Any]]:
        text = str(raw_text or "").strip()
        if not text:
            return None

        fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", text)
        if fenced_match:
            text = fenced_match.group(1).strip()

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        object_match = re.search(r"\{[\s\S]*\}", text)
        if not object_match:
            return None
        candidate = object_match.group(0)
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return None
        return None

    def _check_cancelled(self, task_id: Optional[str]) -> None:
        if task_id:
            task_manager.ensure_not_cancelled(task_id)

    def _update_progress(
        self,
        task_id: Optional[str],
        progress: float,
        message: str,
        *,
        current_step: Optional[int] = None,
        total_steps: Optional[int] = None,
        context_info: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not task_id:
            return
        task_manager.update_progress(
            task_id,
            progress,
            message,
            current_step=current_step,
            total_steps=total_steps,
            context_info=context_info,
        )

    def _append_log(self, task_id: Optional[str], message: str) -> None:
        if task_id:
            task_manager.append_log(task_id, message)

    def validate_and_fix_cases(
        self,
        generated_cases: List[Dict[str, Any]],
        llm_service: Any,
        min_turns: int = 3,
        max_turns: int = 5,
        task_id: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """生成后进行结构化校验、必要修复与质量标记。"""
        validated_cases: List[Dict[str, Any]] = []
        low_quality_case_count = 0
        total_turn_count = 0
        skipped_case_count = 0

        for index, item in enumerate(generated_cases, start=1):
            cluster = item["cluster"]
            try:
                case_dict = dict(item["case_dict"])
                turns = [dict(turn) for turn in (case_dict.get("turns") or []) if isinstance(turn, dict)]
                quality_flags: List[str] = []

                if len(turns) > max_turns:
                    turns = turns[:max_turns]
                    quality_flags.append("truncated_turns")

                if len(turns) < min_turns:
                    added_turns = self._supplement_turns(
                        llm_service=llm_service,
                        cluster=cluster,
                        case_dict=case_dict,
                        turns=turns,
                        target_turn_count=min_turns,
                    )
                    if added_turns:
                        turns.extend(added_turns)
                        quality_flags.append("auto_supplemented_turns")
                    if len(turns) < min_turns:
                        raise RuntimeError("case 修复失败: 无法补足最少轮数")

                normalized_turns: List[Dict[str, Any]] = []
                for turn_index, raw_turn in enumerate(turns[:max_turns], start=1):
                    turn = dict(raw_turn)
                    turn["turn_index"] = turn_index

                    expected_answer = str(turn.get("expected_answer") or "").strip()
                    if not expected_answer:
                        regenerated_answer = self._regenerate_expected_answer(
                            llm_service=llm_service,
                            cluster=cluster,
                            case_type=case_dict.get("case_type") or cluster.case_type,
                            turns=normalized_turns,
                            question=str(turn.get("question") or "").strip(),
                        )
                        turn["expected_answer"] = regenerated_answer
                        quality_flags.append("regenerated_expected_answer")

                    normalized_turns.append(turn)

                case_dict["turns"] = normalized_turns
                case_dict["turns"], dependency_quality_flags = self._normalize_turn_dependency_fields(
                    case_dict["turns"],
                    cluster,
                )
                quality_flags.extend(dependency_quality_flags)
                errors = get_case_schema_errors(case_dict)
                if errors:
                    raise RuntimeError("case 修复后仍不合法: " + "; ".join(errors))

                passed, reason = self._self_check_case(llm_service, cluster, case_dict)
                if not passed:
                    raise RuntimeError(reason or "case 修复后未通过事实一致性/依赖合理性检查")

                is_low_quality = bool(quality_flags)
                if is_low_quality:
                    low_quality_case_count += 1

                total_turn_count += len(normalized_turns)
                validated_cases.append(
                    {
                        "cluster": cluster,
                        "case_dict": case_dict,
                        "quality_info": {
                            "is_low_quality": is_low_quality,
                            "quality_flags": sorted(set(quality_flags)),
                        },
                    }
                )
            except Exception as exc:
                skipped_case_count += 1
                self._append_log(task_id, f"跳过已生成 case {index}/{len(generated_cases)}: {exc}")
                logger.warning(
                    "多轮 case 校验/修复失败，已跳过该 case: index=%s/%s, type=%s, anchor=%s, error=%s",
                    index,
                    len(generated_cases),
                    cluster.case_type,
                    cluster.anchor_chunk.get("id"),
                    exc,
                )
                continue

        quality_report = {
            "valid_case_count": len(validated_cases) - low_quality_case_count,
            "low_quality_case_count": low_quality_case_count,
            "skipped_case_count": skipped_case_count,
            "total_turn_count": total_turn_count,
        }
        return validated_cases, quality_report

    def _supplement_turns(
        self,
        llm_service: Any,
        cluster: ChunkCluster,
        case_dict: Dict[str, Any],
        turns: List[Dict[str, Any]],
        target_turn_count: int,
    ) -> List[Dict[str, Any]]:
        missing_count = max(target_turn_count - len(turns), 0)
        if missing_count <= 0:
            return []

        existing_turns = turns or []
        prompt = (
            PROMPT_MULTI_TURN_CASE_GENERATION.strip()
            + "\n\n当前已有一个多轮 case，但轮数不足，请只补充缺失轮次。\n"
            + f"case_type: {case_dict.get('case_type') or cluster.case_type}\n"
            + f"需要补充的轮数: {missing_count}\n"
            + "已有 turns:\n"
            + json.dumps(existing_turns, ensure_ascii=False, indent=2)
            + "\n\n请输出一个 JSON 对象，格式为：\n"
            + '{"turns":[{"turn_index":4,"question":"...","expected_answer":"...","dependency_type":"accumulative","context_hint":"...","depends_on_turns":[3],"question_state_refs":["前文已确认的条件"],"evidence_chunk_ids":["chunk-id"]}]}'
        )
        try:
            raw_text = asyncio.run(
                llm_service.generate_text(
                    prompt,
                    temperature=0.2,
                    module_name="conversation_case_supplement",
                )
            )
            parsed = self._extract_json_object(raw_text)
            candidate_turns = parsed.get("turns") if isinstance(parsed, dict) else None
            if isinstance(candidate_turns, list):
                supplement = [dict(item) for item in candidate_turns if isinstance(item, dict)]
                if supplement:
                    return supplement[:missing_count]
        except Exception as exc:
            logger.warning(f"自动补轮失败，回退到本地补轮: {exc}")

        fallback_turns: List[Dict[str, Any]] = []
        for offset in range(missing_count):
            turn_index = len(existing_turns) + len(fallback_turns) + 1
            fallback_turns.append(
                {
                    "turn_index": turn_index,
                    "question": f"结合前面的讨论，第 {turn_index} 轮还需要补充说明什么？",
                    "expected_answer": "需要结合前文已确认的信息和当前材料继续补充说明。",
                    "dependency_type": ConversationDependencyType.accumulative.value,
                    "context_hint": "依赖前文累计形成的问题语境和限制条件",
                    "depends_on_turns": [turn_index - 1],
                    "question_state_refs": ["前文累计形成的讨论对象和限制条件"],
                    "evidence_chunk_ids": self._get_available_chunk_ids(cluster)[:1],
                }
            )
        return fallback_turns

    def _regenerate_expected_answer(
        self,
        llm_service: Any,
        cluster: ChunkCluster,
        case_type: str,
        turns: List[Dict[str, Any]],
        question: str,
    ) -> str:
        prompt = (
            "你是一名多轮对话参考答案补全助手。请基于给定切片簇和前文对话，"
            "为当前问题生成一个简洁、准确、非空的 expected_answer。"
            "\n只输出 JSON，对象格式为：{\"expected_answer\":\"...\"}"
            + "\n\ncase_type: "
            + str(case_type)
            + "\n当前问题: "
            + question
            + "\n已有前文 turns:\n"
            + json.dumps(turns, ensure_ascii=False, indent=2)
            + "\n\nanchor_chunk:\n"
            + self._format_chunk(cluster.anchor_chunk)
            + "\n\nsupport_chunks:\n"
            + (
                "\n".join(self._format_chunk(item) for item in cluster.support_chunks)
                if cluster.support_chunks
                else "无"
            )
        )
        try:
            raw_text = asyncio.run(
                llm_service.generate_text(
                    prompt,
                    temperature=0.1,
                    module_name="conversation_expected_answer_regen",
                )
            )
            parsed = self._extract_json_object(raw_text)
            if isinstance(parsed, dict):
                expected_answer = str(parsed.get("expected_answer") or "").strip()
                if expected_answer:
                    return expected_answer
        except Exception as exc:
            logger.warning(f"自动重生成 expected_answer 失败，使用兜底答案: {exc}")
        return "需要结合前文上下文和当前材料信息进行回答。"


conversation_case_generator = ConversationCaseGenerator()


__all__ = [
    "ConversationCaseGenerator",
    "conversation_case_generator",
]
