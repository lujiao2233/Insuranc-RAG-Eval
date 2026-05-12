"""多轮会话 case 生成相关 prompt 模板。"""

PROMPT_MULTI_TURN_OUTPUT_RULES = """
你必须只输出一个合法 JSON 对象，不得输出 Markdown、解释、前后缀文字。

JSON 结构必须严格包含以下字段：
{
  "case_type": "single_chunk_deep | same_doc_chain | cross_doc_assoc",
  "turns": [
    {
      "turn_index": 1,
      "question": "string",
      "expected_answer": "string",
      "dependency_type": "none | contextual | referential | accumulative",
      "context_hint": "string",
      "depends_on_turns": [1],
      "question_state_refs": ["前文已确认的对象/条件/主题"],
      "evidence_chunk_ids": ["anchor_chunk 或 support_chunk 的 chunk_id"]
    }
  ]
}

硬性约束：
1. turns 数量必须为 3 到 5。
2. 第 1 轮必须是基础问题，dependency_type 必须为 "none"。
3. 从第 2 轮开始，每一轮必须依赖前文，dependency_type 不能为 "none"。
4. 每一轮 expected_answer 都必须非空，且必须能从给定材料中得到支撑。
5. 后续轮的依赖必须建立在前文问题链、已提出的对象/条件/范围/主题和当前切片证据上，不要把 expected_answer 当作依赖依据。
6. context_hint 需要简洁说明本轮依赖了哪些前文问题信息。
7. 不得编造材料中不存在的事实、数字、实体或结论。
8. 问题与答案必须以给定切片的正文内容为依据，不得把 metadata、标题、摘要本身当作答案依据。
9. 禁止出现来源视角表述：根据材料、上述材料、文档中提到、材料A、材料B、上文提到、该文档指出。
10. 第1轮问题如果涉及具体产品、合同、责任、方案、条款对象，必须使用切片中明确出现的实体名称（如产品名称、合同名称、保险条款全称等），不要擅自引入新实体。禁止使用"条款要求""该保险""本产品""上述方案"等模糊指代，必须写出完整或部分实体名称。
11. 第 1 轮必须直接锚定 anchor_chunk 中明确出现的事实、规则、定义或流程节点，不得跨到切片未出现的新主题。
12. single_chunk_deep 类型下，后续轮只允许围绕同一主题逐步深挖，不得跳转到锚点切片正文未涉及的新章节主题。
13. 不得引入切片中未出现的关键事实，例如新增期限、材料名称、金额、比例、退费规则、责任条件、理赔步骤。
14. 从第 2 轮开始，depends_on_turns 必须列出所依赖的前置轮次；question_state_refs 必须列出继承的前文问题要素；evidence_chunk_ids 必须列出本轮直接使用的 chunk_id。
"""


PROMPT_MULTI_TURN_CASE_GENERATION = """
你是一名 RAG 多轮测试集设计专家。你的任务是基于给定切片簇，生成一个完整的多轮会话 case，
用于评估模型在连续对话中的上下文保持、跨轮依赖理解和知识整合能力。

输入信息：
- case_type: 指定的 case 类型
- anchor_chunk: 主锚点切片
- support_chunks: 辅助切片列表，可为空

case_type 含义：
- single_chunk_deep: 围绕单一切片逐层深挖，问题逐轮深入同一主题
- same_doc_chain: 基于同一文档内多个相关切片，形成顺序推进的逻辑链
- cross_doc_assoc: 基于不同文档的相关切片，形成跨文档关联与迁移

生成要求：
1. 设计 3 到 5 轮连续对话，整体像真实用户逐步追问，而不是独立题目拼接。
2. 第 1 轮只建立基础语境，不要过早引入复杂跨轮推理。
3. 第 2 轮起必须显式依赖前文上下文，可体现补充追问、指代、省略、比较、延伸分析等。
4. 每轮问题都应自然、简洁、可用于真实对话场景。
5. expected_answer 需要准确、可评估，但"跨轮依赖"必须体现在问题链和会话状态上，而不是建立在 expected_answer 的措辞上。
6. 问题与答案都必须能从给定切片正文中找到依据；若证据不足，必须缩小问题范围或重写。
7. 涉及具体产品、合同、保障责任、规则对象时，必须使用切片中明确出现的实体名称（如产品名称、保险条款全称等），不得自行脑补。禁止使用"条款要求""该保险""本产品"等模糊指代，必须写出完整或部分实体名称。
8. 禁止从保险常识、行业惯例或相邻章节习惯性补全未在切片中出现的关键信息。
9. 从第 2 轮开始，必须显式填写 depends_on_turns、question_state_refs、evidence_chunk_ids，用来描述本轮继承了哪些前文问题要素以及本轮直接依据哪些切片。

针对不同 case_type 的附加要求：
- single_chunk_deep:
  - 问题需围绕同一核心主题逐步深入。
  - 后续轮可使用“这个规则”“刚才提到的条件”之类的前文依赖。
  - 第 1 轮必须直接来自 anchor_chunk 正文里的显式信息点。
  - 不得从锚点切片跳到未出现的新主题，例如从诉讼时效跳到理赔材料、现金价值、核赔时效，除非正文明确出现。
- same_doc_chain:
  - 问题需体现同一文档内多个切片之间的顺序关系、条件关系或流程关系。
  - 至少有一轮需要结合前一轮和当前材料链条信息。
- cross_doc_assoc:
  - 问题需体现跨文档信息迁移、对照、整合或冲突识别。
  - 至少有一轮需要结合两个不同来源的知识片段。

下面会提供切片簇内容。请严格按要求生成结果。

""" + PROMPT_MULTI_TURN_OUTPUT_RULES


