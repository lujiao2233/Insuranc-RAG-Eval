# 多轮对话评估 — WBS 任务分解表

> 基于 `multi_turn_conversation_evaluation_plan.md` 计划书，细化到可直接开发执行的任务级粒度。
> 每项任务包含：编号、任务名、描述、涉及文件、交付物、前置依赖、优先级、预估人天。

***

## 总览

| 阶段     | 模块          | 任务数    | 预估人天合计 |
| ------ | ----------- | ------ | ------ |
| 阶段一    | M1 数据模型与迁移  | 5      | 3      |
| 阶段一    | M2 多轮测试集生成  | 7      | 6      |
| 阶段一    | M3 多轮执行引擎   | 5      | 4      |
| 阶段一    | M4 多轮评估引擎   | 5      | 5      |
| 阶段一    | M5 API 与任务流 | 6      | 4      |
| 阶段二    | M6 前端页面与交互  | 8      | 6      |
| 阶段三    | M7 报告与导出    | 5      | 4      |
| 阶段三    | M8 测试与上线    | 6      | 4      |
| **合计** | <br />      | **51** | **36** |

***

## M1 数据模型与迁移

### M1-1 设计 ConversationTestCase 表结构

- **编号**: M1-1
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/models/database.py` 中新增 `ConversationTestCase` ORM 模型，字段包括：
  - `id` (CHAR(36), PK)
  - `testset_id` (CHAR(36), FK → testsets.id)
  - `case_type` (String(30)) — `single_chunk_deep` / `same_doc_chain` / `cross_doc_assoc`
  - `anchor_chunk_id` (CHAR(36)) — 主锚点切片
  - `support_chunk_ids` (JSON) — 辅助切片列表
  - `evaluation_criteria` (Text) — case 级评估标准描述
  - `turn_count` (Integer) — 实际轮数
  - `case_metadata` (JSON) — 扩展字段（文档来源、难度等）
  - `created_at`, `updated_at`
- **涉及文件**: `backend/models/database.py`
- **交付物**: ORM 模型代码、字段说明文档
- **前置依赖**: 无

### M1-2 设计 ConversationTurn 表结构

- **编号**: M1-2
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在同一文件新增 `ConversationTurn` ORM 模型，字段包括：
  - `id` (CHAR(36), PK)
  - `case_id` (CHAR(36), FK → conversation\_test\_cases.id, CASCADE)
  - `turn_index` (Integer) — 轮次序号（1-based）
  - `question` (Text) — 本轮问题
  - `expected_answer` (Text) — 预期答案
  - `dependency_type` (String(30)) — `none` / `contextual` / `referential` / `accumulative`
  - `context_hint` (Text) — 前文依赖提示
  - `turn_metadata` (JSON) — 扩展字段
  - `created_at`, `updated_at`
- **涉及文件**: `backend/models/database.py`
- **交付物**: ORM 模型代码
- **前置依赖**: M1-1

### M1-3 设计 ConversationExecution 与 TurnResult 表结构

- **编号**: M1-3
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 新增两个 ORM 模型：
  - `ConversationExecution`: `id`, `testset_id`, `evaluation_id`, `user_id`, `status`, `started_at`, `finished_at`, `execution_metadata`
  - `ConversationTurnResult`: `id`, `execution_id`, `case_id`, `turn_id`, `session_id_before`, `session_id_after`, `request_payload` (JSON), `response_payload` (JSON), `generated_answer` (Text), `refs` (Text), `turn_status` (String(20)), `execution_time_ms` (Integer), `created_at`, `updated_at`
- **涉及文件**: `backend/models/database.py`
- **交付物**: ORM 模型代码
- **前置依赖**: M1-1, M1-2

### M1-4 为 TestSet 和 Evaluation 增加模式标识

- **编号**: M1-4
- **优先级**: P0
- **预估**: 0.5d
- **描述**:
  - `TestSet` 新增 `conversation_mode` (String(20), default='single\_turn') — 标识 `single_turn` / `multi_turn`
  - `Evaluation` 新增 `evaluation_mode` (String(30), default='single\_turn') — 标识 `single_turn` / `deepeval_conversation`
  - 添加 relationship：`TestSet.conversation_cases` → `ConversationTestCase`，`ConversationExecution.testset`
- **涉及文件**: `backend/models/database.py`
- **交付物**: 字段与关系变更代码
- **前置依赖**: M1-1 \~ M1-3

### M1-5 编写数据库迁移与索引

- **编号**: M1-5
- **优先级**: P0
- **预估**: 1d
- **描述**:
  - 确保所有新增表的 `create_all` 能正确建表
  - 为 `ConversationTestCase.testset_id`、`ConversationTurn.case_id`、`ConversationTurnResult.execution_id`、`ConversationTurnResult.case_id` 建索引
  - 为 `TestSet.conversation_mode`、`Evaluation.evaluation_mode` 建索引
  - 验证 `Base.metadata.create_all(bind=engine)` 执行无报错
- **涉及文件**: `backend/models/database.py`, `backend/main.py`
- **交付物**: 迁移验证、索引定义
- **前置依赖**: M1-1 \~ M1-4

***

## M2 多轮测试集生成

### M2-1 定义 Case JSON Schema

- **编号**: M2-1
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/services/` 下新增 `conversation_case_schema.py`，定义生成阶段中间产物的 JSON 结构：
  - `ConversationCaseSchema`: `case_type`, `anchor_chunk`, `support_chunks`, `turns`, `evaluation_criteria`
  - `ConversationTurnSchema`: `turn_index`, `question`, `expected_answer`, `dependency_type`, `context_hint`
  - 增加校验函数 `validate_case_schema(case_dict) → bool`，确保：
    - `turns` 数量 3-5
    - 从第 2 轮起 `dependency_type != 'none'`
    - 每轮 `expected_answer` 非空
