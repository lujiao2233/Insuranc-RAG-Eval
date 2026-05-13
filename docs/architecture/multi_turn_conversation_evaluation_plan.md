# 多轮对话评估业务全流程计划书

## 1. 任务目标

- 为现有 RAG 系统新增一套"多轮对话评估"完整业务流，覆盖`测试集生成 -> 会话执行 -> 多轮评估 -> 报告展示/导出`。
- 方案以当前主链路为基础扩展，尽量复用现有测试集、执行、评估、任务队列体系，避免推翻重做。
- 当前可复用的核心入口包括：
  - 测试集生成与执行：`backend/api/routers/testsets.py`
  - 评估任务：`backend/api/routers/evaluations.py`
  - 评估引擎：`backend/services/ragas_evaluator.py`
  - 高级生成器：`backend/services/advanced_testset_generator.py`
  - 执行客户端：`backend/services/api_client.py`

## 2. 总体范围

- 本次任务计划书覆盖 8 个模块：
  - 数据模型与迁移
  - 多轮测试集生成
  - 多轮执行引擎
  - 多轮评估引擎
  - API 与任务流
  - 前端页面与交互
  - 报告与导出
  - 测试、验证与上线

## 3. 业务全流程

- 文档分析后，基于切片簇生成多轮 case
- 每个 case 生成 3-5 轮强依赖问题
- 执行阶段按 `case -> turn` 顺序调用问答接口并维护 `sessionId`
- 每轮记录请求、响应、引用、会话号变化
- 评估阶段按 case 聚合，接入 DeepEval 多轮指标
- 报告阶段输出 case 级与 turn 级结果，并支持导出

## 4. 模块一：数据模型与迁移

### 4.1 目标

- 补齐"会话级"实体，摆脱当前仅 `Question/EvaluationResult` 的单轮结构。

### 4.2 当前基础

- 现有测试集与问题模型在 `backend/models/database.py`

### 4.3 任务项

- 新增 `ConversationTestCase`
- 新增 `ConversationTurn`
- 新增 `ConversationExecution`
- 新增 `ConversationTurnResult`
- 为 `TestSet` 增加测试集模式标识，如 `single_turn` / `multi_turn`
- 为 `Evaluation` 增加评估模式标识，如 `deepeval_conversation`

### 4.4 交付物

- 数据库表设计说明
- 建表/迁移脚本
- ORM 模型

### 4.5 依赖

- 无，优先级最高

### 4.6 验收标准

- 能完整表示一个 case、多个 turn、一次 execution、每轮执行结果

## 5. 模块二：多轮测试集生成

### 5.1 目标

- 从切片簇生成结构化多轮 case，而不是独立单题。

### 5.2 当前基础

- 现有生成任务入口在 `backend/api/routers/testsets.py`
- 现有生成任务执行在 `backend/api/routers/testsets.py`
- 高级生成器已能从切片 metadata 提取分析结果，适合做 case 选材

### 5.3 任务项

- 新增生成模式 `conversation_multi_turn`
- 定义 case JSON schema
- 实现"切片簇选材"规则：
  - 单切片深挖型
  - 同文档切片链型
  - 跨文档关联型
- 实现多轮 prompt 模板
- 生成后做结构化校验：
  - 轮数 3-5
  - 后续轮存在依赖
  - 每轮有 `expected_answer`
  - case 有 `evaluation_criteria`
- 入库 case 与 turn 结构

### 5.4 交付物

- case schema
- 选材算法
- prompt 模板
- 生成落库逻辑

### 5.5 依赖

- 数据模型模块

### 5.6 验收标准

- 能生成一批 case，每个 case 至少 3 轮且依赖关系清晰

## 6. 模块三：多轮执行引擎

### 6.1 目标

- 支持真实连续对话，维护 `sessionId`，执行顺序为 `case -> turn`。

### 6.2 当前基础

- 当前执行逻辑是逐题独立
- 当前客户端请求体已有 `sessionId` 字段位

### 6.3 任务项

- 新增 `MultiTurnConversationExecutor`
- 改造 `TalkApiClient`
  - 首轮不传 `sessionId`
  - 解析响应中的 `sessionId`
  - 后续轮传入 `sessionId`
