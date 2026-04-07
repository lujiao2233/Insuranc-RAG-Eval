<template>
  <div class="report-preview">
    <div class="preview-header">
      <div class="header-left">
        <h3 class="report-title">{{ reportTitle }}</h3>
        <div class="report-meta">
          <span v-if="reportData.timestamp" class="meta-item">
            <el-icon><Clock /></el-icon>
            {{ formatDate(reportData.timestamp) }}
          </span>
          <span v-if="reportData.evaluation_method" class="meta-item">
            <el-icon><DataAnalysis /></el-icon>
            {{ reportData.evaluation_method === 'ragas_official' ? 'RAGAS官方' : 'DeepEval' }}
          </span>
          <span v-if="reportData.total_questions" class="meta-item">
            <el-icon><Document /></el-icon>
            {{ reportData.total_questions }} 题
          </span>
        </div>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button :icon="Download" @click="handleDownload('json')">JSON</el-button>
          <el-button :icon="Download" @click="handleDownload('csv')">CSV</el-button>
          <el-button :icon="Printer" @click="handlePrint">打印</el-button>
        </el-button-group>
      </div>
    </div>

    <div class="preview-content" ref="contentRef">
      <div class="section overview-section">
        <h4 class="section-title">评估概览</h4>
        <div class="overview-cards">
          <div class="overview-card">
            <div class="card-label">总体得分</div>
            <div class="card-value" :class="getScoreClass(overallScore)">
              {{ formatScore(overallScore) }}
            </div>
          </div>
          <div class="overview-card">
            <div class="card-label">评估问题</div>
            <div class="card-value">{{ reportData.evaluated_questions || 0 }} / {{ reportData.total_questions || 0 }}</div>
          </div>
          <div class="overview-card">
            <div class="card-label">评估耗时</div>
            <div class="card-value">{{ formatDuration(reportData.evaluation_time || 0) }}</div>
          </div>
          <div class="overview-card">
            <div class="card-label">评估状态</div>
            <div class="card-value">
              <el-tag :type="getStatusType(reportData.status)">
                {{ getStatusText(reportData.status) }}
              </el-tag>
            </div>
          </div>
        </div>
      </div>

      <div v-if="metrics.length > 0" class="section metrics-section">
        <h4 class="section-title">指标分析</h4>
        <div class="metrics-grid">
          <div v-for="metric in metrics" :key="metric.name" class="metric-item">
            <div class="metric-header">
              <span class="metric-name">{{ metric.name }}</span>
              <el-tooltip v-if="metric.description" :content="metric.description" placement="top">
                <el-icon class="metric-info"><InfoFilled /></el-icon>
              </el-tooltip>
            </div>
            <div class="metric-value" :class="getScoreClass(metric.value)">
              {{ formatScore(metric.value) }}
            </div>
            <el-progress
              :percentage="metric.value * 100"
              :color="getScoreColor(metric.value)"
              :show-text="false"
              :stroke-width="8"
            />
          </div>
        </div>
      </div>

      <div v-if="showChart && metrics.length > 0" class="section chart-section">
        <h4 class="section-title">可视化分析</h4>
        <div class="chart-tabs">
          <el-radio-group v-model="chartType" size="small">
            <el-radio-button value="radar">雷达图</el-radio-button>
            <el-radio-button value="bar">柱状图</el-radio-button>
          </el-radio-group>
        </div>
        <MetricsChart
          :data="chartData"
          :type="chartType"
          :height="300"
          :show-legend="false"
        />
      </div>

      <div v-if="results.length > 0" class="section results-section">
        <h4 class="section-title">
          评估结果详情
          <el-button text size="small" @click="toggleResults">
            {{ resultsExpanded ? '收起' : '展开' }}
          </el-button>
        </h4>
        <el-collapse-transition>
          <div v-show="resultsExpanded" class="results-table">
            <el-table :data="paginatedResults" stripe border size="small">
              <el-table-column type="index" label="#" width="50" />
              <el-table-column prop="question_text" label="问题" min-width="200" show-overflow-tooltip />
              <el-table-column v-if="showExpectedAnswer" prop="expected_answer" label="期望答案" min-width="150" show-overflow-tooltip />
              <el-table-column v-if="showGeneratedAnswer" prop="generated_answer" label="生成答案" min-width="150" show-overflow-tooltip />
              <el-table-column v-for="metric in metricColumns" :key="metric" :label="metric" width="100">
                <template #default="{ row }">
                  <span :class="getScoreClass(row.metrics?.[metric] || 0)">
                    {{ formatScore(row.metrics?.[metric] || 0) }}
                  </span>
                </template>
              </el-table-column>
            </el-table>
            <div v-if="results.length > pageSize" class="pagination-wrapper">
              <el-pagination
                v-model:current-page="currentPage"
                :page-size="pageSize"
                :total="results.length"
                layout="prev, pager, next"
                small
              />
            </div>
          </div>
        </el-collapse-transition>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { Clock, DataAnalysis, Document, Download, Printer, InfoFilled } from '@element-plus/icons-vue'
