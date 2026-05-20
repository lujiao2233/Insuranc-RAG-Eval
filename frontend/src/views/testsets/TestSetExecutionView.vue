<template>
  <div class="page testset-execution-page">
    <el-page-header @back="$router.push('/testsets')" class="section">
      <template #content>
        <span class="page-title">执行测试集</span>
      </template>
    </el-page-header>

    <el-card shadow="never" class="section">
      <template #header>
        <div class="card-header">
          <span class="card-title">执行配置</span>
          <el-tag v-if="testset" type="info">{{ testset.name }}</el-tag>
        </div>
      </template>

      <el-form v-if="!executing && !executionComplete" :model="executionForm" label-width="100px" style="max-width: 680px;">
        <el-alert
          v-if="skipAnswered"
          title="补执行模式：将跳过已有答案的问题，仅执行空答案的问题"
          type="warning"
          :closable="false"
          show-icon
          style="margin-bottom: 16px;"
        />
        <el-form-item label="手机号" required>
          <el-input v-model="executionForm.mobile" placeholder="请输入手机号" />
        </el-form-item>
        <el-form-item label="验证码" required>
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="16">
              <el-input v-model="executionForm.verifyCode" placeholder="请输入验证码" />
            </el-col>
            <el-col :span="8">
              <el-button type="primary" :disabled="countdown > 0" @click="handleSendVerifyCode" style="width: 100%">
                {{ countdown > 0 ? `${countdown}s 后重发` : '发送验证码' }}
              </el-button>
            </el-col>
          </el-row>
        </el-form-item>
        <el-form-item label="BOT_ID" required>
          <el-input v-model="executionForm.botId" placeholder="例如: 1018" />
          <div class="form-help">说明: 1038 东吴宝典标签，1042 东吴宝典工作流，1018 东吴宝典，1043 问综合工作流</div>
        </el-form-item>
        <el-form-item label="API路径">
          <el-radio-group v-model="executionForm.apiType">
            <el-radio-button label="default">默认路径</el-radio-button>
            <el-radio-button label="dwtsbuddy">dwtsbuddy路径</el-radio-button>
          </el-radio-group>
          <div class="form-help">
            <template v-if="executionForm.apiType === 'default'">
              SSE: /talk/createSse | 对话: /talk/chat
            </template>
            <template v-else>
              SSE: /dwtsbuddy/chat/sse | 对话: /dwtsbuddy/chat
            </template>
          </div>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="handleStartExecution">开始执行</el-button>
        </el-form-item>
      </el-form>

      <div v-if="executing || executionComplete || executionFailed" class="progress-section">
        <el-progress :percentage="executionPercentage" :status="executionProgressStatus" :stroke-width="20" />
        <div class="progress-info">
          <span>当前阶段: {{ executionInfo.stage }}</span>
          <span>{{ executionInfo.current }}/{{ executionInfo.total }}</span>
        </div>
        <div v-if="isConversationMode" class="conversation-progress-info">
          <el-tag size="small" type="info">Case {{ executionInfo.currentCase || 0 }}/{{ executionInfo.totalCases || 0 }}</el-tag>
          <el-tag size="small" :type="executionInfo.currentTurn ? 'warning' : 'info'">Turn {{ executionInfo.currentTurn || 0 }}</el-tag>
          <el-tag v-if="executionInfo.sessionId" size="small" type="success">Session {{ executionInfo.sessionIdShort }}</el-tag>
        </div>
        <div v-if="executionInfo.logs.length > 0" class="progress-logs">
          <div v-for="(log, idx) in executionInfo.logs.slice(-10)" :key="idx" class="log-item">
            {{ log }}
          </div>
        </div>
        <div v-if="isConversationMode && conversationSummaries.length > 0" class="conversation-results">
          <div class="conversation-results-title">多轮会话结果</div>
          <el-collapse>
            <el-collapse-item
              v-for="caseSummary in conversationSummaries"
              :key="caseSummary.caseId"
              :title="`Case ${caseSummary.caseIndex} · ${caseSummary.turns.length} 轮`"
              :name="caseSummary.caseId"
            >
              <div class="conversation-case-meta">
                <el-tag size="small" type="info">状态: {{ caseSummary.statusText }}</el-tag>
              </div>
              <div v-for="turn in caseSummary.turns" :key="turn.turnId" class="conversation-turn-card">
                <div class="turn-header">
                  <span>Turn {{ turn.turnIndex }}</span>
                  <el-tag size="small" :type="getTurnStatusTagType(turn.turnStatus)">{{ turn.turnStatusText }}</el-tag>
                </div>
                <div class="turn-block">
                  <div class="block-label">问题</div>
                  <div class="block-text">{{ turn.question }}</div>
                </div>
                <div class="turn-block" v-if="turn.answer">
                  <div class="block-label">模型回答</div>
                  <div class="block-text">{{ turn.answer }}</div>
                </div>
                <div class="turn-meta">
                  <span v-if="turn.sessionId">Session: {{ turn.sessionId }}</span>
                  <span v-if="turn.refs">Refs: {{ turn.refs }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
        <div v-if="executionComplete || executionFailed" style="margin-top: 12px;">
          <el-button @click="$router.push('/testsets')">返回测试集列表</el-button>
          <el-button v-if="testset" type="primary" @click="goToTestsetDetail">
            {{ isConversationMode ? '查看执行结果' : '查看测试集详情' }}
          </el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { testsetApi } from '@/api/testsets'
import { useTaskStore } from '@/stores/task'
import type { TestSet, ConversationTurnResult } from '@/types'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const testset = ref<TestSet | null>(null)
const executionTestsetId = ref<string | null>(null)
const executionId = ref<string | null>(null)
const executing = ref(false)
const executionComplete = ref(false)
const executionFailed = ref(false)
const countdown = ref(0)
const skipAnswered = ref(false)
let countdownTimer: number | null = null

const executionForm = reactive({
  mobile: '13141802889',
  verifyCode: '',
  botId: '1018',
  apiType: 'default'
})

const executionInfo = reactive({
  stage: '准备中',
  current: 0,
  total: 1,
  logs: [] as string[],
  currentCase: 0,
  currentTurn: 0,
  totalCases: 0,
  sessionId: '',
  sessionIdShort: ''
})
const taskProgressRatio = ref(0)
const conversationResults = ref<ConversationTurnResult[]>([])

const isConversationMode = computed(() => testset.value?.conversation_mode === 'multi_turn')

const conversationSummaries = computed(() => {
  if (!isConversationMode.value) return []
  const grouped = new Map<string, ConversationTurnResult[]>()
  for (const item of conversationResults.value) {
    const caseId = String(item.case_id || '')
    if (!caseId) continue
    if (!grouped.has(caseId)) grouped.set(caseId, [])
    grouped.get(caseId)!.push(item)
  }

  return Array.from(grouped.entries()).map(([caseId, turns], index) => {
    const sortedTurns = [...turns].sort((a, b) => {
      const ai = Number((a.response_payload as any)?.turn_index || 0)
      const bi = Number((b.response_payload as any)?.turn_index || 0)
      return ai - bi
    })
    const normalizedTurns = sortedTurns.map((item, turnIndex) => ({
      turnId: item.turn_id,
      turnIndex: turnIndex + 1,
      question: String((item.request_payload as any)?.msg || ''),
      answer: String(item.generated_answer || ''),
      refs: String(item.refs || ''),
      sessionId: String(item.session_id_after || item.session_id_before || ''),
      turnStatus: String(item.turn_status || ''),
      turnStatusText: getTurnStatusText(String(item.turn_status || '')),
    }))
    const caseStatus = normalizedTurns.some(turn => turn.turnStatus === 'failed')
      ? 'failed'
      : normalizedTurns.some(turn => turn.turnStatus === 'partial')
        ? 'partial'
        : 'ok'
    return {
      caseId,
      caseIndex: index + 1,
      turns: normalizedTurns,
      status: caseStatus,
      statusText: getTurnStatusText(caseStatus),
    }
  })
})

const executionPercentage = computed(() => {
  if (taskProgressRatio.value > 0) {
    return Math.round(taskProgressRatio.value * 100)
  }
  if (executionInfo.total <= 0) return 0
  return Math.round((executionInfo.current / executionInfo.total) * 100)
})

const executionProgressStatus = computed(() => {
  if (executing.value) return ''
  if (executionFailed.value) return 'exception'
  if (executionPercentage.value >= 100) return 'success'
  return ''
})

const getTurnStatusText = (status: string) => {
  const statusMap: Record<string, string> = {
    ok: '成功',
    partial: '部分成功',
    failed: '失败',
    cancelled: '已取消',
    partial_failed: '部分失败'
  }
  return statusMap[status] || status || '未知'
}

const getTurnStatusTagType = (status: string) => {
  const typeMap: Record<string, string> = {
    ok: 'success',
    partial: 'warning',
    failed: 'danger',
    cancelled: 'info',
    partial_failed: 'warning'
  }
  return typeMap[status] || 'info'
}

const fetchConversationTurnResults = async () => {
  if (!executionId.value) return
  try {
    const response = await testsetApi.getConversationTurnResults(executionId.value)
    conversationResults.value = response.items || []
  } catch (error) {
    console.error('Failed to fetch conversation turn results:', error)
  }
}

const fetchTestset = async () => {
  const id = route.params.id as string
  try {
    testset.value = await testsetApi.getTestSet(id)
  } catch {
    ElMessage.error('获取测试集失败')
  }
}

const handleSendVerifyCode = async () => {
  const id = route.params.id as string
  if (!executionForm.mobile) {
    ElMessage.warning('请输入手机号')
    return
  }
  try {
    await testsetApi.sendExecutionVerifyCode(id, { mobile: executionForm.mobile })
    ElMessage.success('验证码发送成功')
    countdown.value = 60
    countdownTimer = window.setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0 && countdownTimer) {
        window.clearInterval(countdownTimer)
        countdownTimer = null
      }
    }, 1000)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '发送验证码失败')
  }
}

