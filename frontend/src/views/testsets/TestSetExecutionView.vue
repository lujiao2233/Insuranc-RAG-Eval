<template>
  <div class="testset-execution-view">
    <el-page-header @back="$router.push('/testsets')">
      <template #content>
        <span class="text-large font-600">执行测试集</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card>
      <template #header>
        <div class="card-header">
          <span>执行配置</span>
          <el-tag v-if="testset" type="info">{{ testset.name }}</el-tag>
        </div>
      </template>

      <el-form v-if="!executing && !executionComplete" :model="executionForm" label-width="100px" style="max-width: 680px;">
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
        <div v-if="executionInfo.logs.length > 0" class="progress-logs">
          <div v-for="(log, idx) in executionInfo.logs.slice(-10)" :key="idx" class="log-item">
            {{ log }}
          </div>
        </div>
        <div v-if="executionComplete || executionFailed" style="margin-top: 12px;">
          <el-button @click="$router.push('/testsets')">返回测试集列表</el-button>
          <el-button v-if="testset" type="primary" @click="$router.push(`/testsets/${testset.id}`)">查看测试集详情</el-button>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { testsetApi } from '@/api/testsets'
import { useTaskStore } from '@/stores/task'
import type { TestSet } from '@/types'

const route = useRoute()
const taskStore = useTaskStore()

const testset = ref<TestSet | null>(null)
const executing = ref(false)
const executionComplete = ref(false)
const executionFailed = ref(false)
const countdown = ref(0)
let countdownTimer: number | null = null

const executionForm = reactive({
  mobile: '13141802889',
  verifyCode: '',
  botId: '1018'
})

const executionInfo = reactive({
  stage: '准备中',
  current: 0,
  total: 1,
  logs: [] as string[]
})

const executionPercentage = computed(() => {
  if (executionInfo.total === 0) return 0
  return Math.round((executionInfo.current / executionInfo.total) * 100)
})

const executionProgressStatus = computed(() => {
  if (executing.value) return ''
  if (executionFailed.value) return 'exception'
  if (executionPercentage.value >= 100) return 'success'
  return ''
})

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

      if (task.logs && task.logs.length > lastLogIndex) {
        const newLogs = task.logs.slice(lastLogIndex)
        for (const log of newLogs) {
          executionInfo.logs.push(log)
          const match = log.match(/处理第\s*(\d+)\/(\d+)\s*题/)
          if (match) {
            executionInfo.current = parseInt(match[1], 10)
            executionInfo.total = parseInt(match[2], 10)
            taskStore.updateTask(taskId, {
              progress: Math.round((executionInfo.current / executionInfo.total) * 100),
              status: 'running'
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
        taskStore.updateTask(taskId, { progress: 100, status: 'completed' })
        ElMessage.success('测试集执行完成')
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
  executionInfo.logs = ['正在启动执行任务...']

  try {
    const { task_id } = await testsetApi.startExecution(id, {
      mobile: executionForm.mobile,
      verify_code: executionForm.verifyCode,
      bot_id: executionForm.botId
    })

    taskStore.addTask({
      id: task_id,
      name: `执行测试集: ${testset.value?.name || id}`,
      type: 'testset',
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

onMounted(() => {
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
.testset-execution-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .form-help {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    line-height: 1.4;
  }

  .progress-section {
    .progress-info {
      display: flex;
      justify-content: space-between;
      margin-top: 10px;
      font-size: 14px;
      color: #606266;
    }

    .progress-logs {
      margin-top: 15px;
      max-height: 220px;
      overflow-y: auto;
      background: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      font-size: 12px;

      .log-item {
        padding: 4px 0;
        border-bottom: 1px solid #ebeef5;

        &:last-child {
          border-bottom: none;
        }
      }
    }
  }
}
</style>
