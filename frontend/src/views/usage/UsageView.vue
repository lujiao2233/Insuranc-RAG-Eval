<template>
  <div class="usage-dashboard" v-loading="loading">
    <div class="header-actions">
      <div class="title">API 用量与性能大盘</div>
      <div class="filters">
        <el-select v-model="rangePreset" style="width: 140px; margin-right: 10px" @change="onRangePresetChange">
          <el-option label="最近 1 小时" value="1h" />
          <el-option label="最近 24 小时" value="24h" />
          <el-option label="最近 7 天" value="7d" />
          <el-option label="自定义" value="custom" />
        </el-select>
        <el-date-picker
          v-if="rangePreset === 'custom'"
          v-model="customRange"
          type="datetimerange"
          start-placeholder="开始时间"
          end-placeholder="结束时间"
          format="YYYY-MM-DD HH:mm"
          :clearable="false"
          style="width: 320px; margin-right: 10px"
          @change="fetchData"
        />
        <el-button type="primary" :loading="loading" @click="fetchData">刷新</el-button>
      </div>
    </div>

    <!-- 第一层：高价值总览 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <div class="stat-title">总调用次数</div>
          <div class="stat-value">{{ dashboard?.overview.total_calls || 0 }}</div>
          <div class="stat-desc">近24h: {{ dashboard?.overview.calls_last_24h || 0 }} 次</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <div class="stat-title">总 Token 消耗</div>
          <div class="stat-value">{{ (dashboard?.overview.total_tokens || 0).toLocaleString() }}</div>
          <div class="stat-desc">输入/输出: {{ dashboard?.io_ratio.avg_prompt_tokens || 0 }} / {{ dashboard?.io_ratio.avg_completion_tokens || 0 }} (均值)</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <div class="stat-title">平均耗时 (ms)</div>
          <div class="stat-value">{{ dashboard?.overview.avg_latency || 0 }}</div>
          <div class="stat-desc">P90耗时: {{ dashboard?.percentiles.p90 || 0 }} ms</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="data-card">
          <div class="stat-title">预估费用 (¥)</div>
          <div class="stat-value">{{ dashboard?.overview.estimated_cost || 0 }}</div>
          <div class="stat-desc">按 Qwen 官方标准费率估算</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二层：性能、异常与分布 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="8">
        <el-card shadow="hover" header="耗时分位数分布">
          <div class="stat-row">
            <span>P50 耗时 (中位数):</span> <strong>{{ dashboard?.percentiles.p50 || 0 }} ms</strong>
          </div>
          <div class="stat-row">
            <span>P90 耗时:</span> <strong>{{ dashboard?.percentiles.p90 || 0 }} ms</strong>
          </div>
          <div class="stat-row">
            <span>P95 耗时:</span> <strong style="color: #E6A23C">{{ dashboard?.percentiles.p95 || 0 }} ms</strong>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover" header="异常与失败监控">
          <div class="stat-row">
            <span>失败率:</span> 
            <strong :style="{color: (dashboard?.errors.failure_rate || 0) > 0.05 ? '#F56C6C' : '#67C23A'}">
              {{ ((dashboard?.errors.failure_rate || 0) * 100).toFixed(2) }}%
            </strong>
          </div>
          <div class="stat-row mb-2">
            <span>总失败请求:</span> 
            <strong :style="{color: (dashboard?.errors.total_failures || 0) > 0 ? '#F56C6C' : '#67C23A'}">
              {{ dashboard?.errors.total_failures || 0 }}
            </strong>
          </div>
          <div v-if="dashboard?.errors.top_failed_modules?.length" class="fail-list mt-2">
            <div class="fail-title" style="font-size: 12px; color: #909399; margin-bottom: 4px;">Top 失败模块:</div>
            <div v-for="err in dashboard.errors.top_failed_modules" :key="err.module" class="fail-item">
              <span style="font-size: 13px">{{ getModuleLabel(err.module) }}</span>
              <el-tag type="danger" size="small">{{ err.failures }} 次</el-tag>
            </div>
          </div>
          <div v-else class="text-center mt-4" style="color: #909399; font-size: 13px">暂无失败记录</div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="hover" header="模块 Token 占比">
          <div ref="pieChartRef" style="height: 180px"></div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三层：趋势与对比 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="18">
        <el-card shadow="hover" header="请求明细与 Token 趋势">
          <div ref="chartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" header="环比分析 (vs上一周期)">
          <div class="compare-item">
            <div class="c-label">调用次数</div>
            <div class="c-val">
              <span class="curr">{{ dashboard?.trend_compare.current_period.calls || 0 }}</span>
              <span class="vs">vs</span>
              <span class="prev">{{ dashboard?.trend_compare.previous_period.calls || 0 }}</span>
            </div>
          </div>
          <div class="compare-item">
            <div class="c-label">Token 消耗</div>
            <div class="c-val">
              <span class="curr">{{ dashboard?.trend_compare.current_period.tokens || 0 }}</span>
              <span class="vs">vs</span>
              <span class="prev">{{ dashboard?.trend_compare.previous_period.tokens || 0 }}</span>
            </div>
          </div>
          <div class="compare-item">
            <div class="c-label">预估费用</div>
            <div class="c-val">
              <span class="curr">¥{{ dashboard?.trend_compare.current_period.cost || 0 }}</span>
              <span class="vs">vs</span>
              <span class="prev">¥{{ dashboard?.trend_compare.previous_period.cost || 0 }}</span>
            </div>
          </div>
          <div class="compare-item">
            <div class="c-label">失败率</div>
            <div class="c-val">
              <span class="curr">{{ ((dashboard?.trend_compare.current_period.failure_rate || 0) * 100).toFixed(2) }}%</span>
              <span class="vs">vs</span>
              <span class="prev">{{ ((dashboard?.trend_compare.previous_period.failure_rate || 0) * 100).toFixed(2) }}%</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三层：模型对比表格 -->
    <el-card shadow="hover" header="模型深度分析与对比">
      <el-table :data="dashboard?.models || []" border stripe>
        <el-table-column prop="model" label="模型名称" min-width="150" />
        <el-table-column prop="calls" label="总调用次数" width="120" />
        <el-table-column prop="tokens" label="总 Token 消耗" width="150" />
        <el-table-column label="单次平均 Token" width="150">
          <template #default="{ row }">{{ Math.round(row.avg_tokens) }}</template>
        </el-table-column>
        <el-table-column label="单次平均耗时" width="150">
          <template #default="{ row }">{{ Math.round(row.avg_latency) }} ms</template>
        </el-table-column>
        <el-table-column label="总估算费用" width="150">
          <template #default="{ row }">¥{{ row.cost.toFixed(4) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import { format } from 'date-fns'
