"""文档切片服务模块
基于文档提纲的智能切片功能，用于将长文档分割为适合RAG系统处理的文本块
"""
from typing import List, Dict, Any, Optional, Tuple
import hashlib
import json
import re
from abc import ABC, abstractmethod
from difflib import SequenceMatcher

from utils.logger import get_logger

logger = get_logger("chunking_service")

DEFAULT_CHUNK_SIZE = 1000


class BaseChunkingStrategy(ABC):
    """切片策略基类"""
    
    def __init__(self, llm=None):
        self.llm = llm

    @abstractmethod
    async def chunk(self, text: str, chunk_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        pass

    def _find_content_position(self, full_text: str, content: str, last_pos: int) -> int:
        """从上次位置开始寻找内容，处理重复文本问题"""
        idx = full_text.find(content, last_pos)
        if idx == -1:
            idx = full_text.find(content.strip(), last_pos)
        return idx

    def _fuzzy_find(self, text: str, pattern: str, start_pos: int = 0, threshold: float = 0.8) -> int:
        """模糊查找模式在文本中的位置，返回最佳匹配的起始位置"""
        pattern = pattern.strip()
        if not pattern:
            return -1
        
        exact_idx = text.find(pattern, start_pos)
        if exact_idx != -1:
            return exact_idx
        
        pattern_len = len(pattern)
        best_idx = -1
        best_ratio = threshold
        
        search_range = min(len(text) - start_pos, 10000)
        for i in range(start_pos, start_pos + search_range - pattern_len):
            candidate = text[i:i + pattern_len]
            ratio = SequenceMatcher(None, pattern, candidate).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_idx = i
        
        return best_idx


class GeneralChunkingStrategy(BaseChunkingStrategy):
    """通用语义切片策略"""
    
    async def chunk(self, text: str, chunk_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not text:
            return []
        chunks = self._semantic_split_with_llamaindex(text, chunk_size, section_meta)
        if chunks:
            return chunks
        return self._fallback_semantic_split(text, chunk_size)

    def _semantic_split_with_llamaindex(self, text: str, target_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        """使用 LlamaIndex Node Parsers 执行语义切分（不依赖业务 LLM 调用）。"""
        try:
            from llama_index.core import Document
            from llama_index.core.node_parser import SentenceSplitter
        except Exception as import_error:
            logger.warning(f"LlamaIndex 未安装或导入失败，回退本地规则切分: {import_error}")
            return []

        try:
            safe_size = max(100, int(target_size or DEFAULT_CHUNK_SIZE))
            splitter = SentenceSplitter(
                chunk_size=safe_size,
                chunk_overlap=max(20, min(80, safe_size // 8)),
                paragraph_separator="\n\n",
            )
            nodes = splitter.get_nodes_from_documents([
                Document(text=text, metadata={"section_title": section_meta.get("title", "")})
            ])

            chunks = []
            for node in nodes:
                node_text = ""
                if hasattr(node, "get_content"):
                    node_text = str(node.get_content() or "").strip()
                elif hasattr(node, "text"):
                    node_text = str(node.text or "").strip()
                if node_text:
                    chunks.append({"text": node_text})
            return chunks
        except Exception as e:
            logger.error(f"LlamaIndex Node Parser 语义切分失败: {e}")
            return []

    def _fallback_semantic_split(self, text, target_size):
        """稳健的语义切分逻辑（无重叠）"""
        if not text:
            return []
        
        sentence_delimiters = r'([。！？\n])'
        raw_parts = re.split(sentence_delimiters, text)
        sentences = []
        for i in range(0, len(raw_parts) - 1, 2):
            sentences.append(raw_parts[i] + raw_parts[i + 1])
        if len(raw_parts) % 2 == 1:
            sentences.append(raw_parts[-1])
            
        sub_chunks = []
        current_chunk = ""
        
        for s in sentences:
            if len(s) > target_size:
                if current_chunk:
                    sub_chunks.append({"text": current_chunk.strip()})
                    current_chunk = ""
                sub_parts = re.split(r'([，, \s])', s)
                temp_s = ""
                for part in sub_parts:
                    if len(temp_s) + len(part) > target_size and temp_s:
                        sub_chunks.append({"text": temp_s.strip()})
                        temp_s = part
                    else:
                        temp_s += part
                if temp_s:
                    current_chunk = temp_s
                continue

            if len(current_chunk) + len(s) > target_size and current_chunk:
                sub_chunks.append({"text": current_chunk.strip()})
                current_chunk = s
            else:
                current_chunk += s
                
        if current_chunk:
            sub_chunks.append({"text": current_chunk.strip()})
        return sub_chunks


class InsuranceClauseStrategy(GeneralChunkingStrategy):
    """保险条款切片策略：强化正则锚点识别"""
    
    async def chunk(self, text: str, chunk_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        anchor_patterns = [
            r'^第[一二三四五六七八九十百]+[条章节]\s+',
            r'^\d+\.\d+(\.\d+)?\s+',
            r'^[（\(][一二三四五六七八九十]+[）\)]\s+'
        ]
        
        lines = text.split('\n')
        anchors = []
        for i, line in enumerate(lines):
            stripped_line = line.strip()
            for pattern in anchor_patterns:
                if re.match(pattern, stripped_line):
                    anchors.append({"line_idx": i, "text": stripped_line})
                    break
        
        if not anchors:
            return await super().chunk(text, chunk_size, section_meta)
            
        segments = []
        current_segment = []
        for i, line in enumerate(lines):
            is_anchor = any(a["line_idx"] == i for a in anchors)
            if is_anchor and current_segment:
                segments.append("\n".join(current_segment))
                current_segment = [line]
            else:
                current_segment.append(line)
        if current_segment:
            segments.append("\n".join(current_segment))
            
        final_chunks = []
        for seg in segments:
            if len(seg) > chunk_size * 1.2:
                final_chunks.extend(await super().chunk(seg, chunk_size, section_meta))
            else:
                final_chunks.append({"text": seg.strip()})
        return final_chunks


class TableDataStrategy(GeneralChunkingStrategy):
    """表格切片策略：将表格记录转换为结构化 JSON，每行作为一个独立切片"""
    
    async def chunk(self, text: str, chunk_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        if '[[' in text and ']]' in text:
            return self._chunk_list_to_json(text)
            
        table_markers = [r'\[TABLE \d+\]', r'^表格\d+:', r'\|']
        is_table = any(re.search(m, text, re.MULTILINE) for m in table_markers)
        
        if not is_table:
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            multi_column_lines = 0
            numeric_lines = 0
            
            for l in lines[:10]:
                parts = [c.strip() for c in re.split(r'\s{2,}|\t', l) if c.strip()]
                if len(parts) >= 3:
                    multi_column_lines += 1
                if re.search(r'\d+', l):
                    numeric_lines += 1
            
            if multi_column_lines >= 2 and numeric_lines >= 2:
                is_table = True
        
        if is_table:
            table_result = self._chunk_markdown_to_json(text)
            if table_result is not None:
                return table_result
            
        kt_meta = section_meta.get("knowledge_type")
        is_numeric = False
        if isinstance(kt_meta, list):
            is_numeric = "数据数值" in kt_meta
        else:
            is_numeric = kt_meta == "数据数值"

        if is_numeric or section_meta.get("doc_type") in ["费率表", "现金价值表"]:
            if self.llm and len(text) < 4000:
                logger.info("正则解析表格失败，尝试使用 LLM 结构化提取")
                return await self._chunk_table_with_llm(text)
            
        return await super().chunk(text, chunk_size, section_meta)

    async def _chunk_table_with_llm(self, text: str) -> List[Dict[str, Any]]:
        """使用 LLM 将杂乱的文本还原为 JSON 表格"""
        prompt = f"""
你是一个数据清洗专家。请将下面这段杂乱的文本还原为结构化的 JSON 数组格式。
这段文本原本是一个表格，包含多个列（如年龄、保费、性别、保险期间等）。

**特别注意多级表头 (Merged Cells)**:
1. 如果表格前两行存在合并单元格（如第一行是"交费期间1年"，第二行是"男性"、"女性"），请务必将它们合并为唯一的键，例如："交费期间1年_男性"、"交费期间1年_女性"。
2. 确保每一行数据都映射到这些完整的复合键上。
3. 识别并跳过表格上方的标题、单位（如"单位：元"）等非数据行。

要求：
1. 识别并对齐每一行的数据。
2. 识别表头。如果表头不清晰，请根据内容推断（如：年龄, 保费, 性别, 保险期间）。
3. 只返回 JSON 数组，每个元素是一个键值对对象。
4. 如果文本确实不是表格，请返回空数组 []。

待处理文本：
{text}
"""
        try:
            response = await self.llm.generate_text(
                prompt,
                max_tokens=2000,
                temperature=0.1,
                module_name="document_analysis"
            )
            text_response = str(response).strip()
            if "```json" in text_response:
                text_response = text_response.split("```json")[1].split("```")[0]
            elif "```" in text_response:
                text_response = text_response.split("```")[1].split("```")[0]
            
            records = json.loads(text_response)
            if isinstance(records, list) and records:
                return self._records_to_row_chunks(records)
        except Exception as e:
            logger.error(f"LLM 表格结构化失败: {e}")
        
        return self._fallback_semantic_split(text, DEFAULT_CHUNK_SIZE)

    def _merge_multi_level_headers(self, raw_headers: List[List[str]]) -> List[str]:
        """合并多级表头（例如前两行混合的情况）"""
        if not raw_headers:
            return []
        if len(raw_headers) == 1:
            return [h.strip() for h in raw_headers[0] if h and h.strip()]
            
        final_headers = []
        h1 = list(raw_headers[0])
        h2 = list(raw_headers[1]) if len(raw_headers) > 1 else []
        
        max_len = max(len(h1), len(h2))
        h1 += [""] * (max_len - len(h1))
        h2 += [""] * (max_len - len(h2))
        
        last_h1 = ""
        for i in range(max_len):
            curr_h1 = (h1[i].strip() if h1[i] else "") or last_h1
            curr_h2 = h2[i].strip() if h2[i] else ""
            
            if curr_h1 and curr_h2:
                if curr_h1 == curr_h2:
                    final_headers.append(curr_h1)
                else:
                    final_headers.append(f"{curr_h1}_{curr_h2}")
            elif curr_h1:
                final_headers.append(curr_h1)
            elif curr_h2:
                final_headers.append(curr_h2)
            else:
                final_headers.append(f"Column_{i}")
            
            if h1[i] and h1[i].strip():
                last_h1 = h1[i].strip()
            
        return final_headers

    def _chunk_markdown_to_json(self, text: str) -> Optional[List[Dict[str, Any]]]:
        """将 Markdown/空格分隔表格转换为结构化 JSON 记录流，每行一个切片"""
        lines = [l.strip() for l in text.split('\n') if l.strip() and not re.match(r'^[\s\|:\-]+$', l)]
        if len(lines) < 2:
            return [{"text": text}]

        def split_line(l):
            if '|' in l:
                parts = [c.strip() for c in l.split('|')]
                return [p for p in parts if p]
            parts = [c.strip() for c in re.split(r'\s{2,}|\t', l) if c.strip()]
            if len(parts) >= 2:
                return parts
            single_space_parts = [c.strip() for c in l.split(' ') if c.strip()]
            if len(single_space_parts) >= 3:
                return single_space_parts
            return [l.strip()]

        header_start_idx = 0
        header_col_count = 0
        
        for i in range(min(10, len(lines))):
            cols = split_line(lines[i])
            if len(cols) >= 2:
                has_numeric = any(re.search(r'\d+', c) for c in cols)
                next_lines_match = True
                for j in range(i + 1, min(i + 3, len(lines))):
                    next_cols = split_line(lines[j])
                    if len(next_cols) < 2 or abs(len(next_cols) - len(cols)) > 1:
                        next_lines_match = False
                        break
                
                if has_numeric or next_lines_match:
                    header_start_idx = i
                    header_col_count = len(cols)
                    break
        
        if header_col_count < 2:
            return None
        
        relevant_lines = lines[header_start_idx:]
        if len(relevant_lines) < 2:
            return [{"text": text}]

        raw_header_rows = [split_line(l) for l in relevant_lines[:2]]
        
        if len(raw_header_rows) >= 2:
            first_row_has_numeric = any(re.search(r'\d+', c) for c in raw_header_rows[0])
            second_row_has_numeric = any(re.search(r'\d+', c) for c in raw_header_rows[1])
            
            if first_row_has_numeric and not second_row_has_numeric:
                raw_header_rows = [raw_header_rows[1], raw_header_rows[0]]
            elif first_row_has_numeric and second_row_has_numeric:
                raw_header_rows = [raw_header_rows[0]]
        
        headers = self._merge_multi_level_headers(raw_header_rows)
        
        if len(headers) < 2:
            logger.warning(f"表格表头识别失败，仅检测到 {len(headers)} 列")
            return None
        
        data_start = 2 if len(raw_header_rows) >= 2 and not any(re.search(r'\d+', c) for c in raw_header_rows[1]) else 1
        data_lines = relevant_lines[data_start:]
        
        records = []
        for line in data_lines:
            values = split_line(line)
            if len(values) < 2:
                continue
            values += [""] * (len(headers) - len(values))
            record = dict(zip(headers, values[:len(headers)]))
            if any(v for v in record.values() if v and v.strip()):
                records.append(record)
            
        if not records:
            return None
            
        if len(headers) <= 1:
            logger.warning(f"表格分列异常，仅检测到单列: {headers}")
            return None
            
        return self._records_to_row_chunks(records)

    def _chunk_list_to_json(self, text: str) -> List[Dict[str, Any]]:
        """将 Excel 列表格式转换为结构化 JSON 记录流，每行一个切片"""
        row_pattern = r'(\[[^\[\]]+?\])'
        rows_str = re.findall(row_pattern, text)
        if len(rows_str) < 2:
            return [{"text": text}]
        
        try:
            h1 = json.loads(rows_str[0].replace("'", '"'))
            h2 = json.loads(rows_str[1].replace("'", '"')) if len(rows_str) > 1 else []
            
            first_row_has_numeric = any(isinstance(c, (int, float)) or (isinstance(c, str) and re.search(r'\d+', c)) for c in h1)
            second_row_has_numeric = any(isinstance(c, (int, float)) or (isinstance(c, str) and re.search(r'\d+', c)) for c in h2) if h2 else False
            
            if first_row_has_numeric and not second_row_has_numeric and h2:
                h1, h2 = h2, h1
            elif first_row_has_numeric and second_row_has_numeric:
                h2 = []
            
            headers = self._merge_multi_level_headers([h1, h2] if h2 else [h1])
            
            data_start = 2 if h2 and not second_row_has_numeric else 1
            data_rows = rows_str[data_start:]
            
            records = []
            for r_str in data_rows:
                values = json.loads(r_str.replace("'", '"'))
                values += [""] * (len(headers) - len(values))
                record = dict(zip(headers, values[:len(headers)]))
                if any(v for v in record.values() if v is not None and str(v).strip()):
                    records.append(record)
                
            return self._records_to_row_chunks(records)
        except Exception as e:
            logger.error(f"JSON 表格解析失败: {e}")
            return [{"text": text}]

    def _records_to_row_chunks(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """将每条记录转换为独立的切片（每行一个切片）"""
        chunks = []
        for rec in records:
            if rec and any(v for v in rec.values() if v is not None and str(v).strip()):
                chunks.append({"text": json.dumps(rec, ensure_ascii=False)})
        return chunks if chunks else [{"text": ""}]


class AnnouncementStrategy(GeneralChunkingStrategy):
    """公告切片策略：强调语义支点和段落完整性"""
    
    async def chunk(self, text: str, chunk_size: int, section_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        paragraphs = text.split('\n\n')
        if not paragraphs:
            return await super().chunk(text, chunk_size, section_meta)
            
        if len(text) < chunk_size * 1.5:
            return [{"text": text}]
            
        return await super().chunk(text, chunk_size, section_meta)


class ChunkingService:
    """文档切片服务类"""
    
    def __init__(self, llm=None):
        self._llm = llm
        self.strategies = {
            "保险条款": InsuranceClauseStrategy(llm),
            "费率表": TableDataStrategy(llm),
            "现金价值表": TableDataStrategy(llm),
            "管理制度": InsuranceClauseStrategy(llm),
            "宣传彩页": AnnouncementStrategy(llm),
            "公文公告": AnnouncementStrategy(llm),
            "其他": AnnouncementStrategy(llm),
            "default": GeneralChunkingStrategy(llm)
        }
        self._sentence_end_pattern = re.compile(r'[。！？!?…\.]+[”"’\'）)\]】]*$')
        self._short_chunk_merge_threshold = 60
        self._max_chunk_chars = 500
        self._title_like_pattern = re.compile(
            r'^\s*((第[一二三四五六七八九十百千万0-9]+[章节条款项])|([一二三四五六七八九十]+[、.]))|(\d+[、.)）])'
        )
        self._table_doc_types = {"费率表", "现金价值表"}
        self._valid_knowledge_types = ["概念定义", "规则约束", "流程操作", "数据数值", "触发条件", "事实陈述", "异常除外"]

    @property
    def llm(self):
        return self._llm

    @llm.setter
    def llm(self, value):
        self._llm = value
        for strategy in self.strategies.values():
            strategy.llm = value

    async def chunk_document(
        self, 
        text: str, 
        outline: List[Dict[str, Any]], 
        doc_metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not text:
            return []
        
        doc_type = doc_metadata.get("doc_type", "default")
        short_threshold, max_chars = self._resolve_chunking_thresholds(doc_metadata)
        strategy = self.strategies.get(doc_type, self.strategies["default"])
        logger.info(f"使用切片策略: {strategy.__class__.__name__} (文档类型: {doc_type})")

        flat_outline = self._flatten_outline(outline)
        chunks = []
        sequence_number = 0
        
        nodes_with_pos = []
        search_start = 0
        for node in flat_outline:
            title = node.get("anchor_text") or node.get("title", "").strip()
            if not title:
                continue
            
            idx = text.find(title, search_start)
            if idx != -1:
                nodes_with_pos.append({"start": idx, "node": node})
                search_start = idx + len(title)
            else:
                alt_title = node.get("title", "").strip()
                if alt_title and alt_title != title:
                    idx = text.find(alt_title, search_start)
                    if idx != -1:
                        nodes_with_pos.append({"start": idx, "node": node})
                        search_start = idx + len(alt_title)
        
        if not nodes_with_pos:
            return await self._generate_base_chunks(text, doc_metadata, strategy)

        import asyncio
        tasks = []
        segments_info = []
        
        for i in range(len(nodes_with_pos)):
            curr_node = nodes_with_pos[i]
            next_node_start = nodes_with_pos[i + 1]["start"] if i < len(nodes_with_pos) - 1 else len(text)
            
            segment_text = text[curr_node["start"]:next_node_start].strip()
            if not segment_text:
                continue
            
            segments_info.append({
                "start_pos": curr_node["start"],
                "node": curr_node["node"]
            })
            
            meta_to_pass = {**curr_node["node"], "doc_type": doc_type}
            tasks.append(strategy.chunk(segment_text, DEFAULT_CHUNK_SIZE, meta_to_pass))
            
        if not tasks:
            return chunks

        all_sub_chunks = await asyncio.gather(*tasks)
        
        for i, sub_chunks in enumerate(all_sub_chunks):
            sub_chunks = self._post_process_sub_chunks(sub_chunks, short_threshold, max_chars)
            seg_info = segments_info[i]
            current_search_pos = seg_info["start_pos"]
            
            for sc in sub_chunks:
                sc_text = sc["text"]
                if not sc_text:
                    continue
                    
                sc_idx = text.find(sc_text, current_search_pos)
                
                if sc_idx != -1:
                    sc_start = sc_idx
                    current_search_pos = sc_idx + len(sc_text)
                else:
                    sc_start = current_search_pos
                    current_search_pos += len(sc_text)
                
                chunks.append(await self._create_chunk_dict(
                    sc_text, sequence_number, sc_start, sc_start + len(sc_text), doc_metadata, seg_info["node"]
                ))
                sequence_number += 1

        if self._should_enforce_text_merge(doc_metadata):
            chunks = self._merge_chunk_dicts_document_level(chunks, short_threshold)
            chunks = self._split_chunk_dicts_by_max_chars(chunks, max_chars, short_threshold)
        chunks = self._reindex_chunk_dicts(chunks, text)
        await self._batch_infer_knowledge_types(chunks)
        return chunks

    def _flatten_outline(self, outline: List[Dict[str, Any]], level: int = 1) -> List[Dict[str, Any]]:
        flat = []
        for node in outline:
            node_copy = node.copy()
            node_copy["level"] = level
            flat.append(node_copy)
            if node.get("children"):
                flat.extend(self._flatten_outline(node["children"], level + 1))
        return flat

    async def _create_chunk_dict(self, text, seq, start, end, doc_meta, section_meta):
        md5_input = f"{text}_{start}"
        md5 = hashlib.md5(md5_input.encode('utf-8')).hexdigest()
        safe_doc_meta = {
            k: v for k, v in (doc_meta or {}).items()
            if not str(k).startswith("_chunking_")
        }
        knowledge_type_raw = section_meta.get("knowledge_type")
        knowledge_type = self._normalize_knowledge_type_value(knowledge_type_raw) or ["事实陈述"]
        
        return {
            "content": text,
            "md5": md5,
            "sequence_number": seq,
            "start_char": start,
            "end_char": end,
            "metadata": {
                **safe_doc_meta,
                "section_id": section_meta.get("id"),
                "section_title": section_meta.get("title"),
                "section_level": section_meta.get("level"),
                "breadcrumb_path": section_meta.get("breadcrumb_path", ""),
                "knowledge_type": knowledge_type,
                "knowledge_type_raw": knowledge_type_raw,
                "key_terms": section_meta.get("key_terms"),
                "section_summary": section_meta.get("summary", ""),
                "has_context_mounted": False
            }
        }

    def _normalize_knowledge_type_value(self, value: Any) -> List[str]:
        if isinstance(value, str):
            return [value] if value in self._valid_knowledge_types else []
        if isinstance(value, list):
            filtered = [v for v in value if v in self._valid_knowledge_types]
            return filtered if filtered else []
        return []

    async def _batch_infer_knowledge_types(self, chunks: List[Dict[str, Any]], batch_size: int = 20):
        """批量调用 LLM 进行知识类型判断，避免逐片段调用造成 token 激增。"""
        if not chunks or not self.llm:
            return

        fallback = ["事实陈述"]
        candidates = []
        for idx, chunk in enumerate(chunks):
            content = str(chunk.get("content") or "").strip()
            if not content:
                chunk.setdefault("metadata", {})["knowledge_type"] = fallback
                continue

            metadata = chunk.setdefault("metadata", {})
            normalized_existing = self._normalize_knowledge_type_value(metadata.get("knowledge_type"))
            metadata["knowledge_type"] = normalized_existing or fallback

            candidates.append({
                "index": idx,
                "section_title": metadata.get("section_title", ""),
                "breadcrumb_path": metadata.get("breadcrumb_path", ""),
                "text": content[:1000]
            })

        if not candidates:
            return

        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            prompt = f"""
你是一个专业的保险与制度文档知识分类专家。
请基于每条文本及其上下文，给出知识类型（可多选）。

可选知识类型：
{json.dumps(self._valid_knowledge_types, ensure_ascii=False)}

输入数据：
{json.dumps(batch, ensure_ascii=False)}

输出要求：
1. 只输出 JSON。
2. 输出格式必须为：
{{
  "results": [
    {{"index": 0, "knowledge_type": ["事实陈述"]}}
  ]
}}
3. 每个 index 都必须返回；若不确定则返回 ["事实陈述"]。
"""
            try:
                response = await self.llm.generate_text(
                    prompt,
                    max_tokens=min(4000, 300 + len(batch) * 120),
                    temperature=0.1,
                    module_name="document_analysis"
                )
                text_response = str(response).strip()
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0]
                elif "```" in text_response:
                    text_response = text_response.split("```")[1].split("```")[0]

                parsed = json.loads(text_response)
                results = parsed.get("results", []) if isinstance(parsed, dict) else []
                by_index = {}
                for item in results:
                    if not isinstance(item, dict):
                        continue
                    idx = item.get("index")
                    types = self._normalize_knowledge_type_value(item.get("knowledge_type"))
                    if isinstance(idx, int):
                        by_index[idx] = types or fallback

                for item in batch:
                    chunk_idx = item["index"]
                    chunks[chunk_idx].setdefault("metadata", {})["knowledge_type"] = by_index.get(chunk_idx, fallback)
            except Exception as e:
                logger.error(f"LLM 批量知识类型分类失败: {e}")
                for item in batch:
                    chunk_idx = item["index"]
                    chunks[chunk_idx].setdefault("metadata", {})["knowledge_type"] = fallback

    def _is_complete_sentence_end(self, text: str) -> bool:
        t = str(text or "").strip()
        if not t:
            return True
        # 表格/JSON行切片不强制按句号结尾，避免无意义合并
        if (t.startswith("{") and t.endswith("}")) or (t.startswith("[") and t.endswith("]")):
            return True
        return bool(self._sentence_end_pattern.search(t))

    def _resolve_chunking_thresholds(self, doc_meta: Dict[str, Any]) -> Tuple[int, int]:
        short_threshold = self._short_chunk_merge_threshold
        max_chars = self._max_chunk_chars
        try:
            v = int((doc_meta or {}).get("_chunking_short_merge_threshold", short_threshold))
            short_threshold = max(20, v)
        except Exception:
            pass
        try:
            v = int((doc_meta or {}).get("_chunking_max_chunk_chars", max_chars))
            max_chars = max(100, v)
        except Exception:
            pass
        return short_threshold, max_chars

    def _merge_incomplete_sentence_chunks(self, sub_chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not sub_chunks:
            return sub_chunks
        merged: List[Dict[str, Any]] = []
        current_text = str(sub_chunks[0].get("text") or "")
        for i in range(1, len(sub_chunks)):
            next_text = str(sub_chunks[i].get("text") or "")
            if self._is_complete_sentence_end(current_text):
                merged.append({"text": current_text.strip()})
                current_text = next_text
            else:
                # 当前片段若未以句末符号结束，则与后续片段合并，避免行尾截断半句
                current_text = (current_text + next_text).strip()
        if current_text:
            merged.append({"text": current_text.strip()})
        return merged

    def _is_title_like_fragment(self, text: str) -> bool:
        t = str(text or "").strip()
        if not t:
            return False
        if t.endswith(("：", ":", "；", ";")):
            return True
        if len(t) <= 24 and self._title_like_pattern.search(t):
            return True
        return False

    def _merge_short_chunks(self, sub_chunks: List[Dict[str, Any]], short_threshold: int) -> List[Dict[str, Any]]:
        if not sub_chunks:
            return sub_chunks
        chunks = [{"text": str(c.get("text") or "").strip()} for c in sub_chunks if str(c.get("text") or "").strip()]
        if not chunks:
            return []
        merged: List[Dict[str, Any]] = []
        i = 0
        while i < len(chunks):
            current = chunks[i]["text"]
            current_len = len(current.replace("\n", "").strip())
            force_merge = self._is_title_like_fragment(current)
            if (force_merge or current_len < short_threshold) and i + 1 < len(chunks):
                current = (current + chunks[i + 1]["text"]).strip()
                i += 1
            elif (force_merge or current_len < short_threshold) and merged:
                prev = merged.pop()["text"]
                current = (prev + current).strip()
            merged.append({"text": current})
            i += 1
        return merged

    def _post_process_sub_chunks(self, sub_chunks: List[Dict[str, Any]], short_threshold: int, max_chars: int) -> List[Dict[str, Any]]:
        merged = self._merge_incomplete_sentence_chunks(sub_chunks)
        merged = self._merge_short_chunks(merged, short_threshold)
        merged = self._split_sub_chunks_by_max_chars(merged, max_chars, short_threshold)
        return merged

    def _find_earliest_paragraph_cut(self, window: str, min_piece: int) -> Optional[int]:
        for m in re.finditer(r'\n\s*\n|\n', window):
            boundary_start = m.start()
            prefix = window[:boundary_start].rstrip()
            if len(prefix) < min_piece:
                continue
            if prefix.endswith(("。", "！", "？", "!", "?", "；", ";")):
                return len(prefix)
        return None

    def _find_earliest_sentence_cut(self, window: str, min_piece: int) -> Optional[int]:
        for i, ch in enumerate(window):
            if i + 1 < min_piece:
                continue
            if ch in ("。", "！", "？", "!", "?", "；", ";"):
                return i + 1
        return None

    def _find_earliest_comma_cut(self, window: str, min_piece: int) -> Optional[int]:
        for i, ch in enumerate(window):
            if i + 1 < min_piece:
                continue
            if ch in ("，", ","):
                return i + 1
        return None

    def _split_overlong_text(self, text: str, max_chars: int, min_piece: int) -> List[str]:
        remain = str(text or "")
        if len(remain) <= max_chars:
            return [remain]
        parts: List[str] = []
        while len(remain) > max_chars:
            window = remain[:max_chars]
            cut = self._find_earliest_paragraph_cut(window, min_piece)
            if cut is None:
                cut = self._find_earliest_sentence_cut(window, min_piece)
            if cut is None:
                cut = self._find_earliest_comma_cut(window, min_piece)
            if cut is None or cut <= 0:
                cut = max_chars
            part = remain[:cut].rstrip()
            if not part:
                part = remain[:max_chars]
                cut = max_chars
            parts.append(part)
            remain = remain[cut:].lstrip()
        if remain:
            parts.append(remain)
        return parts

    def _split_sub_chunks_by_max_chars(self, sub_chunks: List[Dict[str, Any]], max_chars: int, short_threshold: int) -> List[Dict[str, Any]]:
        if not sub_chunks:
            return sub_chunks
        result: List[Dict[str, Any]] = []
        min_piece = max(20, min(80, short_threshold // 2))
        for c in sub_chunks:
            t = str(c.get("text") or "")
            if len(t) <= max_chars:
                result.append({"text": t})
                continue
            parts = self._split_overlong_text(t, max_chars, min_piece)
            for p in parts:
                if p:
                    result.append({"text": p})
        return result

    def _should_enforce_text_merge(self, doc_meta: Dict[str, Any]) -> bool:
        doc_type = str((doc_meta or {}).get("doc_type") or "").strip()
        return doc_type not in self._table_doc_types

    def _merge_chunk_dicts_document_level(self, chunks: List[Dict[str, Any]], short_threshold: int) -> List[Dict[str, Any]]:
        if not chunks:
            return chunks
        merged: List[Dict[str, Any]] = []
        current = dict(chunks[0])
        for i in range(1, len(chunks)):
            nxt = chunks[i]
            current_text = str(current.get("content") or "")
            current_len = len(current_text.replace("\n", "").strip())
            force_merge = self._is_title_like_fragment(current_text)
            need_merge = force_merge or (current_len < short_threshold) or (not self._is_complete_sentence_end(current_text))
            if need_merge:
                joined = (current_text + str(nxt.get("content") or "")).strip()
                current["content"] = joined
                current["end_char"] = nxt.get("end_char", current.get("end_char"))
            else:
                merged.append(current)
                current = dict(nxt)
        merged.append(current)

        # 重新编号与MD5，保证数据一致
        for idx, c in enumerate(merged):
            c["sequence_number"] = idx
            start = c.get("start_char", 0)
            content = str(c.get("content") or "")
            md5_input = f"{content}_{start}"
            c["md5"] = hashlib.md5(md5_input.encode("utf-8")).hexdigest()
        return merged

    def _split_chunk_dicts_by_max_chars(self, chunks: List[Dict[str, Any]], max_chars: int, short_threshold: int) -> List[Dict[str, Any]]:
        if not chunks:
            return chunks
        result: List[Dict[str, Any]] = []
        min_piece = max(20, min(80, short_threshold // 2))
        for c in chunks:
            content = str(c.get("content") or "")
            if len(content) <= max_chars:
                result.append(dict(c))
                continue
            parts = self._split_overlong_text(content, max_chars, min_piece)
            for p in parts:
                nc = dict(c)
                nc["content"] = p
                result.append(nc)
        return result

    def _reindex_chunk_dicts(self, chunks: List[Dict[str, Any]], full_text: str) -> List[Dict[str, Any]]:
        if not chunks:
            return chunks
        current_search_pos = 0
        for idx, c in enumerate(chunks):
            content = str(c.get("content") or "")
            if not content:
                continue
            sc_idx = full_text.find(content, current_search_pos)
            if sc_idx != -1:
                sc_start = sc_idx
                current_search_pos = sc_idx + len(content)
            else:
                sc_start = current_search_pos
                current_search_pos += len(content)
            c["sequence_number"] = idx
            c["start_char"] = sc_start
            c["end_char"] = sc_start + len(content)
            md5_input = f"{content}_{sc_start}"
            c["md5"] = hashlib.md5(md5_input.encode("utf-8")).hexdigest()
        return chunks

    async def _generate_base_chunks(self, text, meta, strategy=None):
        """无提纲时的基础切片逻辑"""
        if strategy is None:
            strategy = self.strategies["default"]
            
        sub_chunks = await strategy.chunk(text, DEFAULT_CHUNK_SIZE, {})
        short_threshold, max_chars = self._resolve_chunking_thresholds(meta)
        sub_chunks = self._post_process_sub_chunks(sub_chunks, short_threshold, max_chars)
        chunks = []
        current_search_pos = 0
        for i, sc in enumerate(sub_chunks):
            sc_text = sc["text"]
            if not sc_text:
                continue
            sc_idx = text.find(sc_text, current_search_pos)
            if sc_idx != -1:
                sc_start = sc_idx
                current_search_pos = sc_idx + len(sc_text)
            else:
                sc_start = current_search_pos
                current_search_pos += len(sc_text)
                
            chunks.append(await self._create_chunk_dict(sc_text, i, sc_start, sc_start + len(sc_text), meta, {}))
        if self._should_enforce_text_merge(meta):
            chunks = self._merge_chunk_dicts_document_level(chunks, short_threshold)
            chunks = self._split_chunk_dicts_by_max_chars(chunks, max_chars, short_threshold)
        chunks = self._reindex_chunk_dicts(chunks, text)
        await self._batch_infer_knowledge_types(chunks)
        return chunks

    def chunk_by_semantic(self, text: str, min_chunk_size: int = 200, max_chunk_size: int = 1000, metadata: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    self._generate_base_chunks(text, metadata or {})
                )
                return future.result()
        else:
            return asyncio.run(self._generate_base_chunks(text, metadata or {}))
