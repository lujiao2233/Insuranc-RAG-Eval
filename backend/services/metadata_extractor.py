"""元数据提取器模块
使用LLM智能提取文档元数据和生成文档提纲
"""
import os
import json
import re
from typing import Dict, Any, Optional

from utils.logger import get_logger

logger = get_logger("metadata_extractor")


class MetadataExtractor:
    """元数据提取器类
    
    使用大语言模型（LLM）智能提取文档的元数据信息和结构化提纲。
    支持动态设计元数据字段，适应不同类型的文档。
    """
    
    def __init__(self, llm=None):
        self.llm = llm

    def _build_llm(self):
        """构建LLM实例 (已弃用，优先通过 extract 传入 llm)"""
        from services.llm_service import get_llm_service
        return get_llm_service()

    async def extract(self, text: str, llm=None) -> Dict[str, Any]:
        """提取文档元数据和提纲
        
        使用LLM分析文档内容，提取元数据并生成结构化提纲。
        对于长文档，采用首尾截断策略保留关键信息。
        
        Args:
            text: 文档文本内容
            llm: 可选的LLM实例，如果不提供则使用默认实例
            
        Returns:
            元数据字典，包含doc_type、product_name、outline等字段
        """
        target_llm = llm or self.llm
        if not target_llm:
            logger.warning("LLM未初始化，跳过元数据提取")
            return {}

        # 直接使用全文，不再进行截断，以确保提纲覆盖所有章节
        prompt = self._get_extraction_prompt(text)
        
        try:
            # 统一使用异步调用，增加 max_tokens 以处理全文提纲
            if hasattr(target_llm, 'generate_text'):
                response = await target_llm.generate_text(
                    prompt,
                    max_tokens=16000,
                    module_name="metadata_extraction"
                )
            elif hasattr(target_llm, 'ainvoke'):
                response = await target_llm.ainvoke(prompt)
            elif hasattr(target_llm, 'invoke'):
                # 如果只有同步 invoke，则回退（虽然 QwenService 现在是异步的）
                response = target_llm.invoke(prompt)
            else:
                logger.error("LLM实例不支持已知的调用方法")
                return {}
            
            result = self._parse_json_response(str(response))
            result = self._ensure_issue_date(text, result)
            if not result or "outline" not in result:
                logger.error(f"LLM响应解析成功但缺少必要字段: {result}")
            return result
        except Exception as e:
            logger.error(f"元数据提取失败: {str(e)}")
            return {}

    def _parse_json_response(self, response: str) -> Dict[str, Any]:
        """解析LLM返回的JSON响应
        
        处理各种JSON格式响应，包括标准JSON、代码块包裹的JSON等。
        增加了对截断 JSON 的深度修复尝试（处理未闭合字符串和嵌套结构）。
        """
        text = response.strip()
        
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
        
        text = text.strip()
        
        try:
            return self._do_parse(text)
        except json.JSONDecodeError as e:
            logger.warning(f"初次解析JSON失败，尝试深度修复: {e}")
            try:
                fixed_text = text
                
                # 1. 处理未闭合的字符串 (Unterminated string)
                if fixed_text.count('"') % 2 != 0:
                    fixed_text += '"'
                
                # 2. 处理未闭合的括号嵌套结构
                stack = []
                for char in fixed_text:
                    if char == '{':
                        stack.append('}')
                    elif char == '[':
                        stack.append(']')
                    elif char == '}':
                        if stack and stack[-1] == '}':
                            stack.pop()
                    elif char == ']':
                        if stack and stack[-1] == ']':
                            stack.pop()
                
                # 逆序补齐所有未闭合的标签
                while stack:
                    fixed_text += stack.pop()
                
                return self._do_parse(fixed_text)
            except Exception as fix_err:
                logger.warning(f"深度修复并解析JSON响应失败: {fix_err}. 响应预览: {text[:100]}")
                return {}

    def _do_parse(self, text: str) -> Dict[str, Any]:
        """执行实际解析逻辑"""
        data = json.loads(text)
        
        # 提取核心字段，确保它们在结果字典的顶层
        result = {}
        
        # 1. 处理元数据键值对 (展开 metadata_values)
        if "metadata_values" in data and isinstance(data["metadata_values"], dict):
            result.update(data["metadata_values"])
            
        # 2. 合并根级别的其他重要字段 (不覆盖已有的 metadata_values)
        core_fields = ["doc_type", "purpose_summary", "product_entities", "outline"]
        for field in core_fields:
            if field in data:
                result[field] = data[field]
        
        # 3. 兼容旧版或嵌套格式的兜底逻辑
        if "outline" not in result and "doc_analysis" in data:
            result["outline"] = data["doc_analysis"].get("outline")
            
        if "doc_type" not in result and "doc_analysis" in data:
            result["doc_type"] = data["doc_analysis"].get("doc_type_guess") or data["doc_analysis"].get("doc_type")

        return result

    def _ensure_issue_date(self, text: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """确保结果中尽可能包含发文日期字段（issue_date）"""
        if not isinstance(result, dict):
            return result

        # 统一将不同命名的日期字段映射到 issue_date
        candidate_keys = [
            "issue_date", "document_date", "official_date",
            "发文日期", "成文日期", "印发日期", "发布日期",
            "发文时间", "成文时间"
        ]
        for key in candidate_keys:
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                normalized = self._normalize_issue_date_value(value)
                if normalized:
                    result["issue_date"] = normalized
                break

        # 若仍缺失，尝试从原文中兜底提取
        if not result.get("issue_date"):
            extracted = self._extract_issue_date_from_text(text)
            if extracted:
                result["issue_date"] = extracted
        else:
            normalized_existing = self._normalize_issue_date_value(str(result.get("issue_date")))
            if normalized_existing:
                result["issue_date"] = normalized_existing
            else:
                result.pop("issue_date", None)

        return result
    
    def _normalize_issue_date_value(self, value: str) -> Optional[str]:
        if not isinstance(value, str):
            return None
        v = value.strip()
        if not v:
            return None
        if v.lower() in {"unknown", "n/a", "na", "null", "none"}:
            return None
        if v in {"未知", "无", "-", "不详", "缺失"}:
            return None
        return v

    def _extract_issue_date_from_text(self, text: str) -> Optional[str]:
        """从正文中提取发文日期（优先匹配显式字段）"""
        if not text:
            return None

        patterns = [
            r"(?:发文日期|成文日期|印发日期|发布日期|发文时间|成文时间)\s*[：:]\s*([0-9]{4}[年\./-][0-9]{1,2}[月\./-][0-9]{1,2}日?)",
            r"(?:发文日期|成文日期|印发日期|发布日期|发文时间|成文时间)\s+([0-9]{4}[年\./-][0-9]{1,2}[月\./-][0-9]{1,2}日?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()

        return None

    def _get_extraction_prompt(self, text: str) -> str:
        """生成元数据提取提示词
        
        构建详细的提示词，指导LLM进行文档类型识别、三级提纲生成、
        产品实体提取和元数据字段设计。
        """
        return f"""
你是一个精通保险与金融文档的"文档建模与元数据设计专家"。
现在有一份中文文档，请你**完全基于文档内容本身**，分析文档结构并提取关键信息。

文档内容如下：
```text
{text}
```

请严格按照下面步骤思考和输出结果：

### 第一步：理解文档类型与用途
1. 判断文档类型 (doc_type)，必须从以下精确类别中选择：
   - [保险条款]: 核心合同文本，包含保障责任、免责、缴费、退保等文字条款。
   - [费率表]: 包含大量数值，通常包含"年龄"、"性别"、"交费期间"、"保费"等字段或类似含义的数据。
   - [现金价值表]: 包含大量数值，通常包含"保单年度"、"年龄"、"现金价值"、"账户价值"等字段。
   - [管理制度]: 内部操作规范、考核办法、流程说明。
   - [宣传彩页]: 面向客户的简易产品介绍、亮点说明。
   - [公文公告]: 官方通知、新闻发布、人事任免。
   - [其他]: 无法归类的文档。
2. **特别提醒**：如果文档中包含大量排列整齐的数字或类似 Excel/CSV 的结构，请优先考虑是否为 [费率表] 或 [现金价值表]，即使它们看起来像文字列表。
3. 总结主要用途 (purpose_summary)。

### 第二步：提取产品实体 (Product Entities)
1. 如果文档涉及保险、金融产品，请提取所有提到的产品全称及简称。

### 第三步：生成原子化三级结构化提纲 (Outline Tree)
1. 生成一个层级化的三级标题树。
2. **严禁合并具有独立编号的章节**（如：第一条、第二条、1.1、1.2、(一)）。即使内容简短，只要有独立标题或编号，必须作为独立节点列出。
3. 每个提纲项包含：
   - id: 唯一标识
   - level: 层级 (1, 2, 3)
   - title: 标题完整内容
   - anchor_text: **极其重要**。请从原文中摘录该标题出现的**完整准确字符串**，用于后续精确定位。
   - breadcrumb_path: 完整的标题路径，例如："第一章 > 1.1 > （二）"。
   - knowledge_type: **极其重要**。必须从以下 7 类中选择最适配的一个：
     - [概念定义]: 术语解释、对象定义、名词含义。
     - [规则约束]: 权利、义务、禁止行为、准入条件、判定标准。
     - [流程操作]: 步骤、环节、审批流、操作指南、时间顺序。
     - [数据数值]: 金额、比例、期限、费率、计算公式。
     - [触发条件]: 满足 If...Then... 逻辑的触发时点或后果。
     - [事实陈述]: 背景介绍、现状描述、不带规则的客观信息。
     - [异常除外]: 责任免除、不适用范围、特殊例外说明。
   - key_terms: 提取该章节涉及的 3-5 个核心业务术语或关键词。
   - summary: 该章节的核心内容摘要 (20-30字)
   - children: 子章节列表 (如果是第3级则为空数组)

### 第四步：设计元数据字段
1. 根据文档内容设计合适的元数据键值对 (metadata_values)。
2. **重点规则（公文公告）**：
   - 若文档类型为 [公文公告]，请优先识别并提取发文日期，统一字段名为 `issue_date`。
   - 可从“发文日期/成文日期/印发日期/发布日期”中识别，优先级依次为：发文日期 > 成文日期 > 印发日期 > 发布日期。
   - 如果存在多个日期，只保留最能代表正式发文时间的一个写入 `issue_date`。
   - 如果无法从文档中可靠识别日期，请不要输出 `issue_date` 字段（不要输出空字符串/未知/占位符）。

### 第五步：输出格式（只输出标准 JSON）

```json
{{
  "doc_type": "...",
  "purpose_summary": "...",
  "product_entities": ["产品A", "产品B"],
  "metadata_values": {{
    "key1": "value1"
  }},
  "outline": [
    {{
      "id": "1",
      "level": 1,
      "title": "第一章 ...",
      "anchor_text": "第一章 ...",
      "summary": "...",
      "children": [
        {{
          "id": "1.1",
          "level": 2,
          "title": "1.1 ...",
          "anchor_text": "1.1 ...",
          "summary": "...",
          "children": []
        }}
      ]
    }}
  ]
}}
```

要求：
1. `outline` 必须严谨反映文档的逻辑结构，标题和 `anchor_text` 必须与原文完全一致。
2. 只输出 JSON，无其他解释文字。
"""