- **涉及文件**: 新建 `backend/services/conversation_case_schema.py`
- **交付物**: Schema 定义 + 校验函数
- **前置依赖**: M1-1, M1-2

### M2-2 实现切片簇选材算法

- **编号**: M2-2
- **优先级**: P0
- **预估**: 2d
- **描述**: 在 `backend/services/` 下新增 `conversation_chunk_selector.py`，实现三种选材策略：
  - **单切片深挖型**: 从单切片 metadata 提取分析结果，生成 3-5 轮渐进深挖问题
  - **同文档切片链型**: 从同一文档中选 2-3 个语义相关切片，按逻辑链排列
  - **跨文档关联型**: 从不同文档中选相关切片，考察跨文档知识迁移
  - 核心方法：`select_chunks_for_case(documents, case_type_config) → List[ChunkCluster]`
  - 利用现有 `DocumentChunk.chunk_metadata` 与 `DocumentChunk.entities` 中的分析结果
  - 默认比例配置：20% 单切片深挖 / 60% 同文档切片链 / 20% 跨文档关联
- **涉及文件**: 新建 `backend/services/conversation_chunk_selector.py`, 参考 `backend/services/advanced_testset_generator.py`
- **交付物**: 选材算法实现
- **前置依赖**: M1-1

### M2-3 编写多轮 prompt 模板

- **编号**: M2-3
- **优先级**: P0
- **预估**: 1.5d
- **描述**: 在 `backend/services/` 下新增 `conversation_prompt_templates.py`，包含：
  - `PROMPT_MULTI_TURN_CASE_GENERATION` — 给 LLM 的 case 生成 prompt（输入切片簇，输出完整 case JSON）
  - `PROMPT_TURN_DEPENDENCY_HINT` — 为每轮标注依赖关系和前文提示的辅助 prompt
  - prompt 要求 LLM 输出严格 JSON 格式，包含：
    - `case_type`, `turns[]`, `evaluation_criteria`
    - 每轮 `question`, `expected_answer`, `dependency_type`, `context_hint`
  - prompt 中强制规则：
    - 第 1 轮为基础问题，`dependency_type=none`
    - 后续轮必须有逻辑依赖
    - `expected_answer` 必须包含前文信息才能正确回答
- **涉及文件**: 新建 `backend/services/conversation_prompt_templates.py`
- **交付物**: prompt 模板常量与格式说明
- **前置依赖**: M2-1

### M2-4 实现多轮 case 生成主服务

- **编号**: M2-4
- **优先级**: P0
- **预估**: 1.5d
- **描述**: 新建 `backend/services/conversation_case_generator.py`，核心类 `ConversationCaseGenerator`：
  - `generate_cases(testset_id, num_cases, turn_range, case_type_ratio, user_id) → List[str]` — 返回生成的 case ID 列表
  - 流程：
    1. 查询文档与切片
    2. 调用切片簇选材
    3. 调用 LLM 生成 case JSON
    4. 校验 JSON schema
    5. 入库 `ConversationTestCase` + `ConversationTurn`
    6. 更新 `TestSet.question_count` 与 `TestSet.conversation_mode='multi_turn'`
  - 支持 `task_manager.update_progress()` 结构化进度
  - 在关键步骤调用 `task_manager.ensure_not_cancelled(task_id)`
- **涉及文件**: 新建 `backend/services/conversation_case_generator.py`
- **交付物**: 生成服务类
- **前置依赖**: M2-1, M2-2, M2-3, M1-1, M1-2, M1-4

### M2-5 实现生成后结构化校验与质量检查

- **编号**: M2-5
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在 `conversation_case_generator.py` 中增加 `validate_and_fix_cases()` 方法：
  - 轮数不足 3 的 case 自动补轮或标记为低质量
  - 后续轮 `dependency_type=none` 的标记为弱依赖
  - `expected_answer` 为空的自动重生成
  - 输出质量报告：有效 case 数 / 低质量 case 数 / 总轮数
- **涉及文件**: `backend/services/conversation_case_generator.py`
- **交付物**: 校验与修复逻辑
- **前置依赖**: M2-4

### M2-6 注册生成任务处理器