import MetricsChart from './MetricsChart.vue'
import type { Evaluation, EvaluationResult } from '@/types/models'

interface MetricItem {
  name: string
  value: number
  description?: string
}

interface Props {
  reportData: Partial<Evaluation>
  results?: EvaluationResult[]
  reportTitle?: string
  showChart?: boolean
  showExpectedAnswer?: boolean
  showGeneratedAnswer?: boolean
  pageSize?: number
}

const props = withDefaults(defineProps<Props>(), {
  results: () => [],
  reportTitle: '评估报告',
  showChart: true,
  showExpectedAnswer: true,
  showGeneratedAnswer: true,
  pageSize: 10
})

const emit = defineEmits<{
  (e: 'download', format: 'json' | 'csv'): void
  (e: 'print'): void
}>()

const contentRef = ref<HTMLElement>()
const chartType = ref<'radar' | 'bar'>('radar')
const resultsExpanded = ref(true)
const currentPage = ref(1)

const overallScore = computed(() => {
  if (!props.reportData.overall_metrics) return 0
  const metrics = Object.values(props.reportData.overall_metrics) as number[]
  if (metrics.length === 0) return 0
  return metrics.reduce((sum, val) => sum + val, 0) / metrics.length
})

const metrics = computed((): MetricItem[] => {
  if (!props.reportData.overall_metrics) return []
  return Object.entries(props.reportData.overall_metrics).map(([key, value]) => ({
    name: getMetricLabel(key),
    value: value as number,
    description: getMetricDescription(key)
  }))
})

const chartData = computed(() => {
  return metrics.value.map(m => ({
    name: m.name,
    value: m.value
  }))
})

const metricColumns = computed(() => {
  if (props.results.length === 0 || !props.results[0].metrics) return []
  return Object.keys(props.results[0].metrics)
})

const paginatedResults = computed(() => {
  const start = (currentPage.value - 1) * props.pageSize
  const end = start + props.pageSize
  return props.results.slice(start, end)
})

const getMetricLabel = (key: string) => {
  const labels: Record<string, string> = {
    faithfulness: '忠实度',
    answer_relevancy: '答案相关性',
    context_precision: '上下文精确度',
    context_recall: '上下文召回率',
    answer_correctness: '答案正确性',
    answer_similarity: '答案相似度',
    context_relevancy: '上下文相关性',
    hallucination: '幻觉率'
  }
  return labels[key] || key
}

const getMetricDescription = (key: string) => {
  const descriptions: Record<string, string> = {
    faithfulness: '衡量生成答案与检索上下文的一致性',
    answer_relevancy: '衡量答案与问题的相关程度',
    context_precision: '衡量检索上下文的精确程度',
    context_recall: '衡量检索上下文的召回程度',
    answer_correctness: '衡量答案的正确程度',
    answer_similarity: '衡量生成答案与期望答案的相似度',
    context_relevancy: '衡量检索上下文与问题的相关性',
    hallucination: '衡量生成答案中的幻觉内容比例'
  }
  return descriptions[key]
}

