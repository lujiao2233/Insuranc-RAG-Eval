# 测试集执行功能开发计划

## 1. 现状分析
当前项目中存在独立的 `api_client.py` 和 `config.py` 脚本，用于模拟与“东吴人寿AI问答系统”的交互（发送验证码、登录、建立SSE连接、获取大模型回答）。
在前端（Vue）的测试集管理页面（`TestSetsView.vue`）中，测试集列表的操作列已经有一个“执行”按钮，但绑定的事件仅为“功能待开发”。
在评估管理页面（`EvaluationsView.vue`）中，当前仅展示“导入”的测试集，自动生成的测试集即使完成了执行，也不会默认显示在该页面。

## 2. 目标与需求
1. 点击测试集页面的“执行”按钮，弹窗展示：手机号、验证码（右侧附带发送验证码按钮）、BOT_ID三个输入框，底部为“执行”按钮。
2. 输入手机号后点击“发送验证码”，调用后台接口发送验证码。
3. 填入验证码和BOT_ID，点击“执行”后，进入执行进度页面（复用弹窗展示进度条），后台开始逐条读取该测试集的问题，通过API客户端获取大模型回答，并更新到数据库的 `answer`（模型答案）字段。
4. 执行完成后，测试集状态变为“可评估”，并且能够在“评估管理”页面展示，以便后续进行大模型评估。

## 3. 具体修改方案

### 3.1 后端服务层改造
- **迁移并适配API客户端**：
  - 将 `/workspace/api_client.py` 移动至 `backend/services/api_client.py`。
  - 将 `/workspace/config.py` 移动至 `backend/services/api_config.py`（避免与现有的config目录冲突）。
  - 修改 `TalkApiClient` 的 `__init__` 方法，使其接收 `mobile` 和 `bot_id` 参数，而非从配置文件写死读取。
  - 移除原脚本中用于本地测试的 `if __name__ == "__main__":` 代码块。

### 3.2 后端接口层改造 (`backend/api/routers/testsets.py`)
- **新增发送验证码接口**：`POST /{testset_id}/execution/send-code`
  - 接收 `mobile` 参数，实例化 `TalkApiClient` 并调用 `send_verify_code()`。
- **新增执行测试集接口**：`POST /{testset_id}/execution/start`
  - 接收 `mobile`, `verify_code`, `bot_id`。
  - 实例化 `TalkApiClient` 并调用 `phone_login(verify_code)` 进行验证。
  - 验证成功后，使用现有的 `task_manager.create_task` 创建一个异步后台任务（类型如 `execute_testset`）。
- **新增后台执行任务函数 `_run_execution_task`**：
  - 在后台线程中运行，获取该测试集下的所有无答案或需重新执行的 `Question`。
  - 遍历问题，调用 `TalkApiClient.chat_with_answer_with_status(question.question)`。
  - 将获取到的 `answer` 更新到数据库的 `Question.answer` 字段。
  - 实时更新任务进度（`task_manager.update_progress`）和日志。

### 3.3 前端接口定义 (`frontend/src/api/testsets.ts`)
- 添加 `sendExecutionVerifyCode(testsetId, data: { mobile: string })`。
- 添加 `startExecution(testsetId, data: { mobile: string, verify_code: string, bot_id: string })`，返回 `task_id`。

### 3.4 前端页面改造
- **`TestSetsView.vue` (测试集管理页面)**：
  - 新增执行配置弹窗 `showExecutionDialog` 及对应的表单数据绑定 (`mobile`, `verifyCode`, `botId`)。
  - 实现“发送验证码”按钮逻辑，附带60秒倒计时功能。
  - 实现“执行”按钮逻辑，调用 `startExecution` 接口获取 `task_id`，随后将弹窗内容切换为进度条展示。
  - 实现针对执行任务的轮询函数 `pollExecutionTaskStatus`，实时更新进度条。执行完毕后提示成功并刷新列表。
- **`EvaluationsView.vue` (评估管理页面)**：
  - 修改测试集列表的过滤逻辑：不仅展示导入的测试集（`isUploadedTestset`），同时展示已具备评估条件（`can_evaluate === true`）的测试集。
  - 这样执行完毕的测试集就能顺利出现在评估页面中。

## 4. 假设与决策
- **决策**：执行进度的展示方式采用在当前页面的弹窗内展示进度条（与生成测试集时的交互保持一致），不进行整体页面路由跳转，以提供连贯的用户体验。
- **决策**：为了确保安全性，每次执行都需要用户输入验证码登录并获取 Token。后台服务将在执行任务的生命周期内持有该 Token。
- **假设**：大模型回答接口 `/talk/chat` 在后台并发调用时可能存在频率限制，因此任务处理时将采用串行（逐条发送）方式执行。

## 5. 验证步骤
1. 在前端测试集页面点击“执行”，检查弹窗渲染是否正确。
2. 输入手机号，点击发送验证码，检查手机是否收到短信。
3. 输入验证码和BOT_ID，点击执行，检查进度条是否开始滚动，后台日志是否显示逐条调用模型API。
4. 执行完成后，查看该测试集详情，确认所有问题的“模型答案”字段已成功填充。
5. 切换到“评估管理”页面，确认该测试集出现在列表中，并且状态为“可评估”。