- **编号**: M2-6
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/services/task_handlers.py` 中：
  - 新增 `_run_generate_conversation_cases(params, task_id)` 处理器
  - 新增 `_prepare_generate_conversation_cases_retry(params)` — 重试前清空旧 case 与 turn
  - 注册到 `TASK_HANDLER_MAP["generate_conversation_cases"]`
  - 注册到 `TASK_RETRY_PREPARE_MAP["generate_conversation_cases"]`
- **涉及文件**: `backend/services/task_handlers.py`
- **交付物**: 处理器注册
- **前置依赖**: M2-4

### M2-7 新增多轮生成 API 路由

- **编号**: M2-7
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/testsets.py` 中新增：
  - `POST /testsets/{testset_id}/generate_conversation` — 接收参数 `{num_cases, turn_range, case_type_ratio, document_ids}`
  - 调用 `task_manager.submit_task("generate_conversation_cases", params)`
  - 返回 `{task_id, message}`
  - 校验 `TestSet.conversation_mode == 'multi_turn'` 或将 mode 设为 `multi_turn`
- **涉及文件**: `backend/api/routers/testsets.py`
- **交付物**: API 路由实现
- **前置依赖**: M2-6, M1-4

***

## M3 多轮执行引擎

### M3-1 TalkApiClient sessionId 支持改造

- **编号**: M3-1
- **优先级**: P0
- **预估**: 1d
- **描述**: 改造 `backend/services/api_client.py` 中 `TalkApiClient.chat()` 方法：
  - 新增参数 `session_id: str = ""` 和 `new_dialog: bool = True`
  - payload 中 `sessionId` 使用传入参数而非固定空串
  - payload 中 `newDialog` 使用传入参数而非固定 True
  - 新增方法 `chat_with_session(msg, session_id, new_dialog=False) → (answer, status, refs, new_session_id)`
    - 首次调用 `new_dialog=True, session_id=""`
    - 从响应中提取 `sessionId` 返回
    - 后续调用 `new_dialog=False, session_id=<上一轮返回值>`
  - **联调验证**: 先用真实环境验证 `sessionId` 在响应 JSON / SSE 流中的返回位置
- **涉及文件**: `backend/services/api_client.py`
- **交付物**: 改造后的 client 方法、sessionId 提取逻辑
- **前置依赖**: 无（但需要联调验证 sessionId 返回位置）

### M3-2 实现 MultiTurnConversationExecutor

- **编号**: M3-2
- **优先级**: P0
- **预估**: 1.5d
- **描述**: 新建 `backend/services/conversation_executor.py`，核心类 `MultiTurnConversationExecutor`：
  - `execute_testset(testset_id, execution_id, user_id, mobile, verify_code, bot_id, task_id) → None`
  - 流程：
    1. 查询该 testset 下所有 `ConversationTestCase`
    2. 对每个 case：
       a. 创建 `TalkApiClient` 并登录
       b. 首轮：`chat_with_session(turn_1.question, session_id="", new_dialog=True)`
       c. 提取并保存 `sessionId`
       d. 后续轮：`chat_with_session(turn_n.question, session_id=prev_session_id, new_dialog=False)`
       e. 每轮写入 `ConversationTurnResult`（含 `session_id_before/after`）
    3. 更新 `ConversationExecution` 状态
    4. 结构化进度：`current_step = case_idx * total_turns + turn_idx`，`total_steps = total_cases * avg_turns`
  - 在每轮后检查 `task_manager.ensure_not_cancelled(task_id)`
  - Case 级失败恢复：某 case 失败不影响后续 case，标记为 `partial_failed`
- **涉及文件**: 新建 `backend/services/conversation_executor.py`
- **交付物**: 执行器类
- **前置依赖**: M3-1, M1-3, M1-4

### M3-3 执行结果落库与状态管理

- **编号**: M3-3
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在执行器中完善落库逻辑：
  - 每轮 `ConversationTurnResult` 记录：
    - `request_payload`: 发送给 API 的完整 payload
    - `response_payload`: API 返回的原始 JSON
    - `session_id_before / session_id_after`
    - `generated_answer`, `refs`
    - `turn_status`: `ok` / `partial` / `failed` / `cancelled`
    - `execution_time_ms`
  - 每个 case 完成后更新 `ConversationTestCase.turn_count` 与 case 级状态
  - 整个 testset 完成后更新 `ConversationExecution.status` 与 `Evaluation.status`
- **涉及文件**: `backend/services/conversation_executor.py`
- **交付物**: 落库逻辑
- **前置依赖**: M3-2, M1-3

### M3-4 注册执行任务处理器

- **编号**: M3-4
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/services/task_handlers.py` 中：
  - 新增 `_run_execute_conversation_testset(params, task_id)`
  - 新增 `_prepare_execute_conversation_retry(params)` — 重试前清空旧 `ConversationTurnResult`
  - 注册到 `TASK_HANDLER_MAP["execute_conversation_testset"]`
  - 注册到 `TASK_RETRY_PREPARE_MAP["execute_conversation_testset"]`
- **涉及文件**: `backend/services/task_handlers.py`
- **交付物**: 处理器注册
- **前置依赖**: M3-2

### M3-5 新增多轮执行 API 路由

- **编号**: M3-5
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/testsets.py` 中新增：
  - `POST /testsets/{testset_id}/conversation_execution/start` — 接收 `{mobile, verify_code, bot_id}`
  - 创建 `ConversationExecution` 记录（克隆 testset 为 evaluation 阶段）
  - 调用 `task_manager.submit_task("execute_conversation_testset", params)`
  - 返回 `{task_id, execution_id, message}`
