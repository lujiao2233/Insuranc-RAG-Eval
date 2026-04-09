"""上下文选择器服务
实现原始代码库中的多文档关联问题生成功能，支持深度挖掘、跨产品比较、主题链等策略
"""
import os
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import uuid
from datetime import datetime
import random
import math

from utils.logger import get_logger
from services.document_processor import DocumentProcessor
from services.metadata_extractor import MetadataExtractor
from services.chunking_service import ChunkingService

logger = get_logger("context_selector")


class ContextSelector:
    """上下文选择器类
    
    实现原始代码库中的多文档关联功能，包括：
    1. 深度挖掘策略：基于同一文档的多个切片生成关联问题
    2. 跨产品比较策略：基于不同文档的相似内容生成对比问题
    3. 主题链策略：基于文档间的主题关联生成问题
    """
    
    def __init__(self):
        self.document_processor = DocumentProcessor()
        self.metadata_extractor = MetadataExtractor()
        self.chunking_service = ChunkingService()

    def _get_chunk_text(self, chunk: Dict[str, Any]) -> str:
        return str(chunk.get("chunk") or chunk.get("content") or "")

    def _get_chunk_meta(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        meta = chunk.get("chunk_metadata")
        if isinstance(meta, dict):
            return meta
        meta = chunk.get("metadata")
        if isinstance(meta, dict):
            return meta
        return {}

    def _get_chunk_doc_id(self, chunk: Dict[str, Any], idx: int) -> str:
        doc_id = chunk.get("doc_id") or chunk.get("document_id")
        if doc_id:
            return str(doc_id)
        return f"doc_{idx}"

    def _to_str_list(self, value: Any) -> List[str]:
        if value is None:
            return []
        if isinstance(value, list):
            return [str(v).strip() for v in value if str(v).strip()]
        text = str(value).strip()
        if not text:
            return []
        return [s for s in re.split(r"[、,，;；\s]+", text) if s]

    def _tokenize(self, text: str) -> List[str]:
        if not text:
            return []
        return re.findall(r'[\u4e00-\u9fff]+|[A-Za-z0-9_]+', text.lower())

    def _jaccard(self, a: List[str], b: List[str]) -> float:
        sa = set(a)
        sb = set(b)
        if not sa or not sb:
            return 0.0
        return len(sa & sb) / len(sa | sb)

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        if not a or not b or len(a) != len(b):
            return 0.0
        dot = 0.0
        na = 0.0
        nb = 0.0
        for x, y in zip(a, b):
            dot += x * y
            na += x * x
            nb += y * y
        if na <= 0 or nb <= 0:
            return 0.0
        raw = dot / (math.sqrt(na) * math.sqrt(nb))
        return max(0.0, min(1.0, (raw + 1.0) / 2.0))

    def _knowledge_type_similarity(self, t1: Any, t2: Any) -> float:
        # 支持多标签情况下的相似度计算
        def to_set(val: Any) -> set:
            if isinstance(val, list):
                return {str(v).strip() for v in val if str(v).strip()}
            elif isinstance(val, str):
                return {val.strip()} if val.strip() else set()
            return set()
            
        set_a = to_set(t1)
        set_b = to_set(t2)
        
        if not set_a or not set_b:
            return 0.2
            
        # 如果有直接交集，给高分
        if set_a & set_b:
            return 1.0
            
        related_groups = [
            {"规则约束", "异常除外", "触发条件"},
            {"流程操作", "触发条件"},
            {"概念定义", "事实陈述"},
            {"数据数值", "规则约束"},
        ]
        
        # 只要任意一个标签在同一个 related_group 里，就认为有一定的相似度
        for group in related_groups:
            if (set_a & group) and (set_b & group):
                return 0.6
                
        return 0.2

    def _path_similarity(self, p1: str, p2: str) -> float:
        a = [s.strip() for s in str(p1 or "").split(">") if s.strip()]
        b = [s.strip() for s in str(p2 or "").split(">") if s.strip()]
        if not a or not b:
            return 0.0
        n = min(len(a), len(b))
        common = 0
        for i in range(n):
            if a[i] == b[i]:
                common += 1
            else:
                break
        return common / max(len(a), len(b))

    def _logic_chain_bonus(self, t1: Any, t2: Any) -> float:
        # 支持多标签逻辑链奖励计算
        def to_set(val: Any) -> set:
            if isinstance(val, list):
                return {str(v).strip() for v in val if str(v).strip()}
            elif isinstance(val, str):
                return {val.strip()} if val.strip() else set()
            return set()
            
        set_a = to_set(t1)
        set_b = to_set(t2)
        
        if not set_a or not set_b:
            return 0.0
            
        pairs = {
            ("触发条件", "流程操作"),
            ("规则约束", "流程操作"),
            ("规则约束", "异常除外"),
            ("数据数值", "规则约束"),
            ("概念定义", "规则约束"),
        }
        
        # 检查任意两对标签组合是否在 pairs 中
        for a_label in set_a:
            for b_label in set_b:
                if (a_label, b_label) in pairs or (b_label, a_label) in pairs:
                    return 1.0
                    
        # 只要存在不同的标签就给 0.4
        if set_a != set_b:
            return 0.4
            
        return 0.1

    def _extract_vector(self, chunk: Dict[str, Any]) -> Optional[List[float]]:
        vec = chunk.get("dense_vector")
        if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
            return [float(v) for v in vec]
        meta = self._get_chunk_meta(chunk)
        vec = meta.get("dense_vector")
        if isinstance(vec, list) and vec and isinstance(vec[0], (int, float)):
            return [float(v) for v in vec]
        return None

    def _pair_similarity_score(
        self,
        chunk_a: Dict[str, Any],
        chunk_b: Dict[str, Any],
        relation_type: str
    ) -> Tuple[float, Dict[str, float]]:
        text_a = self._get_chunk_text(chunk_a)
        text_b = self._get_chunk_text(chunk_b)
        meta_a = self._get_chunk_meta(chunk_a)
        meta_b = self._get_chunk_meta(chunk_b)

        vec_a = self._extract_vector(chunk_a)
        vec_b = self._extract_vector(chunk_b)
        if vec_a and vec_b:
            s_sem = self._cosine_similarity(vec_a, vec_b)
        else:
            sem_text_a = f"{text_a} {meta_a.get('section_summary', '')} {' '.join(self._to_str_list(meta_a.get('key_terms')))}"
            sem_text_b = f"{text_b} {meta_b.get('section_summary', '')} {' '.join(self._to_str_list(meta_b.get('key_terms')))}"
            s_sem = self._jaccard(self._tokenize(sem_text_a), self._tokenize(sem_text_b))

        terms_a = self._to_str_list(meta_a.get("key_terms"))
        terms_b = self._to_str_list(meta_b.get("key_terms"))
        if not terms_a:
            terms_a = self._extract_theme_keywords(text_a, top_k=8)
        if not terms_b:
            terms_b = self._extract_theme_keywords(text_b, top_k=8)
        s_terms = self._jaccard(terms_a, terms_b)

        s_type = self._knowledge_type_similarity(meta_a.get("knowledge_type"), meta_b.get("knowledge_type"))
        s_path = self._path_similarity(meta_a.get("breadcrumb_path"), meta_b.get("breadcrumb_path"))

        score = 0.55 * s_sem + 0.20 * s_terms + 0.15 * s_type + 0.10 * s_path

        product_a = str(meta_a.get("product_name") or "").strip()
        product_b = str(meta_b.get("product_name") or "").strip()
        logic_bonus = self._logic_chain_bonus(meta_a.get("knowledge_type"), meta_b.get("knowledge_type"))

        if relation_type == "comparison":
            if product_a and product_b and product_a != product_b:
                score += 0.12
            if s_type >= 0.6:
                score += 0.06
        elif relation_type == "deep_dive":
            if product_a and product_b and product_a == product_b:
                score += 0.08
            if s_type < 1.0:
                score += 0.06
        elif relation_type == "topic_chain":
            score += 0.12 * logic_bonus
            if s_path >= 0.5:
                score += 0.05

        score = max(0.0, min(1.0, score))
        detail = {
            "semantic": round(s_sem, 4),
            "terms": round(s_terms, 4),
            "type": round(s_type, 4),
            "path": round(s_path, 4),
            "final": round(score, 4),
        }
        return score, detail
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算两个文本的相似度"""
        if not text1 or not text2:
            return 0.0
        
        # 简单的Jaccard相似度计算
        set1 = set(text1.lower().split())
        set2 = set(text2.lower().split())
        
        intersection = set1.intersection(set2)
        union = set1.union(set2)
        
        if len(union) == 0:
            return 0.0
        
        return len(intersection) / len(union)
    
    def _find_related_chunks(
        self, 
        target_chunk: Dict[str, Any], 
        all_chunks: List[Dict[str, Any]], 
        threshold: float = 0.3
    ) -> List[Dict[str, Any]]:
        """查找相关的文本块"""
        related_chunks = []
        target_content = target_chunk.get("content", "")
        
        for chunk in all_chunks:
            if chunk.get("id") == target_chunk.get("id"):
                continue  # 跳过自身
            
            chunk_content = chunk.get("content", "")
            similarity = self._calculate_similarity(target_content, chunk_content)
            
            if similarity >= threshold:
                related_chunks.append({
                    **chunk,
                    "similarity": similarity
                })
        
        # 按相似度排序
        related_chunks.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return related_chunks
    
    def _select_context_by_strategy(
        self,
        chunks: List[Dict[str, Any]],
        strategy: str = "deep_dive",
        **kwargs
    ) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """根据策略选择上下文"""
        if strategy == "deep_dive":
            # 深度挖掘策略：选择同一文档的多个相关切片
            return self._select_deep_dive_context(chunks, **kwargs)
        elif strategy == "cross_product":
            # 跨产品比较策略：选择不同文档的相似内容
            return self._select_cross_product_context(chunks, **kwargs)
        elif strategy == "theme_chain":
            # 主题链策略：基于主题关联选择上下文
            return self._select_theme_chain_context(chunks, **kwargs)
        else:
            # 默认使用深度挖掘策略
            return self._select_deep_dive_context(chunks, **kwargs)
    
    def _select_deep_dive_context(
        self,
        chunks: List[Dict[str, Any]],
        max_related: int = 2
    ) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """深度挖掘策略：基于同一文档的多个切片生成关联问题"""
        context_pairs = []
        
        for i, chunk in enumerate(chunks):
            # 查找与当前切片相关的其他切片
            related_chunks = self._find_related_chunks(chunk, chunks)
            selected_related = related_chunks[:max_related]
            
            if selected_related:
                context_pairs.append((chunk, selected_related))
        
        return context_pairs
    
    def _select_cross_product_context(
        self,
        chunks: List[Dict[str, Any]],
        product_categories: Optional[List[str]] = None
    ) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """跨产品比较策略：基于不同文档的相似内容生成对比问题"""
        context_pairs = []
        
        # 按文档分组
        doc_groups = {}
        for chunk in chunks:
            doc_id = chunk.get("document_id", "unknown")
            if doc_id not in doc_groups:
                doc_groups[doc_id] = []
            doc_groups[doc_id].append(chunk)
        
        doc_ids = list(doc_groups.keys())
        
        # 比较不同文档的切片
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                doc1_chunks = doc_groups[doc_ids[i]]
                doc2_chunks = doc_groups[doc_ids[j]]
                
                for chunk1 in doc1_chunks:
                    for chunk2 in doc2_chunks:
                        similarity = self._calculate_similarity(
                            chunk1.get("content", ""), 
                            chunk2.get("content", "")
                        )
                        
                        if similarity > 0.2:  # 设置较低的阈值以获得更多跨产品关联
                            context_pairs.append((
                                chunk1, 
                                [{
                                    **chunk2,
                                    "similarity": similarity,
                                    "document_id": chunk2.get("document_id")
                                }]
                            ))
        
        return context_pairs
    
    def _select_theme_chain_context(
        self,
        chunks: List[Dict[str, Any]],
        theme_keywords: Optional[List[str]] = None
    ) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]]]]:
        """主题链策略：基于文档间的主题关联生成问题"""
        context_pairs = []
        
        if not theme_keywords:
            # 如果没有提供主题关键词，尝试从切片中提取
            all_content = " ".join([chunk.get("content", "") for chunk in chunks])
            theme_keywords = self._extract_theme_keywords(all_content)
        
        for chunk in chunks:
            chunk_content = chunk.get("content", "").lower()
            related_chunks = []
            
            for other_chunk in chunks:
                if other_chunk.get("id") == chunk.get("id"):
                    continue
                
                other_content = other_chunk.get("content", "").lower()
                
                # 检查是否共享相同的主题关键词
                shared_keywords = [kw for kw in theme_keywords if kw.lower() in chunk_content and kw.lower() in other_content]
                
                if shared_keywords:
                    related_chunks.append({
                        **other_chunk,
                        "shared_keywords": shared_keywords
                    })
            
            if related_chunks:
                context_pairs.append((chunk, related_chunks))
        
        return context_pairs
    
    def _extract_theme_keywords(self, text: str, top_k: int = 10) -> List[str]:
        """从文本中提取主题关键词"""
        if not text:
            return []
        
        # 简单的关键词提取：基于词频和长度
        words = re.findall(r'[\u4e00-\u9fff]+|\w+', text.lower())
        
        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        filtered_words = [w for w in words if len(w) > 1 and w not in stop_words]
        
        # 计算词频
        word_freq = {}
        for word in filtered_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # 按频率排序并返回top_k
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_k]]
    
    async def generate_multidoc_questions(
        self,
        documents: List[Dict[str, Any]],
        strategy: str = "deep_dive",
        **kwargs
    ) -> List[Dict[str, Any]]:
        """生成多文档关联问题"""
        all_chunks = []
        
        for doc in documents:
            content = doc.get("content", "")
            doc_id = doc.get("id", str(uuid.uuid4()))
            
            chunks = await self.chunking_service.chunk_document(
                text=content,
                outline=doc.get("outline", []),
                doc_metadata=doc.get("metadata", {})
            )
            
            for chunk in chunks:
                chunk["document_id"] = doc_id
                chunk["filename"] = doc.get("filename", "")
            
            all_chunks.extend(chunks)
        
        context_pairs = self._select_context_by_strategy(all_chunks, strategy, **kwargs)
        
        questions = []
        
        for primary_chunk, related_chunks in context_pairs:
            for related_chunk in related_chunks:
                question_data = self._generate_multidoc_question(
                    primary_chunk, 
                    related_chunk, 
                    strategy
                )
                
                if question_data:
                    questions.append(question_data)
        
        return questions
    
    def select_multi_doc_contexts(self, chunks: List[Dict[str, Any]], num_docs: int = 2) -> Tuple[List[Dict[str, Any]], str]:
        """
        选择多文档上下文用于问题生成
        返回选定的chunks和关系类型
        """
        selection_min_chars = 30
        filtered_chunks = [
            c for c in chunks
            if len(self._get_chunk_text(c).replace("\n", "").strip()) >= selection_min_chars
        ]
        if len(filtered_chunks) >= num_docs:
            chunks = filtered_chunks
        if len(chunks) < num_docs:
            return chunks, "insufficient_docs"

        relation_type = random.choice(["comparison", "deep_dive", "topic_chain"])

        indexed_chunks: List[Tuple[int, Dict[str, Any], str]] = []
        for idx, chunk in enumerate(chunks):
            indexed_chunks.append((idx, chunk, self._get_chunk_doc_id(chunk, idx)))

        doc_ids = {doc_id for _, _, doc_id in indexed_chunks}
        if len(doc_ids) < 2:
            selected = random.sample(chunks, min(num_docs, len(chunks)))
            return selected, relation_type

        pair_scores: List[Tuple[float, Dict[str, float], int, int]] = []
        for i in range(len(indexed_chunks)):
            i_idx, i_chunk, i_doc = indexed_chunks[i]
            for j in range(i + 1, len(indexed_chunks)):
                j_idx, j_chunk, j_doc = indexed_chunks[j]
                if i_doc == j_doc:
                    continue
                score, detail = self._pair_similarity_score(i_chunk, j_chunk, relation_type)
                pair_scores.append((score, detail, i_idx, j_idx))

        if not pair_scores:
            selected = random.sample(chunks, min(num_docs, len(chunks)))
            return selected, relation_type

        pair_scores.sort(key=lambda x: x[0], reverse=True)
        best_score, best_detail, first_idx, second_idx = pair_scores[0]

        selected_indices = [first_idx, second_idx]
        selected_doc_ids = {
            self._get_chunk_doc_id(chunks[first_idx], first_idx),
            self._get_chunk_doc_id(chunks[second_idx], second_idx),
        }
        score_map: Dict[int, Dict[str, float]] = {
            first_idx: best_detail,
            second_idx: best_detail,
        }

        while len(selected_indices) < min(num_docs, len(chunks)):
            best_candidate_idx = None
            best_candidate_score = -1.0
            best_candidate_detail: Dict[str, float] = {}
            for idx, candidate in enumerate(chunks):
                if idx in selected_indices:
                    continue
                candidate_doc_id = self._get_chunk_doc_id(candidate, idx)
                if candidate_doc_id in selected_doc_ids and len(selected_doc_ids) < num_docs:
                    continue
                score_sum = 0.0
                detail_sum = {"semantic": 0.0, "terms": 0.0, "type": 0.0, "path": 0.0, "final": 0.0}
                for selected_idx in selected_indices:
                    pair_score, pair_detail = self._pair_similarity_score(candidate, chunks[selected_idx], relation_type)
                    score_sum += pair_score
                    for k in detail_sum.keys():
                        detail_sum[k] += pair_detail.get(k, 0.0)
                avg_score = score_sum / len(selected_indices)
                if avg_score > best_candidate_score:
                    best_candidate_score = avg_score
                    best_candidate_idx = idx
                    best_candidate_detail = {
                        k: round(v / len(selected_indices), 4) for k, v in detail_sum.items()
                    }
            if best_candidate_idx is None:
                break
            selected_indices.append(best_candidate_idx)
            selected_doc_ids.add(self._get_chunk_doc_id(chunks[best_candidate_idx], best_candidate_idx))
            score_map[best_candidate_idx] = best_candidate_detail

        selected_chunks: List[Dict[str, Any]] = []
        for idx in selected_indices[:num_docs]:
            chunk_copy = dict(chunks[idx])
            sim_info = score_map.get(idx, {})
            if sim_info:
                chunk_copy["similarity"] = sim_info.get("final", 0.0)
                chunk_copy["similarity_breakdown"] = sim_info
            selected_chunks.append(chunk_copy)

        return selected_chunks, relation_type

    def _generate_multidoc_question(
        self,
        primary_chunk: Dict[str, Any],
        related_chunk: Dict[str, Any],
        strategy: str
    ) -> Optional[Dict[str, Any]]:
        """生成多文档关联问题"""
        primary_content = primary_chunk.get("content", "")[:200]  # 截取前200字符
        related_content = related_chunk.get("content", "")[:200]  # 截取前200字符
        
        if strategy == "deep_dive":
            question_template = f"基于以下两段相关内容：\n第一段：{primary_content}\n第二段：{related_content}\n请提出一个需要综合两段内容才能回答的问题。"
            question_type = "多跳综合"
            category_major = "推理与综合类"
        elif strategy == "cross_product":
            question_template = f"比较以下两个不同产品的相关内容：\n产品A：{primary_content}\n产品B：{related_content}\n请提出一个对比这两个产品的问题。"
            question_type = "对比区分"
            category_major = "基础理解类"
        elif strategy == "theme_chain":
            shared_keywords = related_chunk.get("shared_keywords", [])
            keywords_str = "、".join(shared_keywords[:3]) if shared_keywords else "相关信息"
            question_template = f"关于{keywords_str}主题，在以下两段内容中：\n内容1：{primary_content}\n内容2：{related_content}\n请提出一个关联这两段内容的问题。"
            question_type = "跨文档信息整合"
            category_major = "多文档关联类"
        else:
            return None
        
        # 这里应该调用LLM生成问题，但为了简化，我们直接构造一个示例问题
        # 在实际实现中，这里应该调用LLM服务
        question = f"根据提供的两段相关内容，如何综合理解它们之间的关系？"
        expected_answer = f"第一段内容：{primary_content}；第二段内容：{related_content}。综合来看，这两段内容在[共同点]方面相似，在[差异点]方面有所不同。"
        
        return {
            "question": question,
            "question_type": question_type,
            "category_major": category_major,
            "category_minor": question_type,
            "expected_answer": expected_answer,
            "context": f"主要上下文：{primary_content}；关联上下文：{related_content}",
            "metadata": {
                "strategy": strategy,
                "primary_document": primary_chunk.get("filename", ""),
                "related_document": related_chunk.get("filename", ""),
                "similarity": related_chunk.get("similarity", 0),
                "shared_keywords": related_chunk.get("shared_keywords", [])
            }
        }


# 全局实例
context_selector = ContextSelector()