const formatDate = (dateStr: string) => {
  if (!dateStr) return ''
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const formatDuration = (seconds: number) => {
  if (!seconds) return '0秒'
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return mins > 0 ? `${mins}分${secs}秒` : `${secs}秒`
}

const formatScore = (score: number) => {
  if (score >= 1) return score.toFixed(1)
  return (score * 100).toFixed(1) + '%'
}

const getScoreClass = (score: number) => {
  if (score >= 0.8) return 'score-high'
  if (score >= 0.6) return 'score-medium'
  return 'score-low'
}

const getScoreColor = (score: number) => {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

const getStatusType = (status?: string) => {
  const types: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return types[status || ''] || 'info'
}

const getStatusText = (status?: string) => {
  const texts: Record<string, string> = {
    pending: '待处理',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return texts[status || ''] || status
}

const toggleResults = () => {
  resultsExpanded.value = !resultsExpanded.value
}

const handleDownload = (format: 'json' | 'csv') => {
  emit('download', format)

  const data = {
    report: props.reportData,
    results: props.results
  }

  if (format === 'json') {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    downloadBlob(blob, `report_${Date.now()}.json`)
  } else {
    const headers = ['问题', '期望答案', '生成答案', ...metricColumns.value]
    const rows = props.results.map(r => [
      r.question_text,
      r.expected_answer || '',
      r.generated_answer || '',
      ...metricColumns.value.map(m => r.metrics?.[m]?.toFixed(4) || '')
    ])
    const csv = [headers.join(','), ...rows.map(r => r.map(c => `"${c}"`).join(','))].join('\n')
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' })
    downloadBlob(blob, `report_${Date.now()}.csv`)
  }
}

const downloadBlob = (blob: Blob, filename: string) => {
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

const handlePrint = () => {
  emit('print')
  window.print()
}

defineExpose({
  contentRef
})
</script>

<style lang="scss" scoped>
.report-preview {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);

  .preview-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    padding: 20px 24px;
    border-bottom: 1px solid #ebeef5;

    .header-left {
      .report-title {
        font-size: 18px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 12px;
      }

      .report-meta {
        display: flex;
        gap: 16px;

        .meta-item {
          display: flex;
          align-items: center;
          gap: 4px;
          font-size: 13px;
          color: #909399;

          .el-icon {
            font-size: 14px;
          }
        }
      }
    }
  }

  .preview-content {
    padding: 24px;

    .section {
      margin-bottom: 32px;

      &:last-child {
        margin-bottom: 0;
      }

      .section-title {
        display: flex;
        align-items: center;
        justify-content: space-between;
        font-size: 15px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 16px;
        padding-bottom: 12px;
        border-bottom: 1px solid #ebeef5;
      }
    }

    .overview-cards {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;

      .overview-card {
        padding: 16px;
        background-color: #f5f7fa;
        border-radius: 8px;
        text-align: center;

        .card-label {
          font-size: 13px;
          color: #909399;
          margin-bottom: 8px;
        }

        .card-value {
          font-size: 24px;
          font-weight: 600;
          color: #303133;

          &.score-high {
            color: #67c23a;
          }

          &.score-medium {
            color: #e6a23c;
          }

          &.score-low {
            color: #f56c6c;
          }
        }
      }
    }

    .metrics-grid {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;

      .metric-item {
        padding: 16px;
        background-color: #fafafa;
        border-radius: 8px;

        .metric-header {
          display: flex;
          align-items: center;
          gap: 4px;
          margin-bottom: 8px;

          .metric-name {
            font-size: 13px;
            color: #606266;
          }

          .metric-info {
            font-size: 14px;
            color: #909399;
            cursor: help;
          }
        }

        .metric-value {
          font-size: 20px;
          font-weight: 600;
          margin-bottom: 8px;

          &.score-high {
            color: #67c23a;
          }

          &.score-medium {
            color: #e6a23c;
          }

          &.score-low {
            color: #f56c6c;
          }
        }
      }
    }

    .chart-section {
      .chart-tabs {
        margin-bottom: 16px;
      }
    }

    .results-table {
      .pagination-wrapper {
        display: flex;
        justify-content: center;
        margin-top: 16px;
      }
    }
  }
}

.score-high {
  color: #67c23a;
}

.score-medium {
  color: #e6a23c;
}

.score-low {
  color: #f56c6c;
}

@media (max-width: 992px) {
  .report-preview {
    .preview-content {
      .overview-cards {
        grid-template-columns: repeat(2, 1fr);
      }

      .metrics-grid {
        grid-template-columns: repeat(2, 1fr);
      }
    }
  }
}

@media (max-width: 576px) {
  .report-preview {
    .preview-content {
      .overview-cards,
      .metrics-grid {
        grid-template-columns: 1fr;
      }
    }
  }
}

@media print {
  .report-preview {
    .preview-header {
      .header-right {
        display: none;
      }
    }
  }
}
</style>