- **涉及文件**: `backend/api/routers/testsets.py`
- **交付物**: API 路由
- **前置依赖**: M3-4, M1-3

***

## M4 多轮评估引擎

### M4-1 新增 evaluate\_conversations() 入口

- **编号**: M4-1
- **优先级**: P0
- **预估**: 1d
- **描述**: 在 `backend/services/ragas_evaluator.py` 中新增方法：
  - `evaluate_conversations(cases, evaluation_metrics, run_config) → Dict`
  - 输入为 `List[ConversationTestCase]`（含 turn 与 turn\_result）
  - 按 case 聚合 turn 数据
  - 分发到 `_evaluate_conversations_with_deepeval()`
  - 输出两层结果：case 级指标汇总 + turn 级辅助结果
- **涉及文件**: `backend/services/ragas_evaluator.py`
- **交付物**: 评估入口方法
- **前置依赖**: M1-1 \~ M1-3, M3-2

### M4-2 接入 DeepEval 多轮评估指标

- **编号**: M4-2
- **优先级**: P0
- **预估**: 2d
- **描述**: 在 `ragas_evaluator.py` 中新增 `_evaluate_conversations_with_deepeval()`：
  - 尝试导入以下指标（增加版本兼容层）：
    - `Knowledge Retention`
    - `Conversation Relevancy`
    - `Conversation Completeness`
    - `Role Adherence`
  - 按 case 聚合 turn 为 `ConversationalTestCase`（如果 deepeval 支持）
  - 或退化为逐轮 `LLMTestCase` + 上下文拼接（兼容模式）
  - 每个 case 评估后输出 case 级得分 + 每轮得分
- **涉及文件**: `backend/services/ragas_evaluator.py`
- **交付物**: 多轮指标接入代码、兼容层
- **前置依赖**: M4-1

### M4-3 评估结果落库与聚合

- **编号**: M4-3
- **优先级**: P0
- **预估**: 1d
- **描述**:
  - 在 `EvaluationResult` 表中增加 `case_id` (CHAR(36), nullable) 和 `turn_id` (CHAR(36), nullable) 字段
  - 评估完成后：
    - 按 case 写入 case 级 `EvaluationResult`（`case_id` 非空，`turn_id` 为空）
    - 按 turn 写入 turn 级 `EvaluationResult`（`turn_id` 非空）
    - 每条记录的 `metrics` JSON 包含各指标分数
    - 每条记录的 `reasons` JSON 包含各指标评估理由
  - 更新 `Evaluation.overall_metrics` 为按 case 聚合的统计
  - 更新 `Evaluation.evaluation_metrics` 包含多轮指标名
- **涉及文件**: `backend/models/database.py`, `backend/services/ragas_evaluator.py`, `backend/api/routers/evaluations.py`
- **交付物**: 落库逻辑、字段扩展
- **前置依赖**: M4-2, M1-3

### M4-4 注册评估任务处理器

- **编号**: M4-4
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/services/task_handlers.py` 中：
  - 新增 `_run_evaluate_conversation(params, task_id)`
  - 新增 `_prepare_evaluate_conversation_retry(params)` — 重试前清空旧 `EvaluationResult`（含 case\_id / turn\_id）
  - 注册到 `TASK_HANDLER_MAP["evaluate_conversation"]`
  - 注册到 `TASK_RETRY_PREPARE_MAP["evaluate_conversation"]`
- **涉及文件**: `backend/services/task_handlers.py`
- **交付物**: 处理器注册
- **前置依赖**: M4-1, M4-2

### M4-5 新增强对话评估 API 路由

- **编号**: M4-5
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/evaluations.py` 中新增：
  - `POST /evaluations/conversation` — 接收 `{testset_id, evaluation_metrics}`
  - 克隆 testset 为 report 阶段
  - 创建 `Evaluation` 记录，`evaluation_mode='deepeval_conversation'`
  - 调用 `task_manager.submit_task("evaluate_conversation", params)`
  - 返回 `{task_id, evaluation_id, message}`
- **涉及文件**: `backend/api/routers/evaluations.py`
- **交付物**: API 路由
- **前置依赖**: M4-4, M1-4

***

## M5 API 与任务流

### M5-1 扩展任务进度结构

- **编号**: M5-1
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `BackgroundTask` 的 `_serialize_task()` 中增加多轮上下文字段：
  - `context_info` (JSON) — 包含 `{current_case, current_turn, total_cases, session_id}`
  - `task_manager.update_progress()` 增加 `context_info` 参数支持
  - 前端轮询时可读取当前执行到哪个 case 的第几轮
- **涉及文件**: `backend/services/task_manager.py`
- **交付物**: 进度结构扩展
- **前置依赖**: 无

### M5-2 新增会话级查询 API

- **编号**: M5-2
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/testsets.py` 中新增：
  - `GET /testsets/{testset_id}/conversation_cases` — 查询 case 列表（含 turn）
  - `GET /testsets/{testset_id}/conversation_cases/{case_id}` — 查询单个 case 详情
  - `GET /conversation_executions/{execution_id}` — 查询执行结果
  - `GET /conversation_executions/{execution_id}/turn_results` — 查询某执行的所有 turn 结果
- **涉及文件**: `backend/api/routers/testsets.py`（或新建 `backend/api/routers/conversations.py`）
- **交付物**: 查询 API
- **前置依赖**: M1-1 \~ M1-3

### M5-3 新增评估结果会话级查询 API

- **编号**: M5-3
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/evaluations.py` 中新增：
  - `GET /evaluations/{evaluation_id}/conversation_results` — 按 case 聚合的评估结果
  - `GET /evaluations/{evaluation_id}/conversation_results/{case_id}` — 单 case 评估详情（含每 turn）
