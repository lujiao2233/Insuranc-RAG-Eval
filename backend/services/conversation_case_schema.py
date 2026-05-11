"""多轮会话 case 的中间产物 schema 与校验工具。"""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError


class ConversationCaseType(str, Enum):
    single_chunk_deep = "single_chunk_deep"
    same_doc_chain = "same_doc_chain"
    cross_doc_assoc = "cross_doc_assoc"


class ConversationDependencyType(str, Enum):
    none = "none"
    contextual = "contextual"
    referential = "referential"
    accumulative = "accumulative"


class ConversationTurnSchema(BaseModel):
    turn_index: int = Field(..., ge=1)
    question: str = Field(..., min_length=1)
    expected_answer: str = Field(..., min_length=1)
    dependency_type: ConversationDependencyType = ConversationDependencyType.none
    context_hint: Optional[str] = None
    depends_on_turns: List[int] = Field(default_factory=list)
    question_state_refs: List[str] = Field(default_factory=list)
    evidence_chunk_ids: List[str] = Field(default_factory=list)

    model_config = {"str_strip_whitespace": True}


class ConversationCaseSchema(BaseModel):
    case_type: ConversationCaseType
    anchor_chunk: Optional[Dict[str, Any]] = None
    support_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    turns: List[ConversationTurnSchema] = Field(default_factory=list)
    evaluation_criteria: Optional[str] = ""

    model_config = {"str_strip_whitespace": True}


def get_case_schema_errors(case_dict: Dict[str, Any]) -> List[str]:
    """返回 case schema 校验错误列表。"""
    try:
        case = ConversationCaseSchema.model_validate(case_dict)
    except ValidationError as exc:
        return [err["msg"] for err in exc.errors()]

    errors: List[str] = []
    turns = case.turns

    if not 3 <= len(turns) <= 5:
        errors.append("turns 数量必须在 3 到 5 之间")

    for idx, turn in enumerate(turns):
        if not turn.expected_answer.strip():
            errors.append(f"第 {idx + 1} 轮 expected_answer 不能为空")
        if not turn.evidence_chunk_ids:
            errors.append(f"第 {idx + 1} 轮 evidence_chunk_ids 不能为空")
        if idx == 0:
            if turn.dependency_type != ConversationDependencyType.none:
                errors.append("第 1 轮 dependency_type 必须为 none")
            if turn.depends_on_turns:
                errors.append("第 1 轮 depends_on_turns 必须为空")
            if turn.question_state_refs:
                errors.append("第 1 轮 question_state_refs 必须为空")
            continue

        if turn.dependency_type == ConversationDependencyType.none:
            errors.append(f"第 {idx + 1} 轮 dependency_type 不能为 none")
        if not turn.depends_on_turns:
            errors.append(f"第 {idx + 1} 轮 depends_on_turns 不能为空")
        else:
            invalid_depends = [
                ref for ref in turn.depends_on_turns
                if ref < 1 or ref >= turn.turn_index
            ]
            if invalid_depends:
                errors.append(
                    f"第 {idx + 1} 轮 depends_on_turns 包含非法轮次: {invalid_depends}"
                )
        if not turn.question_state_refs:
            errors.append(f"第 {idx + 1} 轮 question_state_refs 不能为空")

    return errors


def validate_case_schema(case_dict: Dict[str, Any]) -> bool:
    """校验 case 是否满足 schema 与业务规则。"""
    return not get_case_schema_errors(case_dict)


__all__ = [
    "ConversationCaseType",
    "ConversationDependencyType",
    "ConversationTurnSchema",
    "ConversationCaseSchema",
    "get_case_schema_errors",
    "validate_case_schema",
]