- 记录每轮：
  - request payload
  - response payload
  - `session_id_before`
  - `session_id_after`
  - 生成答案
  - refs
  - 执行状态
- 增加 case 级失败恢复与中断策略

### 6.4 交付物

- 执行器服务类
- client 扩展方法
- 执行日志落库逻辑

### 6.5 依赖

- 数据模型模块

### 6.6 风险

- `sessionId` 返回位置需先联调确认

### 6.7 验收标准

- 同一个 case 后续轮请求可携带同一会话链路

## 7. 模块四：多轮评估引擎

### 7.1 目标

- 在现有单轮评估基础上，新增会话级评估能力。

### 7.2 当前基础

- 现有 DeepEval 接入仅支持单轮 `LLMTestCase`

### 7.3 任务项

- 新增评估方法 `deepeval_conversation`
- 新增 `evaluate_conversations()` 入口
- 按 case 聚合 turn 数据
- 接入以下指标：
  - `ConversationCompletenessMetric`
  - `TurnRelevancyMetric`
  - `KnowledgeRetentionMetric`
- 输出两层结果：
  - case 级指标
  - turn 级辅助结果
- 增加版本兼容层，屏蔽 DeepEval 不同版本导入差异

### 7.4 交付物

- 多轮评估引擎实现
- 指标映射表
- case/turn 输出结构

### 7.5 依赖

- 数据模型模块
- 执行引擎模块

### 7.6 风险

- 依赖本地 `deepeval` 版本能力

### 7.7 验收标准

- 可对一组 case 批量评估并产出结构化结果

## 8. 模块五：API 与任务流

### 8.1 目标

- 把多轮生成、执行、评估全部挂接进现有统一任务队列。

### 8.2 当前基础

- 当前已统一为 `submit_task()` 入队，worker 轮询执行

### 8.3 任务项

- 新增多轮测试集生成 API
- 新增多轮执行 API
- 新增强对话评估 API
- 扩展 `task_handlers.py` 新任务类型：
  - `generate_conversation_cases`
  - `execute_conversation_testset`
  - `evaluate_conversation`
- 扩展任务进度结构：
  - case 总数
  - 当前 case
  - 当前 turn

### 8.4 交付物

- API 设计文档
- 路由实现
- 任务处理器注册

### 8.5 依赖

- 生成、执行、评估三个核心模块

### 8.6 验收标准

- 三类任务都能入队、取消、重试、轮询

## 9. 模块六：前端页面与交互

### 9.1 目标

- 让用户可创建多轮测试集、执行、查看会话级评估。

### 9.2 当前基础

- 测试集生成页：`frontend/src/views/testsets/TestSetGenerationView.vue`
- 执行页：`frontend/src/views/testsets/TestSetExecutionView.vue`
- 评估页：`frontend/src/views/evaluations/EvaluationCreateView.vue`
- 详情页：`frontend/src/views/evaluations/EvaluationDetailView.vue`

### 9.3 任务项

- 生成页增加"单轮/多轮"模式切换
- 多轮模式增加参数项：
  - case 数
  - 每 case 轮数范围
  - case 类型比例
- 执行页新增会话执行进度展示：
  - 当前 case
  - 当前 turn
  - 当前 `sessionId`
- 评估详情页新增：
  - case 列表
  - 展开看 turn 明细
  - 会话级指标
  - 每轮回答与引用

### 9.4 交付物

- 页面原型
- API 对接
- 状态管理

### 9.5 依赖

- API 与任务流模块

### 9.6 验收标准

- 用户能完整跑通"创建多轮测试集 -> 执行 -> 评估 -> 查看结果"

## 10. 模块七：报告与导出

### 10.1 目标

- 输出 case 级和 turn 级分析结果，支持回溯问题。

### 10.2 当前基础

- 当前报告主要按单题展示

### 10.3 任务项

- 报告页新增会话维度视图
- case 级指标摘要
- turn 级执行日志和评分细项
- 导出字段扩展：
  - `case_id`
  - `turn_index`
  - `session_id_before`
  - `session_id_after`
  - `generated_answer`
  - `turn_relevancy`
  - `knowledge_retention`
  - `conversation_completeness`