- **涉及文件**: `backend/api/routers/evaluations.py`
- **交付物**: 评估查询 API
- **前置依赖**: M4-3

### M5-4 前端类型定义扩展

- **编号**: M5-4
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在 `frontend/src/types/models.ts` 中新增：
  - `ConversationCase` interface: `{id, testset_id, case_type, anchor_chunk_id, support_chunk_ids, evaluation_criteria, turn_count, turns[], case_metadata}`
  - `ConversationTurn` interface: `{id, case_id, turn_index, question, expected_answer, dependency_type, context_hint}`
  - `ConversationExecution` interface: `{id, testset_id, evaluation_id, status, started_at, finished_at}`
  - `ConversationTurnResult` interface: `{id, execution_id, case_id, turn_id, session_id_before, session_id_after, generated_answer, refs, turn_status}`
  - `TaskStatus` 增加 `context_info` 字段
- **涉及文件**: `frontend/src/types/models.ts`
- **交付物**: TypeScript 类型定义
- **前置依赖**: M1-1 \~ M1-3

### M5-5 前端 API 封装扩展

- **编号**: M5-5
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在 `frontend/src/api/` 中新增或扩展：
  - `frontend/src/api/conversations.ts` — 封装会话级 CRUD API
  - `testsetApi.generateConversationQuestions()` — 多轮生成
  - `testsetApi.startConversationExecution()` — 多轮执行
  - `evaluationApi.createConversationEvaluation()` — 多轮评估
  - `evaluationApi.getConversationResults()` — 多轮评估结果查询
- **涉及文件**: 新建 `frontend/src/api/conversations.ts`, 扩展 `frontend/src/api/testsets.ts`, `frontend/src/api/evaluations.ts`
- **交付物**: API 封装函数
- **前置依赖**: M5-2, M5-3, M5-4

### M5-6 任务中心多轮任务类型适配

- **编号**: M5-6
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在 `frontend/src/stores/task.ts` 中：
  - `AppTask.type` 增加 `'conversation'` 类型
  - `AppTask` 增加 `contextInfo?: { currentCase, currentTurn, totalCases, sessionId }` 字段
  - `MainLayout.vue` 任务中心增加多轮任务的进度展示：
    - `Case 2/5 | Turn 3/4 | Session: abc123`
  - 取消/重试按钮对多轮任务同样生效
- **涉及文件**: `frontend/src/stores/task.ts`, `frontend/src/components/layout/MainLayout.vue`
- **交付物**: 任务中心适配
- **前置依赖**: M5-1, M5-4

***

## M6 前端页面与交互

### M6-1 测试集生成页多轮模式切换

- **编号**: M6-1
- **优先级**: P1
- **预估**: 1d
- **描述**: 改造 `frontend/src/views/testsets/TestSetGenerationView.vue`：
  - 增加"单轮 / 多轮"模式切换（Radio 或 Tab）
  - 多轮模式时显示额外参数：
    - case 数量（Number input, default 5）
    - 每 case 轮数范围（Slider: 3-5）
    - case 类型比例（三个百分比输入，自动归一化）
  - 提交时调用 `testsetApi.generateConversationQuestions()`
  - 轮询任务进度时读取 `contextInfo.currentCase / currentTurn / totalCases`
  - 进度展示格式：`正在生成 Case 2/5，Turn 3...`
- **涉及文件**: `frontend/src/views/testsets/TestSetGenerationView.vue`
- **交付物**: 生成页多轮配置 UI
- **前置依赖**: M5-5, M5-6

### M6-2 测试集详情页多轮 case 展示

- **编号**: M6-2
- **优先级**: P1
- **预估**: 1.5d
- **描述**: 改造 `frontend/src/views/testsets/TestSetDetailView.vue`（或新建多轮详情组件）：
  - 当 `TestSet.conversation_mode === 'multi_turn'` 时，切换为 case 列表视图
  - 每个 case 显示：
    - case 类型标签（单切片深挖 / 同文档切片链 / 跨文档关联）
    - 轮次列表，展示每轮问题 + 预期答案 + 依赖类型标签
    - 可展开查看切片来源
  - 支持单独编辑某个 turn 的预期答案
- **涉及文件**: `frontend/src/views/testsets/TestSetDetailView.vue` 或新建组件
- **交付物**: 多轮 case 展示 UI
- **前置依赖**: M5-2, M5-5

### M6-3 执行页多轮会话进度展示

- **编号**: M6-3
- **优先级**: P1
- **预估**: 1d
- **描述**: 改造 `frontend/src/views/testsets/TestSetExecutionView.vue`：
  - 当执行多轮测试集时，进度展示：
    - 当前 case 序号 / 总 case 数
    - 当前 turn 序号 / 该 case 总轮数
    - 当前 sessionId（缩略显示）
  - 轮询时读取 `TaskStatus.contextInfo`
  - 执行完成后跳转到 case 列表查看结果