PROMPT_MULTI_TURN_CASE_REPAIR = """
你是一名多轮会话 case 修复助手。请根据给定切片和审核失败原因，重写整个 case。

修复目标：
1. 保留多轮连续对话形式。
2. 问题与 expected_answer 必须严格以给定切片正文为依据。
3. 删除或改写所有无法被切片支撑的事实、规则、期限、金额、材料要求、流程节点。
4. 保持 case_type 不变，并继续满足 3-5 轮、后续轮依赖前文等约束。
5. 如果某轮无法在当前切片中成立，必须改写该轮，而不是硬保留原问题。
6. 重写时继续使用 depends_on_turns、question_state_refs、evidence_chunk_ids 表达依赖关系，不要引入 standalone_question。

输出要求：
1. 只输出一个合法 JSON 对象。
2. 输出结构必须与多轮 case 生成结构完全一致：
{
  "case_type": "single_chunk_deep | same_doc_chain | cross_doc_assoc",
  "turns": [
    {
      "turn_index": 1,
      "question": "string",
      "expected_answer": "string",
      "dependency_type": "none | contextual | referential | accumulative",
      "context_hint": "string",
      "depends_on_turns": [1],
      "question_state_refs": ["前文已确认的对象/条件/主题"],
      "evidence_chunk_ids": ["anchor_chunk 或 support_chunk 的 chunk_id"]
    }
  ]
}
"""


PROMPT_TURN_DEPENDENCY_HINT = """
你是一名多轮对话结构标注助手。请根据给定的 turns，为每一轮补充或修正 dependency_type 与 context_hint。

标注目标：
1. 第 1 轮必须标记为 "none"。
2. 如果本轮只是基于当前问题本身即可回答，则标记为 "none"。
3. 如果本轮依赖上一轮或更早轮的问题语境、指代对象、已提出的条件、讨论范围、实体或比较对象，则标记为以下之一：
   - contextual: 依赖前文语境或话题背景
   - referential: 依赖前文指代对象、实体、术语、省略内容
   - accumulative: 依赖前面多轮累积出的条件、范围或信息整合
4. 从第 2 轮开始，优先识别真实依赖，不要轻易标记为 "none"。
5. context_hint 要简洁描述本轮依赖了哪些前文问题信息，例如：
   - “依赖上一轮中提到的保障责任范围”
   - “依赖前两轮已确认的产品对象和限制条件”
6. depends_on_turns 需要列出本轮依赖的前置轮次编号。
7. question_state_refs 需要列出本轮直接继承的前文问题要素，使用短语即可，例如“产品对象”“适用条件”“比较维度”。
8. evidence_chunk_ids 需要列出本轮回答直接依据的 chunk_id；如果主要依据 anchor_chunk，也要显式写出其 chunk_id。

输出要求：
1. 只输出合法 JSON。
2. 输出格式必须为：
{
  "turns": [
    {
      "turn_index": 1,
      "dependency_type": "none",
      "context_hint": "",
      "depends_on_turns": [],
      "question_state_refs": [],
      "evidence_chunk_ids": ["chunk-id"]
    }
  ]
}
3. 不要输出 question 或 expected_answer，只输出 turn_index、dependency_type、context_hint、depends_on_turns、question_state_refs、evidence_chunk_ids。
4. 不得改变 turn_index。
"""


def get_conversation_prompt_format_spec() -> str:
    """返回多轮 case 生成的输出格式说明。"""
    return PROMPT_MULTI_TURN_OUTPUT_RULES.strip()


__all__ = [
    "PROMPT_MULTI_TURN_OUTPUT_RULES",
    "PROMPT_MULTI_TURN_CASE_GENERATION",
    "PROMPT_MULTI_TURN_CASE_REPAIR",
    "PROMPT_TURN_DEPENDENCY_HINT",
    "get_conversation_prompt_format_spec",
]
