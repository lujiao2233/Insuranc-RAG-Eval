<template>
  <div class="page evaluation-detail-page" v-loading="loading">
    <el-page-header @back="$router.back()" class="section">
      <template #content>
        <span class="page-title">评估详情</span>
      </template>
    </el-page-header>
    
    <template v-if="evaluation">
      <el-row :gutter="24">
        <el-col :span="24">
          <el-card shadow="never" class="section">
            <template #header>
              <span class="card-title">评估信息</span>
            </template>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="测试集名称">{{ testsetName }}</el-descriptions-item>
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
              <el-descriptions-item label="创建时间">{{ formatDateTime(evaluation.created_at || evaluation.timestamp) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
          
          <el-card class="section" shadow="never" v-if="evaluation.status === 'failed'">
            <template #header>
              <span class="card-title">评估失败</span>
            </template>
            <el-alert
              :title="evaluation.error_message || '评估任务执行失败'"
              type="error"
              :closable="false"
              show-icon
              class="error-alert"
            >
              <template #default>
                <div class="error-details">
                  <p>评估任务在执行过程中遇到错误，已终止执行。</p>
                  <p>请检查测试集数据、系统配置或联系管理员。</p>
                </div>
              </template>
            </el-alert>
            <div class="error-actions">
              <el-button type="primary" @click="handleRetry">重新评估</el-button>
              <el-button @click="$router.back()">返回列表</el-button>
            </div>
          </el-card>
          
          <el-card class="section" shadow="never" v-if="evaluation.status === 'running'">
            <template #header>
              <span class="card-title">评估进度</span>
            </template>
            <el-progress
              :percentage="taskProgress"
              :status="taskProgress === 100 ? 'success' : undefined"
            />
            <div class="progress-info mt-2">
              <span>已评估: {{ taskEvaluated }} / {{ evaluation.total_questions }}</span>
            </div>
          </el-card>
          
          <el-card class="section" shadow="never" v-if="evaluation.overall_metrics">
            <template #header>
              <span class="card-title">评估指标</span>
            </template>
            <div class="metrics-section-title">质量指标（越高越好）</div>
            <div v-if="qualityOverviewMetrics.length > 0" class="metrics-chart section-sm" ref="chartRef"></div>
            <el-empty v-else description="暂无质量指标" :image-size="60" class="section-sm" />
            <div class="metrics-section-title">安全指标（越低越好）</div>
            <div v-if="safetyOverviewMetrics.length > 0" class="metrics-cell">
              <el-tag
                v-for="item in safetyOverviewMetrics"
                :key="item.key"
                :type="getMetricType(item.key, item.value)"
                size="small"
                class="mr-1"
              >
                {{ getMetricName(item.key) }}: {{ item.value.toFixed(3) }}
              </el-tag>
            </div>
            <el-empty v-else description="暂无安全指标" :image-size="60" />
          </el-card>
          
          <el-card class="section" shadow="never" v-if="results.length > 0">
            <template #header>
              <span class="card-title">评估结果</span>
            </template>
            <el-table :data="results" style="width: 100%" size="small">
              <el-table-column type="expand">
                <template #default="{ row }">
                  <div class="expand-content">
                    <div class="expand-section">
                      <h4><el-icon><QuestionFilled /></el-icon>问题</h4>
                      <p class="section-text">{{ row.question_text }}</p>
                    </div>
                    
                    <div class="expand-section" v-if="row.question_type || row.category_major || row.category_minor">
                      <h4><el-icon><List /></el-icon>问题类型</h4>
                      <div class="tag-group">
                        <el-tag v-if="row.category_major" size="small" type="info">{{ row.category_major }}</el-tag>
                        <el-tag v-if="row.category_minor" size="small" type="warning">{{ row.category_minor }}</el-tag>
                        <el-tag v-if="row.question_type && !row.category_minor" size="small">{{ row.question_type }}</el-tag>
                      </div>
                    </div>
                    
                    <div class="expand-section" v-if="row.generated_answer">
                      <h4><el-icon><ChatLineRound /></el-icon>模型答案</h4>
                      <p class="section-text">{{ row.generated_answer }}</p>
                    </div>
                    
                    <div class="expand-section" v-if="row.context">
                      <h4><el-icon><Files /></el-icon>文档切片</h4>
                      <p class="section-text context-text">{{ row.context }}</p>
                    </div>
                    
                    <div class="expand-section">
                      <h4><el-icon><Star /></el-icon>打分依据</h4>
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
                      v-for="item in getOrderedMetricEntries(row.metrics)"
                      :key="item.key"
                      :type="getMetricType(item.key, item.value)"
                      size="small"
                      class="mr-1"
                    >
                      {{ getMetricName(item.key) }}: {{ item.value.toFixed(3) }}
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
import { Document, Download, Delete, QuestionFilled, List, ChatLineRound, Files, Star } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { registerTheme } from '@/utils/echarts/theme'
import { useTaskStore } from '@/stores/task'
import { evaluationApi } from '@/api/evaluations'
import { testsetApi } from '@/api/testsets'
import { formatDateTime, formatDuration } from '@/utils/format'
import type { Evaluation, EvaluationResult } from '@/types'

const route = useRoute()
const router = useRouter()
const taskStore = useTaskStore()

const loading = ref(false)
const evaluation = ref<Evaluation | null>(null)
const testsetName = ref('-')
const results = ref<EvaluationResult[]>([])
const taskProgress = ref(0)
const taskEvaluated = ref(0)
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
let pollingTimer: number | null = null
const SAFETY_METRICS = new Set(['toxicity', 'bias', 'hallucination'])

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

const isSafetyMetric = (key: string) => SAFETY_METRICS.has(key)

const getMetricType = (key: string, value: number) => {
  if (isSafetyMetric(key)) {
    if (value <= 0.2) return 'success'
    if (value <= 0.4) return 'warning'
    return 'danger'
  }
  if (value >= 0.8) return 'success'
  if (value >= 0.6) return 'warning'
  return 'danger'
}

const getMetricName = (key: string): string => {
  const metricNames: Record<string, string> = {
    answer_relevance: '答案相关性',
    context_relevance: '检索相关性',
    faithfulness: '忠实度',
    answer_correctness: '答案正确性',
    answer_similarity: '答案相似度',
    context_precision: '检索精确性',
    context_recall: '上下文召回率',
    toxicity: '有害言论检测',
    bias: '偏见检测',
    hallucination: '幻觉检测',
    ragas_score: '综合评分',
    overall_score: '综合评分',
    total: '总分',
    score: '得分',
    overall: '总体',
    average: '平均值'
  }
  return metricNames[key] || key
}

const normalizeMetricValue = (raw: any): number | null => {
  if (typeof raw === 'number') {
    return Number.isFinite(raw) ? raw : null
  }
  if (typeof raw === 'object' && raw !== null && 'mean' in raw) {
    const mean = (raw as any).mean
    return typeof mean === 'number' && Number.isFinite(mean) ? mean : null
  }
  return null
}

const qualityOverviewMetrics = computed(() => {
  if (!evaluation.value?.overall_metrics) return [] as Array<{ key: string; value: number }>
  const entries = Object.entries(evaluation.value.overall_metrics)
  return entries
    .filter(([key]) => key !== 'overall_score' && !isSafetyMetric(key))
    .map(([key, raw]) => ({ key, value: normalizeMetricValue(raw) }))
    .filter((item): item is { key: string; value: number } => item.value !== null)
})

const safetyOverviewMetrics = computed(() => {
  if (!evaluation.value?.overall_metrics) return [] as Array<{ key: string; value: number }>
  const entries = Object.entries(evaluation.value.overall_metrics)
  return entries
    .filter(([key]) => isSafetyMetric(key))
    .map(([key, raw]) => ({ key, value: normalizeMetricValue(raw) }))
    .filter((item): item is { key: string; value: number } => item.value !== null)
})

const getOrderedMetricEntries = (metrics: Record<string, number>) => {
  return Object.entries(metrics)
    .map(([key, value]) => ({ key, value }))
    .sort((a, b) => Number(isSafetyMetric(a.key)) - Number(isSafetyMetric(b.key)))
}

const fetchTestsetName = async () => {
  if (!evaluation.value?.testset_id) {
    testsetName.value = '-'
    return
  }
  try {
    const testset = await testsetApi.getTestSet(evaluation.value.testset_id)
    testsetName.value = testset.name || '-'
  } catch {
    testsetName.value = '-'
  }
}

const fetchEvaluation = async () => {
  const id = route.params.id as string
  loading.value = true
  
  try {
    evaluation.value = await evaluationApi.getEvaluation(id)
    await fetchTestsetName()
    
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
  
  let pollCount = 0
  
  const poll = async () => {
    pollCount++
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
        status: latest.status as 'running' | 'completed' | 'failed'
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
        
        ElMessage.success('评估任务已完成')
      } else if (latest.status === 'failed') {
        stopPolling()
        
        updateEvaluationTaskStatus(latest.id, {
          status: 'failed',
          error: latest.error_message || '评估失败'
        })

        ElMessage.error({
          message: latest.error_message || '评估任务执行失败',
          duration: 5000,
          showClose: true
        })
      }
    } catch (error) {
      console.error('Polling error:', error)
      // 如果连续失败多次，停止轮询
      if (pollCount > 10) {
        stopPolling()
        ElMessage.error('获取评估状态失败次数过多，已停止轮询')
      }
    }
  }
  
  await poll()
  // 每2秒轮询一次，比之前的3秒更及时
  pollingTimer = window.setInterval(poll, 2000)
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const handleRetry = () => {
  router.push('/evaluations')
}

const initChart = () => {
  if (!chartRef.value) return

  if (qualityOverviewMetrics.value.length === 0) {
    chartInstance?.dispose()
    chartInstance = null
    return
  }
  
  registerTheme()
  chartInstance = echarts.init(chartRef.value, 'saas')
  
  const data = qualityOverviewMetrics.value.map(item => ({
    name: getMetricName(item.key),
    value: item.value
  }))
  
  const option = {
    tooltip: {
      trigger: 'item',
      confine: true
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
        name: '质量指标',
        areaStyle: {
          color: 'rgba(37, 99, 235, 0.3)' // brand-1 transparent
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
.evaluation-detail-page {
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

  .metrics-chart {
    width: 100%;
    height: 300px;
  }

  .metrics-section-title {
    font-size: var(--font-14, 14px);
    color: var(--text-2, #606266);
    margin-bottom: 10px;
  }
  
  .metrics-cell {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
  
  .progress-info {
    color: var(--text-2, #909399);
    font-size: var(--font-14, 14px);
  }

  .error-alert {
    margin-bottom: 16px;
  }

  .error-details {
    p {
      margin: 8px 0;
      font-size: var(--font-14, 14px);
      color: var(--text-2, #606266);
      line-height: 1.6;
    }
  }

  .error-actions {
    display: flex;
    gap: 12px;
    margin-top: 16px;
  }

  .expand-content {
    padding: 24px;
    background-color: var(--bg-app, #f5f7fa);
    display: flex;
    flex-direction: column;
    gap: 24px;

    .expand-section {
      margin-bottom: 0;
      position: relative;
      padding-left: 16px;

      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 0;
        bottom: 0;
        width: 4px;
        background: var(--brand-1, #2563eb);
        border-radius: 2px;
        opacity: 0.3;
      }

      h4 {
        margin: 0 0 12px 0;
        font-size: var(--font-14, 14px);
        font-weight: var(--fw-600, 600);
        color: var(--text-2, #606266);
        text-transform: uppercase;
        letter-spacing: 0.5px;
        display: flex;
        align-items: center;
        gap: 8px;
      }

      .section-text {
        margin: 0;
        color: var(--text-1, #303133);
        font-size: var(--font-14, 14px);
        line-height: 1.8;
        white-space: pre-wrap;
        word-break: break-word;
        background: var(--bg-card, #ffffff);
        padding: 16px;
        border-radius: var(--radius-8, 8px);
        border: 1px solid var(--border-1, #e5eaf0);
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
      }

      .context-text {
        max-height: 300px;
        overflow-y: auto;
        font-family: var(--el-font-family-mono, monospace);
        font-size: 13px;
        color: var(--text-2, #606266);
      }

      .tag-group {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        padding: 4px 0;
      }

      .reasons-list {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
        gap: 12px;

        .reason-item {
          margin-bottom: 0;
          background: var(--bg-card, #ffffff);
          padding: 12px;
          border-radius: var(--radius-8, 8px);
          border: 1px solid var(--border-1, #e5eaf0);
          display: flex;
          flex-direction: column;
          gap: 8px;

          .el-tag {
            width: fit-content;
            margin-bottom: 0;
          }

          .reason-text {
            margin: 0;
            color: var(--text-2, #606266);
            font-size: 13px;
            line-height: 1.6;
          }
        }
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

:deep(.el-table) {
  --el-table-header-bg-color: var(--bg-app, #f8fafc);
  --el-table-header-text-color: var(--text-2, #606266);
  border-radius: var(--radius-8, 8px);
  overflow: hidden;
  
  th.el-table__cell {
    font-weight: 500;
  }
}
</style>