- **涉及文件**: `frontend/src/views/testsets/TestSetExecutionView.vue`
- **交付物**: 执行进度增强 UI
- **前置依赖**: M5-5, M5-6

### M6-4 评估创建页多轮评估入口

- **编号**: M6-4
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 改造 `frontend/src/views/evaluations/EvaluationCreateView.vue`：
  - 当选择的 testset 是 `multi_turn` 模式时：
    - 评估方法自动切换为 `deepeval_conversation`
    - 指标选项变为：`ConversationCompletenessMetric`, `TurnRelevancyMetric`, `KnowledgeRetentionMetric`
    - 可勾选指标组合
  - 提交时调用 `evaluationApi.createConversationEvaluation()`
- **涉及文件**: `frontend/src/views/evaluations/EvaluationCreateView.vue`
- **交付物**: 多轮评估创建 UI
- **前置依赖**: M5-5

### M6-5 评估详情页多轮结果视图

- **编号**: M6-5
- **优先级**: P1
- **预估**: 2d
- **描述**: 改造 `frontend/src/views/evaluations/EvaluationDetailView.vue`：
  - 当 `Evaluation.evaluation_mode === 'deepeval_conversation'` 时，切换为会话视图：
    - 总览面板：case 级指标均值 + 指标分布图
    - Case 列表：
      - 每个 case 显示会话完整性得分、知识保持得分
      - 展开 turn 列表：
        - 每轮显示：问题、模型回答、逐轮相关性得分、评估理由
        - sessionId 变化链路展示
    - 支持按 case 类型筛选
    - 支持按指标排序
- **涉及文件**: `frontend/src/views/evaluations/EvaluationDetailView.vue`
- **交付物**: 多轮评估详情 UI
- **前置依赖**: M5-3, M5-5

### M6-6 执行结果对话回放组件

- **编号**: M6-6
- **优先级**: P2
- **预估**: 1d
- **描述**: 新建 `frontend/src/components/ConversationReplay.vue`：
  - 可视化回放一个 case 的完整对话过程
  - 左侧：用户问题（按轮次排列，标注依赖类型）
  - 右侧：模型回答 + 引用来源
  - 底部：sessionId 变化时间线
  - 支持在评估详情页和报告页中嵌入
- **涉及文件**: 新建 `frontend/src/components/ConversationReplay.vue`
- **交付物**: 对话回放组件
- **前置依赖**: M6-5

### M6-7 多轮测试集列表页适配

- **编号**: M6-7
- **优先级**: P2
- **预估**: 0.5d
- **描述**: 改造 `frontend/src/views/testsets/TestSetsView.vue`：
  - 测试集列表中增加 `conversation_mode` 标签（单轮 / 多轮）
  - 多轮测试集显示 case 数量而非 question 数量
  - 筛选器增加"仅多轮"选项
- **涉及文件**: `frontend/src/views/testsets/TestSetsView.vue`
- **交付物**: 列表页适配
- **前置依赖**: M5-2, M5-5

### M6-8 前端路由与导航更新

- **编号**: M6-8
- **优先级**: P2
- **预估**: 0.5d
- **描述**:
  - 在 `frontend/src/router/` 中为多轮相关页面确认路由路径
  - 侧边导航增加"多轮评估"入口（或在测试集/评估导航下增加子入口）
  - 确保多轮页面与单轮页面共享路由参数风格（testset\_id / evaluation\_id）
- **涉及文件**: `frontend/src/router/index.ts`, `frontend/src/components/layout/MainLayout.vue`
- **交付物**: 路由与导航更新
- **前置依赖**: M6-1 \~ M6-5

***

## M7 报告与导出

### M7-1 报告页会话维度视图

- **编号**: M7-1
- **优先级**: P1
- **预估**: 1.5d
- **描述**: 改造报告中心页面，增加会话维度视图：
  - 当评估为多轮模式时，报告展示：
    - 总览卡片：case 总数、平均会话完整性、平均知识保持率
    - 按 case 类型分组的柱状图
    - case 级得分分布热力图（行=case，列=指标）
  - 支持从总览点击进入单个 case 详情
- **涉及文件**: `frontend/src/views/reports/` 或评估详情页内嵌报告区域
- **交付物**: 报告会话视图
- **前置依赖**: M6-5

### M7-2 报告页 Turn 级明细展示

- **编号**: M7-2
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在报告页 case 详情中展示 turn 级明细：
  - 每轮：问题 → 模型回答 → 逐轮相关性得分 → 知识保持得分 → 评估理由
  - 标注依赖类型：`[依赖前文]` / `[独立问题]`
  - 可展开查看 `sessionId` 变化
  - 嵌入 `ConversationReplay.vue` 回放组件
- **涉及文件**: 报告页面组件
- **交付物**: Turn 级展示
- **前置依赖**: M7-1, M6-6

### M7-3 CSV 导出字段扩展

