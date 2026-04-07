<template>
  <div class="report-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">报告详情</span>
      </template>
    </el-page-header>
    
    <el-divider />
    
    <template v-if="summary">
      <el-row :gutter="20">
        <el-col :span="16">
          <el-card>
            <template #header>
              <span>评估摘要</span>
            </template>
            
            <el-descriptions :column="2" border>
              <el-descriptions-item label="评估ID">{{ evaluationId }}</el-descriptions-item>
              <el-descriptions-item label="问题总数">{{ summary.total_questions }}</el-descriptions-item>
              <el-descriptions-item label="已评估">{{ summary.evaluated_questions }}</el-descriptions-item>
              <el-descriptions-item label="综合得分">
                <el-tag :type="getScoreType(summary.overall_score)">
                  {{ summary.overall_score ? (summary.overall_score * 100).toFixed(1) + '%' : '-' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="性能等级">
                <el-tag>{{ summary.performance_level }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="评估耗时">{{ summary.evaluation_time }}s</el-descriptions-item>
            </el-descriptions>
          </el-card>
          
          <el-card class="mt-4">
            <template #header>
              <span>指标详情</span>
            </template>
            <div class="metrics-chart" ref="chartRef"></div>
          </el-card>
          
          <el-card class="mt-4" v-if="summary.recommendations.length > 0">
            <template #header>
              <span>改进建议</span>
            </template>
            <ul class="recommendations">
              <li v-for="(rec, index) in summary.recommendations" :key="index">
                {{ rec }}
              </li>
            </ul>
          </el-card>
        </el-col>
        
        <el-col :span="8">
          <el-card>
            <template #header>
              <span>操作</span>
            </template>
            
            <div class="action-buttons">
              <el-button type="primary" @click="downloadReport('html')">
                <el-icon><Download /></el-icon>
                下载HTML
              </el-button>
              <el-button type="success" @click="downloadReport('pdf')">
                <el-icon><Download /></el-icon>
                下载PDF
              </el-button>
              <el-button type="warning" @click="showCompareDialog = true">
                <el-icon><Sort /></el-icon>
                对比报告
              </el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>
    
    <el-dialog
      v-model="showCompareDialog"
      title="选择对比报告"
      width="400px"
    >
      <el-select v-model="compareId" placeholder="选择要对比的报告" style="width: 100%">
        <el-option
          v-for="report in otherReports"
          :key="report.evaluation_id"
          :label="report.evaluation_id.substring(0, 8)"
          :value="report.evaluation_id"
        />
      </el-select>
      
      <template #footer>
        <el-button @click="showCompareDialog = false">取消</el-button>
        <el-button type="primary" @click="compareReports" :disabled="!compareId">
          对比
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Download, Sort } from '@element-plus/icons-vue'
import * as echarts from 'echarts'
import { reportApi, type Report } from '@/api/reports'
import type { FormInstance } from 'element-plus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const evaluationId = ref('')
const summary = ref<any>(null)
const metrics = ref<Record<string, any>>({})
const otherReports = ref<Report[]>([])
const chartRef = ref<HTMLElement>()
const showCompareDialog = ref(false)
const compareId = ref('')
let chartInstance: echarts.ECharts | null = null

const getScoreType = (score: number | null) => {
  if (score === null) return 'info'
  if (score >= 0.8) return 'success'
  if (score >= 0.6) return 'warning'
  return 'danger'
}

const fetchReport = async () => {
  evaluationId.value = route.params.id as string
  loading.value = true
  
  try {
    const [summaryRes, metricsRes] = await Promise.all([
      reportApi.getReportSummary(evaluationId.value),
      reportApi.getReportMetrics(evaluationId.value)
    ])
    
    summary.value = summaryRes
    metrics.value = metricsRes.metrics
    
    await nextTick()
    initChart()
  } catch (error) {
    ElMessage.error('获取报告详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const fetchOtherReports = async () => {
  try {
    const response = await reportApi.getReports()
    otherReports.value = response.items.filter(
      (r: Report) => r.evaluation_id !== evaluationId.value
    )
  } catch (error) {
    console.error('Failed to fetch other reports:', error)
  }
}

const initChart = () => {
  if (!chartRef.value || !metrics.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  const data = Object.entries(metrics.value).map(([key, value]) => {
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

const downloadReport = async (format: 'pdf' | 'html') => {
  try {
    const blob = await reportApi.downloadReport(evaluationId.value, format)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `report_${evaluationId.value.substring(0, 8)}.${format}`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('下载失败')
  }
}

const compareReports = () => {
  if (!compareId.value) return
  router.push(`/reports/${evaluationId.value}/compare/${compareId.value}`)
}

onMounted(() => {
  fetchReport()
  fetchOtherReports()
})

onUnmounted(() => {
  chartInstance?.dispose()
})
</script>

<style lang="scss" scoped>
.report-detail {
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
  
  .recommendations {
    padding-left: 20px;
    
    li {
      margin-bottom: 8px;
      color: #606266;
    }
  }
}
</style>