const pollExecutionTaskStatus = (taskId: string) => {
  let lastLogIndex = 0
  const poll = async () => {
    if (!executing.value) return
    try {
      const task = await testsetApi.getTaskStatus(taskId)
      executionInfo.stage = task.message || task.status
      if (typeof task.progress === 'number') {
        taskProgressRatio.value = Math.max(0, Math.min(1, task.progress))
      }
      if (typeof task.total_steps === 'number' && task.total_steps > 0) {
        executionInfo.total = task.total_steps
      }
      if (typeof task.current_step === 'number') {
        executionInfo.current = task.current_step
      }
      const contextInfo = (task.contextInfo || task.context_info || {}) as Record<string, any>
      const currentCase = Number(contextInfo.currentCase ?? contextInfo.current_case ?? 0)
      const currentTurn = Number(contextInfo.currentTurn ?? contextInfo.current_turn ?? 0)
      const totalCases = Number(contextInfo.totalCases ?? contextInfo.total_cases ?? 0)
      const sessionId = String(contextInfo.sessionId ?? contextInfo.session_id ?? '')
      if (testset.value?.conversation_mode === 'multi_turn' && totalCases > 0) {
        executionInfo.currentCase = currentCase
        executionInfo.currentTurn = currentTurn
        executionInfo.totalCases = totalCases
        executionInfo.sessionId = sessionId
        executionInfo.sessionIdShort = sessionId ? sessionId.slice(0, 8) : ''
        executionInfo.stage = currentCase > 0
          ? `正在执行 Case ${currentCase}/${totalCases}${currentTurn > 0 ? `，Turn ${currentTurn}` : ''}${sessionId ? `，Session ${sessionId.slice(0, 8)}` : ''}`
          : (task.message || task.status)
        executionInfo.total = totalCases
        executionInfo.current = currentCase
      }

      // 兜底从阶段文本中提取进度，例如：正在处理第 4/14 题...
      const stageMatch = String(executionInfo.stage).match(/(\d+)\s*\/\s*(\d+)/)
      if (stageMatch) {
        executionInfo.current = parseInt(stageMatch[1], 10)
        executionInfo.total = parseInt(stageMatch[2], 10)
      }

      if (task.logs && task.logs.length > lastLogIndex) {
        const newLogs = task.logs.slice(lastLogIndex)
        for (const log of newLogs) {
          executionInfo.logs.push(log)
          const match = log.match(/(?:处理第\s*|提问\s*\[)(\d+)\s*\/\s*(\d+)/)
          if (match) {
            executionInfo.current = parseInt(match[1], 10)
            executionInfo.total = parseInt(match[2], 10)
            taskStore.updateTask(taskId, {
              progress: Math.round((taskProgressRatio.value || (executionInfo.current / executionInfo.total)) * 100),
              status: 'running',
              message: task.message,
              currentStep: task.current_step ?? undefined,
              totalSteps: task.total_steps ?? undefined,
              contextInfo: totalCases > 0 ? {
                currentCase,
                currentTurn,
                totalCases,
                sessionId
              } : undefined
            })
          }
        }
        lastLogIndex = task.logs.length
      }

      if (task.status === 'finished') {
        executing.value = false
        executionComplete.value = true
        executionInfo.stage = '执行完成'
        executionInfo.current = executionInfo.total
        taskProgressRatio.value = 1
        if (isConversationMode.value) {
          await fetchConversationTurnResults()
        }
        taskStore.updateTask(taskId, { progress: 100, status: 'completed' })
        ElMessage.success('测试集执行完成')
        return
      }

      if (task.status === 'cancelled') {
        executing.value = false
        executionFailed.value = true
        executionInfo.stage = '执行已取消'
        taskStore.updateTask(taskId, { status: 'cancelled', error: task.error || '任务已取消' })
        ElMessage.warning(task.message || '测试集执行已取消')
        return
      }

      if (task.status === 'failed') {
        executing.value = false
        executionFailed.value = true
        executionInfo.stage = '执行失败'
        taskStore.updateTask(taskId, { status: 'failed', error: task.error || '未知错误' })
        ElMessage.error(task.error || '执行失败')
        return
      }

      window.setTimeout(poll, 2000)
    } catch {
      window.setTimeout(poll, 2000)
    }
  }

  poll()
}

const handleStartExecution = async () => {
  const id = route.params.id as string
  if (!executionForm.mobile || !executionForm.verifyCode || !executionForm.botId) {
    ElMessage.warning('请填写完整信息')
    return
  }

  executing.value = true
  executionComplete.value = false
  executionFailed.value = false
  executionInfo.stage = '准备中'
  executionInfo.current = 0
  executionInfo.total = 1
  taskProgressRatio.value = 0
  executionInfo.logs = ['正在启动执行任务...']

  try {
    const isConversation = testset.value?.conversation_mode === 'multi_turn'
    const extraParams: Record<string, any> = {}
    if (skipAnswered.value) {
      extraParams.skip_answered = true
    }
    const response = isConversation
      ? await testsetApi.startConversationExecution(id, {
          mobile: executionForm.mobile,
          verify_code: executionForm.verifyCode,
          bot_id: executionForm.botId,
          api_type: executionForm.apiType,
          ...extraParams
        })
      : await testsetApi.startExecution(id, {
          mobile: executionForm.mobile,
          verify_code: executionForm.verifyCode,
          bot_id: executionForm.botId,
          api_type: executionForm.apiType,
          ...extraParams
        })
    const { task_id, execution_testset_id, execution_id } = response as any
    if (execution_testset_id) {
      executionTestsetId.value = execution_testset_id
    }
    if (execution_id) {
      executionId.value = execution_id
    }

    taskStore.addTask({
      id: task_id,
      name: `${isConversation ? '执行多轮测试集' : '执行测试集'}: ${testset.value?.name || id}`,
      type: isConversation ? 'conversation' : 'testset',
      progress: 0,
      status: 'running',
      targetId: id
    })

    executionInfo.logs.push(`任务已创建: ${task_id}`)
    pollExecutionTaskStatus(task_id)
  } catch (error: any) {
    executing.value = false
    executionFailed.value = true
    executionInfo.stage = '执行失败'
    const errorMsg = error?.response?.data?.detail || error?.message || '未知错误'
    executionInfo.logs.push(`错误: ${errorMsg}`)
    ElMessage.error(errorMsg)
  }
}

const goToTestsetDetail = () => {
  if (!executionTestsetId.value) return
  // 跳转后由 MainLayout 读取该标记并关闭当前执行页标签
  sessionStorage.setItem('pending-close-tag-path', route.path)
  if (isConversationMode.value) {
    router.push(`/testsets/${executionTestsetId.value}`)
    return
  }
  router.push(`/evaluations?focus_testset_id=${executionTestsetId.value}`)
}

onMounted(() => {
  skipAnswered.value = route.query.skip_answered === 'true'
  fetchTestset()
})

onUnmounted(() => {
  if (countdownTimer) {
    window.clearInterval(countdownTimer)
    countdownTimer = null
  }
})
</script>

<style lang="scss" scoped>
.testset-execution-page {
  .page-title {
    font-size: var(--font-20, 20px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .card-title {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .form-help {
    font-size: var(--font-12, 12px);
    color: var(--text-2, #909399);
    margin-top: 4px;
    line-height: 1.4;
  }

  .progress-section {
    .conversation-progress-info {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      margin-top: 12px;
    }

    .progress-info {
      display: flex;
      justify-content: space-between;
      margin-top: 10px;
      font-size: var(--font-14, 14px);
      color: var(--text-2, #606266);
    }

    .progress-logs {
      margin-top: 15px;
      max-height: 220px;
      overflow-y: auto;
      background: var(--bg-app, #f5f7fa);
      padding: 10px;
      border-radius: var(--radius-8, 8px);
      font-size: var(--font-12, 12px);
      color: var(--text-1, #303133);

      .log-item {
        padding: 4px 0;
        border-bottom: 1px solid var(--border-1, #ebeef5);

        &:last-child {
          border-bottom: none;
        }
      }
    }

    .conversation-results {
      margin-top: 16px;

      .conversation-results-title {
        font-size: var(--font-14, 14px);
        font-weight: var(--fw-600, 600);
        color: var(--text-1, #303133);
        margin-bottom: 12px;
      }

      .conversation-case-meta {
        margin-bottom: 12px;
      }

      .conversation-turn-card {
        border: 1px solid var(--border-1, #ebeef5);
        border-radius: var(--radius-8, 8px);
        padding: 12px;
        background: var(--bg-card, #fff);
        margin-bottom: 12px;
      }

      .turn-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        font-size: var(--font-14, 14px);
        color: var(--text-1, #303133);
        font-weight: var(--fw-600, 600);
      }

      .turn-block {
        margin-bottom: 10px;

        .block-label {
          font-size: var(--font-12, 12px);
          color: var(--text-2, #909399);
          margin-bottom: 4px;
        }

        .block-text {
          font-size: var(--font-14, 14px);
          color: var(--text-1, #303133);
          line-height: 1.6;
          white-space: pre-wrap;
          word-break: break-word;
        }
      }

      .turn-meta {
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        font-size: var(--font-12, 12px);
        color: var(--text-2, #909399);
      }
    }
  }
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid var(--border-1, #ebeef5);
}

:deep(.el-card) {
  border-radius: var(--radius-8, 8px);
}
</style>