import { usageApi, type UsageEvent, type UsageDashboard } from '@/api/usage'

type RangePreset = '1h' | '24h' | '7d' | 'custom'

const loading = ref(false)
const rangePreset = ref<RangePreset>('24h')
const customRange = ref<[Date, Date] | null>(null)

const dashboard = ref<UsageDashboard | null>(null)
const events = ref<UsageEvent[]>([])

const chartRef = ref<HTMLElement>()
const pieChartRef = ref<HTMLElement>()
let chartInstance: ECharts | null = null
let pieChartInstance: ECharts | null = null

const MODULE_LABEL_MAP: Record<string, string> = {
  document_analysis: '文档分析',
  metadata_extraction: '文档分析',
  outline_generation: '文档分析',
  testset_gen: '测试集生成',
  evaluation: '评估',
  unknown: '文档分析(未标注)'
}

const getModuleLabel = (moduleName: string) => MODULE_LABEL_MAP[moduleName] || moduleName

const toLocalIso = (date: Date) => format(date, "yyyy-MM-dd'T'HH:mm:ss")

const getRange = () => {
  const now = new Date()
  if (rangePreset.value === 'custom' && customRange.value) {
    return { start: toLocalIso(customRange.value[0]), end: toLocalIso(customRange.value[1]) }
  }

  const end = toLocalIso(now)
  const startDate = new Date(now.getTime())
  if (rangePreset.value === '1h') startDate.setHours(startDate.getHours() - 1)
  if (rangePreset.value === '24h') startDate.setHours(startDate.getHours() - 24)
  if (rangePreset.value === '7d') startDate.setDate(startDate.getDate() - 7)
  const start = toLocalIso(startDate)
  return { start, end }
}

const buildPieOption = (data: any[]): EChartsOption => {
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} Tokens ({d}%)' },
    legend: { orient: 'vertical', left: 'right', top: 'center', textStyle: { fontSize: 12 } },
    series: [
      {
        name: '模块占比',
        type: 'pie',
        radius: ['40%', '70%'],
        center: ['35%', '50%'],
        avoidLabelOverlap: false,
        label: { show: false },
        data: data.map(item => ({
          name: getModuleLabel(item.module),
          value: item.tokens
        }))
      }
    ]
  }
}