- **编号**: M7-3
- **优先级**: P1
- **预估**: 0.5d
- **描述**: 在 `backend/api/routers/evaluations.py` 导出逻辑中扩展多轮导出字段：
  - 新增列：`case_id`, `case_type`, `turn_index`, `session_id_before`, `session_id_after`, `dependency_type`
  - 新增多轮指标列：`conversation_completeness`, `turn_relevancy`, `knowledge_retention`
  - 多轮导出格式：每 turn 一行，case 级指标在首行标注
- **涉及文件**: `backend/api/routers/evaluations.py`, `backend/api/routers/testsets.py`（导出端）
- **交付物**: CSV 导出扩展
- **前置依赖**: M4-3

### M7-4 JSON 导出与结构化数据输出

- **编号**: M7-4
- **优先级**: P2
- **预估**: 0.5d
- **描述**: 增加多轮评估结果的 JSON 导出端：
  - `GET /evaluations/{evaluation_id}/conversation_export?format=json`
  - 输出结构：`{cases: [{case_id, case_type, turns: [{turn_index, question, expected_answer, generated_answer, metrics, reasons}], case_metrics}], overall_metrics}`
  - JSON 导出保留完整层级，便于二次分析
- **涉及文件**: `backend/api/routers/evaluations.py`
- **交付物**: JSON 导出端
- **前置依赖**: M4-3

### M7-5 报告聚合统计增强

- **编号**: M7-5
- **优先级**: P2
- **预估**: 1d
- **描述**: 在后端新增聚合统计 API：
  - `GET /evaluations/{evaluation_id}/conversation_stats`
  - 返回：
    - 按 case 类型的指标均值对比
    - 依赖类型 vs 指标表现的相关性
    - sessionId 保持率统计
    - 低得分 case 自动标记与原因总结
  - 前端报告页展示为图表
- **涉及文件**: 后端新增统计端，前端报告页图表组件
- **交付物**: 聚合统计 API + 图表展示
- **前置依赖**: M7-1, M4-3

***

## M8 测试与上线

### M8-1 Case Schema 校验单元测试

- **编号**: M8-1
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 编写单元测试覆盖：
  - 合法 case JSON 通过 `validate_case_schema()` 校验
  - 轮数不足 3 的 case 被拒绝
  - 后续轮 `dependency_type=none` 的 case 被标记为弱依赖
  - `expected_answer` 空的 turn 被拒绝
  - case 类型不在枚举内的被拒绝
- **涉及文件**: `backend/tests/` 或 `tests/`
- **交付物**: 测试用例
- **前置依赖**: M2-1, M2-5

### M8-2 切片选材逻辑单元测试

- **编号**: M8-2
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 编写单元测试覆盖 `conversation_chunk_selector.py`：
  - 单切片深挖型选材正确
  - 同文档切片链选材：切片来源同一文档且语义相关
  - 跨文档关联选材：切片来源不同文档
  - 比例配置生效
  - 边界：文档只有 1 个切片时的降级处理
- **涉及文件**: `backend/tests/`
- **交付物**: 测试用例
- **前置依赖**: M2-2

### M8-3 会话执行状态机集成测试

- **编号**: M8-3
- **优先级**: P0
- **预估**: 1d
- **描述**: 编写集成测试覆盖执行引擎：
  - 正常流程：case 1 → case 2 → case 3 顺序执行
  - sessionId 正确传递与提取
  - 单 case 失败不影响后续 case
  - 任务取消在 turn 间正确中断
  - 任务重试清理旧结果后重新执行
  - 边界：API 返回超时 / SSE 流中断
- **涉及文件**: `backend/tests/`
- **交付物**: 集成测试
- **前置依赖**: M3-2, M3-3

### M8-4 评估指标集成测试

- **编号**: M8-4
- **优先级**: P0
- **预估**: 0.5d
- **描述**: 编写集成测试覆盖评估引擎：
  - 多轮指标正确计算（至少 mock 3 个 case）
  - 兼容层在 deepeval 不支持多轮指标时正确降级
  - case 级与 turn 级结果正确入库
  - `overall_metrics` 按案例聚合正确
- **涉及文件**: `backend/tests/`
- **交付物**: 测试用例
- **前置依赖**: M4-2, M4-3

### M8-5 端到端主链路验证

- **编号**: M8-5
- **优先级**: P0
- **预估**: 1d
- **描述**: 人工验证完整链路：
  - 创建多轮测试集 → 执行 → 评估 → 查看报告 → 导出 CSV
  - 前端 UI 完整跑通
  - 取消 / 重试在各个阶段正确工作
  - 异常场景：session 丢失 / API 限流 / 评估 LLM 错误
  - 记录联调结果与问题清单
- **涉及文件**: 全链路
- **交付物**: 联调记录、问题清单
- **前置依赖**: 所有前序模块

### M8-6 上线准备与配置补齐

- **编号**: M8-6
- **优先级**: P1
- **预估**: 0.5d
- **描述**:
  - 补齐 `config_service.py` 中多轮相关配置键：
    - `conversation.default_case_count`
    - `conversation.default_turn_range`
    - `conversation.default_type_ratio`
    - `conversation.execution_timeout`
  - 增加日志与报警：
    - 多轮任务执行异常日志
    - sessionId 丢失报警
  - 增加数据清理策略：
    - 多轮测试集生命周期与单轮一致（base → evaluation → report）
    - 失败任务残留数据自动清理