- 支持 CSV/JSON 导出

### 10.4 交付物

- 报告字段设计
- 导出实现
- 展示模板

### 10.5 依赖

- 评估引擎模块

### 10.6 验收标准

- 能对一个 case 的所有 turn 做完整回放和评分说明

## 11. 模块八：测试、验证与上线

### 11.1 目标

- 保证这条新业务链路可稳定运行。

### 11.2 任务项

- 单元测试：
  - case schema 校验
  - 切片选材逻辑
  - 会话执行状态机
- 集成测试：
  - 生成 -> 执行 -> 评估主链路
  - 取消/重试
  - session 丢失/接口异常
- 人工联调：
  - `sessionId` 提取验证
  - deepeval 多轮指标导入验证
- 上线准备：
  - 配置项补齐
  - 报警与日志
  - 数据清理策略

### 11.3 交付物

- 测试用例清单
- 联调记录
- 上线检查表

### 11.4 依赖

- 所有前序模块

### 11.5 验收标准

- 关键主链路与异常链路均可验证通过

## 12. 建议实施阶段

### 12.1 第一阶段：后端 MVP

- 范围：
  - 数据模型
  - 多轮生成
  - 多轮执行
  - 多轮评估
  - API 入队
- 目标：
  - 后端先打通完整链路
- 预计产出：
  - 可通过接口跑完整流程

### 12.2 第二阶段：前端接入

- 范围：
  - 生成页
  - 执行页
  - 评估详情页
- 目标：
  - 用户可在 UI 中完整使用

### 12.3 第三阶段：报告与导出

- 范围：
  - 报告展示
  - CSV/JSON 导出
  - 统计聚合
- 目标：
  - 结果可运营、可分析、可复盘

## 13. 建议排期

- 第 1 周：
  - 数据模型
  - schema
  - 生成规则与 prompt
  - `sessionId` 联调验证
- 第 2 周：
  - 多轮执行器
  - API client 改造
  - 执行结果落库
- 第 3 周：
  - 多轮评估器
  - DeepEval 指标接入
  - 批量评估与任务流
- 第 4 周：
  - 前端接入
  - 报告展示
  - 导出与联调
- 第 5 周：
  - 回归测试
  - 性能优化
  - 上线准备

## 14. 关键风险

- `sessionId` 返回位置不明确，需优先联调确认
- DeepEval 多轮指标可能存在版本差异
- 如果继续沿用单轮表结构硬扩展，后续维护成本会明显上升
- 报告页复杂度会比单轮高很多，需要提前设计信息层级

## 15. 关键里程碑

- `M1`：case/turn 数据模型落地
- `M2`：多轮 case 自动生成可入库
- `M3`：多轮执行器拿到稳定 `sessionId`
- `M4`：DeepEval 多轮指标跑通
- `M5`：前端完整业务流可用
- `M6`：报告导出完成并通过验收

## 16. 验收标准

- 用户可创建多轮测试集
- 每个 case 包含 `3-5` 轮且有显式依赖
- 执行时后续轮可正确带 `sessionId`
- 评估结果包含三类多轮指标
- 报告页可查看 case 级与 turn 级详情
- 任务支持进度、取消、重试
- 异常场景下状态可回收，不残留脏数据

## 17. 优先级建议

- `P0`
  - 数据模型
  - 多轮生成
  - `sessionId` 执行器
  - 多轮评估
- `P1`
  - 前端完整接入
  - 报告展示
- `P2`
  - 导出增强
  - 聚合分析
  - 高级筛选

## 18. 建议的任务拆分清单

### 18.1 后端

- 表结构设计
- ORM 模型
- case 生成 schema
- prompt 模板
- 切片簇选材
- 多轮执行器
- `TalkApiClient` session 化改造
- 会话评估引擎
- 新 API/任务处理器

### 18.2 前端

- 生成页多轮配置
- 执行进度增强
- 评估详情多轮视图
- 报告页 case/turn 展示

### 18.3 测试

- schema 测试
- 会话执行测试
- 评估指标测试
- 集成回归测试

## 19. 一句话版本

- 先做"后端会话级能力"，再接"前端业务流"，最后补"报告与导出"，按模块拆分推进最稳。