const buildOption = (): EChartsOption => {
  const data = events.value.map((e) => ({
    value: [new Date(e.timestamp).getTime(), e.total_tokens],
    module: e.module,
    model: e.model,
    latency_ms: e.latency_ms,
    prompt_tokens: e.prompt_tokens,
    completion_tokens: e.completion_tokens
  }))

  return {
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        const ts = params?.data?.value?.[0]
        const tokenVal = params?.data?.value?.[1]
        const timeStr = ts ? format(new Date(ts), 'yyyy-MM-dd HH:mm:ss') : '-'
        const moduleName = params?.data?.module ?? '-'
        const modelName = params?.data?.model ?? '-'
        const latency = params?.data?.latency_ms ?? 0
        const promptTokens = params?.data?.prompt_tokens ?? 0
        const completionTokens = params?.data?.completion_tokens ?? 0
        return [
          `<div style="font-weight:600;margin-bottom:6px;">${timeStr}</div>`,
          `<div>模块：${getModuleLabel(moduleName)}</div>`,
          `<div>模型：${modelName}</div>`,
          `<div>Token：${tokenVal}</div>`,
          `<div>输入/输出：${promptTokens}/${completionTokens}</div>`,
          `<div>耗时：${latency} ms</div>`
        ].join('')
      }
    },
    xAxis: {
      type: 'time',
      axisLabel: { color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      splitLine: { show: false }
    },
    yAxis: {
      type: 'value',
      name: 'Tokens',
      nameTextStyle: { color: '#909399', padding: [0, 20, 0, 0] },
      axisLabel: { color: '#909399' },
      splitLine: { lineStyle: { type: 'dashed', color: '#ebeef5' } }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100 },
      { start: 0, end: 100, height: 16, bottom: 0, borderColor: 'transparent', backgroundColor: '#f4f4f5' }
    ],
    series: [
      {
        name: 'Token 消耗',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 6,
        itemStyle: { color: '#5470c6', borderColor: '#fff', borderWidth: 2 },
        lineStyle: { width: 3, shadowColor: 'rgba(84,112,198,0.3)', shadowBlur: 10 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(84,112,198,0.3)' },
            { offset: 1, color: 'rgba(84,112,198,0.05)' }
          ])
        },
        data
      }
    ]
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const { start, end } = getRange()
    const [eventsRes, dashRes] = await Promise.all([
      usageApi.getEvents({ start, end }),
      usageApi.getDashboard({ start, end })
    ])

    events.value = eventsRes.data || []
    dashboard.value = dashRes.data

    await nextTick()
    
    if (chartRef.value) {
      if (!chartInstance) {
        chartInstance = echarts.init(chartRef.value)
      }
      chartInstance.setOption(buildOption(), true)
    }

    if (pieChartRef.value && dashboard.value?.module_ratio) {
      if (!pieChartInstance) {
        pieChartInstance = echarts.init(pieChartRef.value)
      }
      pieChartInstance.setOption(buildPieOption(dashboard.value.module_ratio), true)
    }
  } catch (error) {
    console.error('Fetch usage data error:', error)
  } finally {
    loading.value = false
  }
}

const onRangePresetChange = () => {
  if (rangePreset.value === 'custom') {
    const end = new Date()
    const start = new Date()
    start.setDate(start.getDate() - 1)
    customRange.value = [start, end]
  } else {
    fetchData()
  }
}

const handleResize = () => {
  chartInstance?.resize()
  pieChartInstance?.resize()
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  pieChartInstance?.dispose()
})
</script>

<style scoped>
.usage-dashboard {
  padding: 20px;
}

.header-actions {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions .title {
  font-size: 20px;
  font-weight: bold;
  color: #303133;
}

.filters {
  display: flex;
  align-items: center;
}

.mb-4 {
  margin-bottom: 16px;
}

.data-card {
  height: 120px;
}

.stat-title {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 8px;
}

.stat-desc {
  font-size: 12px;
  color: #909399;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
}

.mt-2 { margin-top: 8px; }
.mt-4 { margin-top: 16px; }

.fail-list {
  background: #fdf6f6;
  border-radius: 4px;
  padding: 8px;
}
.fail-item {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
}

.compare-item {
  margin-bottom: 16px;
}
.compare-item .c-label {
  font-size: 13px;
  color: #909399;
  margin-bottom: 4px;
}
.compare-item .c-val {
  display: flex;
  align-items: baseline;
}
.compare-item .curr {
  font-size: 18px;
  font-weight: bold;
  color: #303133;
}
.compare-item .vs {
  margin: 0 8px;
  font-size: 12px;
  color: #C0C4CC;
}
.compare-item .prev {
  font-size: 14px;
  color: #909399;
}
</style>
