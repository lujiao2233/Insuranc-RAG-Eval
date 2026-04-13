<template>
  <div class="evaluation-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">评估详情</span>
      </template>
    </el-page-header>
    
    <el-divider />
    
    <template v-if="evaluation">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-card>
            <template #header>
              <span>评估信息</span>
            </template>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="评估ID">{{ evaluation.id }}</el-descriptions-item>
              <el-descriptions-item label="评估方法">{{ evaluation.evaluation_method }}</el-descriptions-item>
              <el-descriptions-item label="问题总数">{{ evaluation.total_questions }}</el-descriptions-item>
              <el-descriptions-item label="已评估">{{ evaluation.evaluated_questions }}</el-descriptions-item>
              <el-descriptions-item label="状态">
                <el-tag :type="getStatusType(evaluation.status)">
                  {{ getStatusText(evaluation.status) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="耗时">
                {{ evaluation.evaluation_time ? formatDuration(evaluation.evaluation_time) : '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDateTime(evaluation.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="更新时间">
                {{ evaluation.updated_at ? formatDateTime(evaluation.updated_at) : '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-card>
          
          <el-card class="mt-4" v-if="evaluation.status === 'running'">
            <template #header>
              <span>评估进度</span>
            </template>
            <el-progress
              :percentage="taskProgress"
              :status="taskProgress === 100 ? 'success' : undefined"
            />
            <div class="progress-info mt-2">
              <span>已评估: {{ taskEvaluated }} / {{ evaluation.total_questions }}</span>
            </div>
          </el-card>
          
          <el-card class="mt-4" v-if="evaluation.overall_metrics">
            <template #header>
              <span>评估指标</span>
            </template>
            <div class="metrics-chart" ref="chartRef"></div>
          </el-card>
          
          <el-card class="mt-4" v-if="results.length > 0">
            <template #header>
              <span>评估结果</span>
            </template>
            <el-table :data="results" style="width: 100%">
              <el-table-column type="expand">
                <template #default="{ row }">
                  <div class="expand-content">
                    <div class="expand-section">
                      <h4>问题</h4>
                      <p class="section-text">{{ row.question_text }}</p>
                    </div>
                    
                    <div class="expand-section" v-if="row.question_type || row.category_major || row.category_minor">
                      <h4>问题类型</h4>
                      <div class="tag-group">
                        <el-tag v-if="row.category_major" size="small" type="info">{{ row.category_major }}</el-tag>
                        <el-tag v-if="row.category_minor" size="small" type="warning">{{ row.category_minor }}</el-tag>
                        <el-tag v-if="row.question_type && !row.category_minor" size="small">{{ row.question_type }}</el-tag>
                      </div>
                    </div>
                    
                    <div class="expand-section" v-if="row.generated_answer">
                      <h4>模型答案</h4>
                      <p class="section-text">{{ row.generated_answer }}</p>
                    </div>
                    
                    <div class="expand-section" v-if="row.context">
                      <h4>文档切片</h4>
                      <p class="section-text context-text">{{ row.context }}</p>
                    </div>
                    
                    <div class="expand-section">
                      <h4>打分依据</h4>
                      <div v-if="row.reasons && Object.keys(row.reasons).length > 0" class="reasons-list">
                        <div v-for="(reason, metricName) in row.reasons" :key="metricName" class="reason-item">
                          <el-tag size="small" type="info">{{ getMetricName(metricName as string) }}</el-tag>
                          <p class="reason-text">{{ reason }}</p>
                        </div>
                      </div>
                      <el-empty v-else description="暂无打分依据" :image-size="60" />
                    </div>
                  </div>
                </template>
              </el-table-column>
              <el-table-column prop="question_text" label="问题" min-width="200">
                <template #default="{ row }">
                  <el-text truncated>{{ row.question_text }}</el-text>
                </template>
              </el-table-column>
              <el-table-column label="指标" width="300">
                <template #default="{ row }">
                  <div v-if="row.metrics" class="metrics-cell">
                    <el-tag
                      v-for="(value, key) in row.metrics"
                      :key="key"
                      :type="getMetricType(value)"
                      size="small"
                      class="mr-1"
                    >
                      {{ getMetricName(key as string) }}: {{ value.toFixed(3) }}
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
      </el-row>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Document, Download, Delete } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { useTaskStore } from '@/stores/task'
import { evaluationApi } from '@/api/evaluations'
import { formatDateTime, formatDuration } from '@/utils/format'
import type { Evaluation, EvaluationResult } from '@/types'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const loading = ref(false)
const evaluation = ref<Evaluation | null>(null)
const results = ref<EvaluationResult[]>([])
const taskProgress = ref(0)
const taskEvaluated = ref(0)
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
let pollingTimer: number | null = null

const updateEvaluationTaskStatus = (evaluationId: string, updates: { progress?: number; status?: 'running' | 'completed' | 'failed'; error?: string }) => {
  // 兼容两种任务ID：task_id 或 evaluation_id
  const byTaskId = taskStore.getTask(evaluationId)
  if (byTaskId) {
    taskStore.updateTask(evaluationId, updates)
    return
  }
  const byTarget = taskStore.tasks.find(task => task.type === 'evaluation' && task.targetId === evaluationId)
  if (byTarget) {
    taskStore.updateTask(byTarget.id, updates)
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    completed: 'success',
    running: 'warning',
    pending: 'info',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    completed: '已完成',
    running: '执行中',
    pending: '待处理',
    failed: '失败'
  }
  return texts[status] || status
}

const getMetricType = (value: number) => {
  if (value >= 0.8) return 'success'
  if (value >= 0.6) return 'warning'
  return 'danger'
}

const getMetricName = (key: string): string => {
  const metricNames: Record<string, string> = {
    answer_relevance: '答案相关性',
    context_relevance: '上下文相关性',
    faithfulness: '忠实度',
    answer_correctness: '答案正确性',
    answer_similarity: '答案相似度',
    context_precision: '上下文精确度',
    context_recall: '上下文召回率',
    ragas_score: '综合评分',
    overall_score: '综合评分',
    total: '总分',
    score: '得分',
    overall: '总体',
    average: '平均值'
  }
  return metricNames[key] || key
}

const fetchEvaluation = async () => {
  const id = route.params.id as string
  loading.value = true
  
  try {
    evaluation.value = await evaluationApi.getEvaluation(id)
    
    if (evaluation.value.status === 'completed') {
      await fetchResults()
      await nextTick()
      initChart()
    } else if (evaluation.value.status === 'running') {
      startPolling()
    }
  } catch (error) {
    ElMessage.error('获取评估详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const fetchResults = async () => {
  if (!evaluation.value) return
  
  try {
    const response = await evaluationApi.getEvaluationResults(evaluation.value.id)
    results.value = response.items
  } catch (error) {
    console.error('Failed to fetch results:', error)
  }
}

const startPolling = async () => {
  if (!evaluation.value) return
  
  const poll = async () => {
    try {
      const latest = await evaluationApi.getEvaluation(evaluation.value!.id)
      evaluation.value = latest
      taskEvaluated.value = latest.evaluated_questions || 0
      taskProgress.value = latest.total_questions
        ? Math.min(100, Math.round((taskEvaluated.value / latest.total_questions) * 100))
        : 0

      // 尝试更新全局任务进度 (如果有的话)
      // 如果 evaluation 创建时关联了 task_id，可以更新。如果没存 task_id，退而求其次更新状态。
      updateEvaluationTaskStatus(latest.id, {
        progress: taskProgress.value,
        status: 'running'
      })

      if (latest.status === 'completed') {
        stopPolling()
        
        updateEvaluationTaskStatus(latest.id, {
          progress: 100,
          status: 'completed'
        })

        await fetchResults()
        await nextTick()
        initChart()
      } else if (latest.status === 'failed') {
        stopPolling()
        
        updateEvaluationTaskStatus(latest.id, {
          status: 'failed',
          error: latest.error_message || '评估失败'
        })

        ElMessage.error(latest.error_message || '评估失败')
      }
    } catch (error) {
      console.error('Polling error:', error)
    }
  }
  
  await poll()
  pollingTimer = window.setInterval(poll, 3000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const initChart = () => {
  if (!chartRef.value || !evaluation.value?.overall_metrics) return
  
  chartInstance = echarts.init(chartRef.value)
  
  const metrics = evaluation.value.overall_metrics
  const data = Object.entries(metrics).map(([key, value]) => {
    const mean = typeof value === 'object' && value !== null && 'mean' in value 
      ? (value as any).mean 
      : value
    return {
      name: getMetricName(key),
      value: typeof mean === 'number' ? mean : 0
    }
  })
  
  const option = {
    tooltip: {
      trigger: 'item'
    },
    radar: {
      indicator: data.map(item => ({
        name: item.name,
        max: 1
      })),
      center: ['50%', '50%'],
      radius: '60%'
    },
    series: [{
      type: 'radar',
      data: [{
        value: data.map(item => item.value),
        name: '评估指标',
        areaStyle: {
          color: 'rgba(64, 158, 255, 0.3)'
        }
      }]
    }]
  }
  
  chartInstance.setOption(option)
}

onMounted(() => {
  fetchEvaluation()
})

onUnmounted(() => {
  stopPolling()
  chartInstance?.dispose()
})
</script>

<style lang="scss" scoped>
.evaluation-detail {
  .metrics-chart {
    width: 100%;
    height: 300px;
  }
  
  .metrics-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .progress-info {
    color: #909399;
    font-size: 14px;
  }

  .expand-content {
    padding: 20px;
    background-color: #fafafa;

    .expand-section {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      h4 {
        margin: 0 0 8px 0;
        font-size: 14px;
        font-weight: 600;
        color: #303133;
      }

      .section-text {
        margin: 0;
        color: #606266;
        font-size: 14px;
        line-height: 1.6;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .context-text {
        background-color: #f5f7fa;
        padding: 12px;
        border-radius: 4px;
        max-height: 200px;
        overflow-y: auto;
      }

      .tag-group {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }

      .reasons-list {
        .reason-item {
          margin-bottom: 12px;

          &:last-child {
            margin-bottom: 0;
          }

          .el-tag {
            margin-bottom: 4px;
          }

          .reason-text {
            margin: 0;
            color: #606266;
            font-size: 14px;
            line-height: 1.5;
          }
        }
      }
    }
  }

  .mt-2 {
    margin-top: 0.5rem;
  }

  .mt-4 {
    margin-top: 1.5rem;
  }
}
</style>
