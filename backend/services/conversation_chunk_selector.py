"""多轮会话 case 的切片选材服务。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
import math
import re


CASE_TYPE_SINGLE_CHUNK_DEEP = "single_chunk_deep"
CASE_TYPE_SAME_DOC_CHAIN = "same_doc_chain"
CASE_TYPE_CROSS_DOC_ASSOC = "cross_doc_assoc"

SUPPORTED_CASE_TYPES = (
    CASE_TYPE_SINGLE_CHUNK_DEEP,
    CASE_TYPE_SAME_DOC_CHAIN,
    CASE_TYPE_CROSS_DOC_ASSOC,
)

DEFAULT_CASE_TYPE_RATIO: Dict[str, float] = {
    CASE_TYPE_SINGLE_CHUNK_DEEP: 0.2,
    CASE_TYPE_SAME_DOC_CHAIN: 0.6,
    CASE_TYPE_CROSS_DOC_ASSOC: 0.2,
}


@dataclass
class ChunkCluster:
    case_type: str
    anchor_chunk: Dict[str, Any]
    support_chunks: List[Dict[str, Any]]
    score: float
    cluster_metadata: Dict[str, Any]


class ConversationChunkSelector:
    """为多轮 case 生成准备切片簇。"""

    def select_chunks_for_case(
        self,
        documents: Iterable[Any],
        case_type_config: Optional[Dict[str, Any]] = None,
    ) -> List[ChunkCluster]:
        config = case_type_config or {}
        chunks = self._normalize_chunks(documents)
        if not chunks:
            return []

        plan = self._build_case_type_plan(
            num_cases=int(config.get("num_cases") or 1),
            explicit_case_type=config.get("case_type"),
            case_type_ratio=config.get("case_type_ratio"),
        )
        if not plan:
            return []

        clusters: List[ChunkCluster] = []
        used_signatures = set()
        for case_type in plan:
            cluster = self._select_cluster_by_type(chunks, case_type, used_signatures)
            if cluster is None:
                continue
            clusters.append(cluster)
            used_signatures.add(self._cluster_signature(cluster))
        return clusters

    def _build_case_type_plan(
        self,
        num_cases: int,
        explicit_case_type: Optional[str],
        case_type_ratio: Optional[Dict[str, float]],
    ) -> List[str]:
        if num_cases <= 0:
            return []
        if explicit_case_type in SUPPORTED_CASE_TYPES:
            return [str(explicit_case_type)] * num_cases

        ratio = self._normalize_ratio(case_type_ratio)
        raw_counts = {case_type: ratio[case_type] * num_cases for case_type in SUPPORTED_CASE_TYPES}
        counts = {case_type: int(math.floor(value)) for case_type, value in raw_counts.items()}
        remainder = num_cases - sum(counts.values())
        order = sorted(
            SUPPORTED_CASE_TYPES,
            key=lambda item: (raw_counts[item] - counts[item], ratio[item]),
            reverse=True,
        )
        for case_type in order[:remainder]:
            counts[case_type] += 1

        plan: List[str] = []
        for case_type in SUPPORTED_CASE_TYPES:
            plan.extend([case_type] * counts[case_type])
        return plan[:num_cases]

    def _normalize_ratio(self, custom_ratio: Optional[Dict[str, float]]) -> Dict[str, float]:
        ratio: Dict[str, float] = {}
        source = custom_ratio or DEFAULT_CASE_TYPE_RATIO
        total = 0.0
        for case_type in SUPPORTED_CASE_TYPES:
            value = source.get(case_type, DEFAULT_CASE_TYPE_RATIO[case_type])
            try:
                numeric = max(float(value), 0.0)
            except Exception:
                numeric = DEFAULT_CASE_TYPE_RATIO[case_type]
            ratio[case_type] = numeric
            total += numeric
        if total <= 0:
            return dict(DEFAULT_CASE_TYPE_RATIO)
        return {case_type: ratio[case_type] / total for case_type in SUPPORTED_CASE_TYPES}

    def _normalize_chunks(self, documents: Iterable[Any]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in documents:
            chunk = self._normalize_chunk(item)
            if chunk is None:
                continue
            normalized.append(chunk)
        return normalized

    def _normalize_chunk(self, item: Any) -> Optional[Dict[str, Any]]:
        if item is None:
            return None

        if isinstance(item, dict):
            content = str(item.get("content") or item.get("chunk") or "").strip()
            chunk_id = item.get("chunk_id") or item.get("id")
            document_id = item.get("doc_id") or item.get("document_id")
            metadata = item.get("metadata") or item.get("chunk_metadata") or {}
            entities = item.get("entities") or []
            sequence_number = item.get("sequence_number")
            filename = item.get("filename") or ""
        else:
            content = str(getattr(item, "content", "") or "").strip()
            chunk_id = getattr(item, "id", None)
            document_id = getattr(item, "document_id", None)
            metadata = getattr(item, "chunk_metadata", None) or {}
            entities = getattr(item, "entities", None) or []
            sequence_number = getattr(item, "sequence_number", None)
            filename = getattr(getattr(item, "document", None), "filename", "") or ""

        if not content:
            return None

        return {
            "id": str(chunk_id or ""),
            "content": content,
            "document_id": str(document_id or ""),
            "filename": filename,
            "sequence_number": self._to_int(sequence_number),
            "chunk_metadata": metadata if isinstance(metadata, dict) else {},
            "entities": self._to_str_list(entities),
        }

    def _select_cluster_by_type(
        self,
        chunks: List[Dict[str, Any]],
        case_type: str,
        used_signatures: set,
    ) -> Optional[ChunkCluster]:
        selector_map = {
            CASE_TYPE_SINGLE_CHUNK_DEEP: self._select_single_chunk_deep,
            CASE_TYPE_SAME_DOC_CHAIN: self._select_same_doc_chain,
            CASE_TYPE_CROSS_DOC_ASSOC: self._select_cross_doc_assoc,
        }
        selector = selector_map.get(case_type)
        if selector is None:
            return None

        cluster = selector(chunks, used_signatures)
        if cluster is not None:
            return cluster

        if case_type == CASE_TYPE_CROSS_DOC_ASSOC:
            return self._select_same_doc_chain(chunks, used_signatures) or self._select_single_chunk_deep(chunks, used_signatures)
        if case_type == CASE_TYPE_SAME_DOC_CHAIN:
            return self._select_single_chunk_deep(chunks, used_signatures)
        return None

    def _select_single_chunk_deep(
        self,
        chunks: List[Dict[str, Any]],
        used_signatures: set,
    ) -> Optional[ChunkCluster]:
        ranked = sorted(chunks, key=self._single_chunk_score, reverse=True)
        for chunk in ranked:
            cluster = ChunkCluster(
                case_type=CASE_TYPE_SINGLE_CHUNK_DEEP,
                anchor_chunk=chunk,
                support_chunks=[],
                score=round(self._single_chunk_score(chunk), 4),
                cluster_metadata={
                    "strategy": CASE_TYPE_SINGLE_CHUNK_DEEP,
                    "document_id": chunk.get("document_id"),
                    "reason": "基于单切片信息密度进行深挖",
                },
            )
            if self._cluster_signature(cluster) not in used_signatures:
                return cluster
        return None

    def _select_same_doc_chain(
        self,
        chunks: List[Dict[str, Any]],
        used_signatures: set,
    ) -> Optional[ChunkCluster]:
        docs = self._group_by_document(chunks)
        candidates: List[ChunkCluster] = []
        for doc_id, doc_chunks in docs.items():
            if len(doc_chunks) < 2:
                continue
            ordered = sorted(doc_chunks, key=lambda item: item.get("sequence_number", 0))
            for window_size in (3, 2):
                if len(ordered) < window_size:
                    continue
                for idx in range(len(ordered) - window_size + 1):
                    cluster_chunks = ordered[idx: idx + window_size]
                    score = self._same_doc_chain_score(cluster_chunks)
                    candidates.append(
                        ChunkCluster(
                            case_type=CASE_TYPE_SAME_DOC_CHAIN,
                            anchor_chunk=cluster_chunks[0],
                            support_chunks=cluster_chunks[1:],
                            score=round(score, 4),
                            cluster_metadata={
                                "strategy": CASE_TYPE_SAME_DOC_CHAIN,
                                "document_id": doc_id,
                                "chain_length": window_size,
                                "reason": "同文档切片按顺序构成逻辑链",
                            },
                        )
                    )
        candidates.sort(key=lambda item: item.score, reverse=True)
        for cluster in candidates:
            if self._cluster_signature(cluster) not in used_signatures:
                return cluster
        return None

    def _select_cross_doc_assoc(
        self,
        chunks: List[Dict[str, Any]],
        used_signatures: set,
    ) -> Optional[ChunkCluster]:
        candidates: List[ChunkCluster] = []
        for idx, left in enumerate(chunks):
            for right in chunks[idx + 1:]:
                if left.get("document_id") == right.get("document_id"):
                    continue
                score = self._cross_doc_score(left, right)
                if score <= 0:
                    continue
                anchor, support = self._order_cross_doc_pair(left, right)
                candidates.append(
                    ChunkCluster(
                        case_type=CASE_TYPE_CROSS_DOC_ASSOC,
                        anchor_chunk=anchor,
                        support_chunks=[support],
                        score=round(score, 4),
                        cluster_metadata={
                            "strategy": CASE_TYPE_CROSS_DOC_ASSOC,
                            "document_ids": [anchor.get("document_id"), support.get("document_id")],
                            "reason": "跨文档共享主题或实体关联",
                        },
                    )
                )
        candidates.sort(key=lambda item: item.score, reverse=True)
        for cluster in candidates:
            if self._cluster_signature(cluster) not in used_signatures:
                return cluster
        return None

    def _single_chunk_score(self, chunk: Dict[str, Any]) -> float:
        meta = chunk.get("chunk_metadata") or {}
        text = chunk.get("content") or ""
        content_score = min(len(text) / 500.0, 1.0)
        metadata_score = 0.0
        if meta.get("section_summary"):
            metadata_score += 0.25
        if meta.get("knowledge_type"):
            metadata_score += 0.2
        if self._extract_terms(chunk):
            metadata_score += 0.2
        if self._to_str_list(meta.get("product_entities")) or chunk.get("entities"):
            metadata_score += 0.15
        if meta.get("breadcrumb_path") or meta.get("section_title"):
            metadata_score += 0.1
        return content_score + metadata_score

    def _same_doc_chain_score(self, cluster_chunks: List[Dict[str, Any]]) -> float:
        if len(cluster_chunks) < 2:
            return 0.0
        adjacency_score = 0.0
        similarity_score = 0.0
        transition_bonus = 0.0
        for left, right in zip(cluster_chunks, cluster_chunks[1:]):
            left_seq = left.get("sequence_number", 0)
            right_seq = right.get("sequence_number", 0)
            gap = abs(right_seq - left_seq)
            adjacency_score += 1.0 if gap <= 1 else max(0.2, 1.0 - 0.15 * gap)
            similarity_score += self._term_similarity(left, right)
            if self._knowledge_type(left) != self._knowledge_type(right):
                transition_bonus += 0.2
        steps = len(cluster_chunks) - 1
        richness = sum(self._single_chunk_score(chunk) for chunk in cluster_chunks) / len(cluster_chunks)
        return (
            0.35 * (adjacency_score / steps)
            + 0.35 * (similarity_score / steps)
            + 0.15 * min(transition_bonus, 1.0)
            + 0.15 * min(richness, 1.0)
        )

    def _cross_doc_score(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        term_score = self._term_similarity(left, right)
        type_score = 1.0 if self._knowledge_type(left) and self._knowledge_type(left) == self._knowledge_type(right) else 0.3
        entity_score = self._entity_overlap_score(left, right)
        semantic_score = self._text_similarity(left.get("content", ""), right.get("content", ""))
        return 0.35 * term_score + 0.25 * type_score + 0.20 * entity_score + 0.20 * semantic_score

    def _order_cross_doc_pair(self, left: Dict[str, Any], right: Dict[str, Any]) -> tuple[Dict[str, Any], Dict[str, Any]]:
        if self._single_chunk_score(left) >= self._single_chunk_score(right):
            return left, right
        return right, left

    def _group_by_document(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in chunks:
            doc_id = chunk.get("document_id") or ""
            grouped.setdefault(doc_id, []).append(chunk)
        return grouped

    def _cluster_signature(self, cluster: ChunkCluster) -> tuple:
        chunk_ids = [cluster.anchor_chunk.get("id")] + [item.get("id") for item in cluster.support_chunks]
        normalized_ids = tuple(sorted(str(item or "") for item in chunk_ids))
        return cluster.case_type, normalized_ids

    def _extract_terms(self, chunk: Dict[str, Any]) -> List[str]:
        meta = chunk.get("chunk_metadata") or {}
        terms = self._to_str_list(meta.get("key_terms"))
        if terms:
            return terms
        terms = self._to_str_list(meta.get("product_entities"))
        if terms:
            return terms
        entities = chunk.get("entities") or []
        if entities:
            return self._to_str_list(entities)
        return self._tokenize_keywords(chunk.get("content", ""))

    def _term_similarity(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        return self._jaccard(self._extract_terms(left), self._extract_terms(right))

    def _entity_overlap_score(self, left: Dict[str, Any], right: Dict[str, Any]) -> float:
        left_entities = set(self._to_str_list(left.get("entities")))
        right_entities = set(self._to_str_list(right.get("entities")))
        if not left_entities or not right_entities:
            return 0.0
        return len(left_entities & right_entities) / len(left_entities | right_entities)

    def _knowledge_type(self, chunk: Dict[str, Any]) -> str:
        meta = chunk.get("chunk_metadata") or {}
        value = meta.get("knowledge_type")
        if isinstance(value, list):
            return "、".join(str(item).strip() for item in value if str(item).strip())
        return str(value or "").strip()

    def _text_similarity(self, left: str, right: str) -> float:
        return self._jaccard(self._tokenize_keywords(left), self._tokenize_keywords(right))

    def _tokenize_keywords(self, text: str) -> List[str]:
        if not text:
            return []
        tokens = re.findall(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9_]{2,}", text.lower())
        stop_words = {
            "这个", "那个", "以及", "相关", "进行", "如果", "其中", "我们", "你们",
            "their", "with", "from", "that", "this", "have", "will", "into",
        }
        return [token for token in tokens if token not in stop_words]

    def _jaccard(self, left: List[str], right: List[str]) -> float:
        left_set = set(left)
        right_set = set(right)
        if not left_set or not right_set:
            return 0.0
        return len(left_set & right_set) / len(left_set | right_set)

    def _to_str_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [item for item in re.split(r"[、,，;；\s]+", text) if item]

    def _to_int(self, value: Any) -> int:
        try:
            return int(value)
        except Exception:
            return 0


conversation_chunk_selector = ConversationChunkSelector()


__all__ = [
    "CASE_TYPE_SINGLE_CHUNK_DEEP",
    "CASE_TYPE_SAME_DOC_CHAIN",
    "CASE_TYPE_CROSS_DOC_ASSOC",
    "DEFAULT_CASE_TYPE_RATIO",
    "SUPPORTED_CASE_TYPES",
    "ChunkCluster",
    "ConversationChunkSelector",
    "conversation_chunk_selector",
]
