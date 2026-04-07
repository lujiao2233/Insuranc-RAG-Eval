<template>
  <div class="evaluation-progress">
    <div class="progress-header">
      <div class="header-left">
        <el-tag :type="statusTagType" size="large">
          {{ statusText }}
        </el-tag>
        <span v-if="estimatedTime" class="estimated-time">
          预计剩余: {{ formatDuration(estimatedTime) }}
        </span>
      </div>
      <div class="header-right">
        <el-button
          v-if="canCancel"
          type="danger"
          size="small"
          @click="handleCancel"
        >
          取消评估
        </el-button>
        <el-button
          v-if="canRetry"
          type="primary"
          size="small"
          @click="handleRetry"
        >
          重新评估
        </el-button>
      </div>
    </div>

    <div class="progress-main">
      <el-progress
        :percentage="displayProgress"
        :status="progressStatus"
        :stroke-width="24"
        :show-text="true"
        :format="progressFormat"
      />
    </div>

    <div class="progress-stats">
      <div class="stat-item">
        <span class="stat-label">已评估</span>
        <span class="stat-value">{{ evaluatedCount }} / {{ totalCount }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">耗时</span>
        <span class="stat-value">{{ formatDuration(elapsedTime) }}</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">成功率</span>
        <span class="stat-value">{{ successRate }}%</span>
      </div>
      <div class="stat-item">
        <span class="stat-label">平均耗时</span>
        <span class="stat-value">{{ formatDuration(avgTime) }}/题</span>
      </div>
    </div>

    <div v-if="showLogs && logs.length > 0" class="progress-logs">
      <div class="logs-header">
        <span>执行日志</span>
        <el-button text size="small" @click="toggleLogs">
          {{ logsExpanded ? '收起' : '展开' }}
        </el-button>
      </div>
      <el-collapse-transition>
        <div v-show="logsExpanded" class="logs-content">
          <div
            v-for="(log, index) in displayLogs"
            :key="index"
            class="log-item"
            :class="log.type"
          >
            <span class="log-time">{{ log.time }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </div>
      </el-collapse-transition>
    </div>

    <div v-if="error" class="progress-error">
      <el-alert
        :title="error"
        type="error"
        show-icon
        :closable="false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue'
import { usePolling } from '@/composables/usePolling'
import type { TaskStatus } from '@/types/models'

interface LogItem {
  time: string
  message: string
  type: 'info' | 'success' | 'warning' | 'error'
}

interface Props {
  taskId: string
  status?: 'pending' | 'running' | 'completed' | 'failed'
  progress?: number
  totalCount?: number
  evaluatedCount?: number
  elapsedTime?: number
  logs?: string[]
  error?: string
  showLogs?: boolean
  pollingInterval?: number
  onComplete?: (result: any) => void
  onError?: (error: Error) => void
}

const props = withDefaults(defineProps<Props>(), {
  status: 'pending',
  progress: 0,
  totalCount: 0,
  evaluatedCount: 0,
  elapsedTime: 0,
  logs: () => [],
  showLogs: true,
  pollingInterval: 2000
})

const emit = defineEmits<{
  (e: 'update:status', status: TaskStatus): void
  (e: 'complete', result: any): void
  (e: 'error', error: Error): void
  (e: 'cancel'): void
  (e: 'retry'): void
}>()

const logsExpanded = ref(true)
const startTime = ref(Date.now())
const localElapsedTime = ref(0)

const statusText = computed(() => {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '评估中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[props.status] || props.status
})

const statusTagType = computed(() => {
  const types: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[props.status] || 'info'
})

const progressStatus = computed(() => {
  if (props.status === 'completed') return 'success'
  if (props.status === 'failed') return 'exception'
  return undefined
})

const displayProgress = computed(() => {
  if (props.status === 'completed') return 100
  if (props.status === 'failed') return props.progress
  return Math.min(99, props.progress)
})

const canCancel = computed(() => props.status === 'running')
const canRetry = computed(() => props.status === 'failed')

const successRate = computed(() => {
  if (props.evaluatedCount === 0) return 100
  return Math.round((props.evaluatedCount / props.totalCount) * 100)
})

const avgTime = computed(() => {
  if (props.evaluatedCount === 0) return 0
  return Math.round(props.elapsedTime / props.evaluatedCount)
})

const estimatedTime = computed(() => {
  if (props.status !== 'running' || props.evaluatedCount === 0) return 0
  const remaining = props.totalCount - props.evaluatedCount
  return remaining * avgTime.value
})

const displayLogs = computed((): LogItem[] => {
  return props.logs.map((log, index) => {
    let type: LogItem['type'] = 'info'
    if (log.includes('成功') || log.includes('完成')) type = 'success'
    if (log.includes('警告') || log.includes('跳过')) type = 'warning'
    if (log.includes('错误') || log.includes('失败')) type = 'error'

    return {
      time: formatTime(Date.now() - (props.logs.length - index) * 1000),
      message: log,
      type
    }
  })
})

const progressFormat = (percentage: number) => {
  if (props.status === 'completed') return '完成'
  if (props.status === 'failed') return '失败'
  return `${percentage}%`
}

const formatDuration = (seconds: number) => {
  if (!seconds || seconds <= 0) return '0秒'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}时${minutes}分${secs}秒`
  }
  if (minutes > 0) {
    return `${minutes}分${secs}秒`
  }
  return `${secs}秒`
}

const formatTime = (timestamp: number) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const toggleLogs = () => {
  logsExpanded.value = !logsExpanded.value
}

const handleCancel = () => {
  emit('cancel')
}

const handleRetry = () => {
  emit('retry')
}

const fetchTaskStatus = async () => {
  emit('update:status', {
    task_id: props.taskId,
    status: props.status,
    progress: props.progress,
    logs: props.logs
  } as TaskStatus)
}

const { start, stop } = usePolling(fetchTaskStatus, props.pollingInterval, {
  immediate: props.status === 'running'
})

watch(() => props.status, (newStatus) => {
  if (newStatus === 'running') {
    start()
  } else {
    stop()
  }

  if (newStatus === 'completed') {
    emit('complete', { taskId: props.taskId })
  } else if (newStatus === 'failed') {
    emit('error', new Error(props.error || '评估失败'))
  }
})

let timer: number | null = null
if (props.status === 'running') {
  timer = window.setInterval(() => {
    localElapsedTime.value = Math.floor((Date.now() - startTime.value) / 1000)
  }, 1000)
}

onUnmounted(() => {
  stop()
  if (timer) {
    clearInterval(timer)
  }
})

defineExpose({
  start,
  stop
})
</script>

<style lang="scss" scoped>
.evaluation-progress {
  padding: 24px;
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

  .progress-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .estimated-time {
        font-size: 14px;
        color: #909399;
      }
    }

    .header-right {
      display: flex;
      gap: 8px;
    }
  }

  .progress-main {
    margin-bottom: 24px;

    :deep(.el-progress__text) {
      font-size: 16px !important;
      font-weight: 600;
    }
  }

  .progress-stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;

    .stat-item {
      text-align: center;
      padding: 16px;
      background-color: #f5f7fa;
      border-radius: 8px;

      .stat-label {
        display: block;
        font-size: 12px;
        color: #909399;
        margin-bottom: 8px;
      }

      .stat-value {
        display: block;
        font-size: 20px;
        font-weight: 600;
        color: #303133;
      }
    }
  }

  .progress-logs {
    margin-bottom: 16px;

    .logs-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 16px;
      background-color: #f5f7fa;
      border-radius: 4px 4px 0 0;
      font-weight: 500;
      color: #606266;
    }

    .logs-content {
      max-height: 200px;
      overflow-y: auto;
      border: 1px solid #ebeef5;
      border-top: none;
      border-radius: 0 0 4px 4px;

      .log-item {
        display: flex;
        padding: 8px 16px;
        border-bottom: 1px solid #ebeef5;
        font-size: 13px;

        &:last-child {
          border-bottom: none;
        }

        .log-time {
          flex-shrink: 0;
          width: 80px;
          color: #909399;
          font-family: monospace;
        }

        .log-message {
          flex: 1;
          color: #606266;
        }

        &.success .log-message {
          color: #67c23a;
        }

        &.warning .log-message {
          color: #e6a23c;
        }

        &.error .log-message {
          color: #f56c6c;
        }
      }
    }
  }

  .progress-error {
    margin-top: 16px;
  }
}

@media (max-width: 768px) {
  .evaluation-progress {
    .progress-stats {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}
</style>