- **涉及文件**: `backend/services/config_service.py`, `backend/services/task_manager.py`
- **交付物**: 配置项、日志、清理策略
- **前置依赖**: M8-5

***

## 依赖关系图

```
M1-1 → M1-2 → M1-3 → M1-4 → M1-5
                              ↓
M2-1 (依赖 M1-1, M1-2)
M2-2 (依赖 M1-1)
M2-3 (依赖 M2-1)
M2-4 (依赖 M2-1, M2-2, M2-3, M1-1, M1-2, M1-4)
M2-5 (依赖 M2-4)
M2-6 (依赖 M2-4)
M2-7 (依赖 M2-6, M1-4)

M3-1 (独立，但需联调 sessionId)
M3-2 (依赖 M3-1, M1-3, M1-4)
M3-3 (依赖 M3-2, M1-3)
M3-4 (依赖 M3-2)
M3-5 (依赖 M3-4, M1-3)

M4-1 (依赖 M1-1~M1-3, M3-2)
M4-2 (依赖 M4-1)
M4-3 (依赖 M4-2, M1-3)
M4-4 (依赖 M4-1, M4-2)
M4-5 (依赖 M4-4, M1-4)

M5-1 (独立)
M5-2 (依赖 M1-1~M1-3)
M5-3 (依赖 M4-3)
M5-4 (依赖 M1-1~M1-3)
M5-5 (依赖 M5-2, M5-3, M5-4)
M5-6 (依赖 M5-1, M5-4)

M6-1 (依赖 M5-5, M5-6)
M6-2 (依赖 M5-2, M5-5)
M6-3 (依赖 M5-5, M5-6)
M6-4 (依赖 M5-5)
M6-5 (依赖 M5-3, M5-5)
M6-6 (依赖 M6-5)
M6-7 (依赖 M5-2, M5-5)
M6-8 (依赖 M6-1~M6-5)

M7-1 (依赖 M6-5)
M7-2 (依赖 M7-1, M6-6)
M7-3 (依赖 M4-3)
M7-4 (依赖 M4-3)
M7-5 (依赖 M7-1, M4-3)

M8-1 (依赖 M2-1, M2-5)
M8-2 (依赖 M2-2)
M8-3 (依赖 M3-2, M3-3)
M8-4 (依赖 M4-2, M4-3)
M8-5 (依赖全部)
M8-6 (依赖 M8-5)
```

***

## 建议排期（按任务编号）

### 第 1 周：数据模型 + 选材 + prompt + sessionId 联调

| 任务               | 预估 |
| ---------------- | -- |
| M1-1 \~ M1-5     | 3d |
| M2-1, M2-2, M2-3 | 4d |
| M3-1 (含联调)       | 1d |

### 第 2 周：生成 + 执行引擎

| 任务                     | 预估 |
| ---------------------- | -- |
| M2-4, M2-5, M2-6, M2-7 | 4d |
| M3-2, M3-3, M3-4, M3-5 | 3d |
| M5-1, M5-2             | 1d |

### 第 3 周：评估引擎 + API 层 + 前端类型

| 任务                           | 预估 |
| ---------------------------- | -- |
| M4-1, M4-2, M4-3, M4-4, M4-5 | 5d |
| M5-3, M5-4, M5-5, M5-6       | 2d |

### 第 4 周：前端页面 + 报告

| 任务                           | 预估   |
| ---------------------------- | ---- |
| M6-1, M6-2, M6-3, M6-4, M6-5 | 5d   |
| M7-1, M7-2, M7-3             | 2.5d |

### 第 5 周：导出 + 测试 + 上线

| 任务               | 预估   |
| ---------------- | ---- |
| M7-4, M7-5       | 1.5d |
| M6-6, M6-7, M6-8 | 2d   |
| M8-1 \~ M8-6     | 4d   |

***

## 风险标注

| 任务   | 风险点                    | 应对                                   |
| ---- | ---------------------- | ------------------------------------ |
| M3-1 | sessionId 返回位置不明确      | 第 1 周优先联调，如无 sessionId 则降级为无状态逐轮     |
| M4-2 | deepeval 版本可能不支持多轮指标   | 已设计 GEval 兼容层，确保降级可用                 |
| M2-4 | LLM 生成 case JSON 格式不稳定 | 已设计 schema 校验 + 自动修复                 |
| M6-5 | 评估详情页复杂度高              | 优先做 case 列表 + turn 展开核心视图，回放组件 P2 后补 |

***

## 优先级汇总

| 优先级 | 任务数 | 任务编号                                                                             |
| --- | --- | -------------------------------------------------------------------------------- |
| P0  | 29  | M1-1\~M1-5, M2-1\~M2-4,M2-6,M2-7, M3-1\~M3-5, M4-1\~M4-5, M5-1\~M5-3, M8-1\~M8-5 |
| P1  | 16  | M2-5, M5-4\~M5-6, M6-1\~M6-5, M7-1\~M7-3, M8-6                                   |
| P2  | 6   | M6-6\~M6-8, M7-4, M7-5                                                           |

***

## 一句话版本

- 51 项任务，36 人天，P0 先做后端全链路 + P1 再做前端接入 + P2 补导出与回放，5 周交付。

