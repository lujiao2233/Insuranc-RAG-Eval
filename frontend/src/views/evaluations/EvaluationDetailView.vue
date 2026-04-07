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
        <el-col :span="16">
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
                      {{ key }}: {{ value.toFixed(3) }}
                    </el-tag>
                  </div>
                </template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        
        <el-col :span="8">
          <el-card>
            <template #header>
              <span>操作</span>
            </template>
            
            <div class="action-buttons">
              <el-button
                type="primary"
                @click="viewReport"
                :disabled="evaluation.status !== 'completed'"
              >
                <el-icon><Document /></el-icon>
                查看报告
              </el-button>
              <el-button
                type="success"
                @click="exportResults"
                :disabled="evaluation.status !== 'completed'"
              >
                <el-icon><Download /></el-icon>
                导出结果
              </el-button>
              <el-button type="danger" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                删除评估
              </el-button>
            </div>
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
import { useEvaluationStore } from '@/stores/evaluation'
import { evaluationApi } from '@/api/evaluations'
import { formatDateTime, formatDuration } from '@/utils/format'
import type { Evaluation, EvaluationResult } from '@/types'

const route = useRoute()
const router = useRouter()
const evaluationStore = useEvaluationStore()

const loading = ref(false)
const evaluation = ref<Evaluation | null>(null)
const results = ref<EvaluationResult[]>([])
const taskProgress = ref(0)
const taskEvaluated = ref(0)
const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null
let pollingTimer: number | null = null

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
      const status = await evaluationApi.getTaskStatus(evaluation.value!.id)
      taskProgress.value = status.progress || 0
      taskEvaluated.value = status.evaluated_questions || 0
      
      if (status.status === 'completed') {
        stopPolling()
        await fetchEvaluation()
      } else if (status.status === 'failed') {
        stopPolling()
        ElMessage.error('评估失败')
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
      name: key,
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

const viewReport = () => {
  router.push(`/reports/${evaluation.value?.id}`)
}

const exportResults = () => {
  ElMessage.info('导出功能开发中')
}

const handleDelete = async () => {
  if (!evaluation.value) return
  
  try {
    await ElMessageBox.confirm(
      '确定要删除此评估吗？',
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await evaluationStore.deleteEvaluation(evaluation.value.id)
    ElMessage.success('删除成功')
    router.push('/evaluations')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
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
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    .el-button {
      width: 100%;
      justify-content: flex-start;
    }
  }
  
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
}
</style>
