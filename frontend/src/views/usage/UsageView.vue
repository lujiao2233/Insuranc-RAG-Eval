<template>
  <div class="page usage-page" v-loading="loading">
    <div class="header-actions section-sm">
      <div class="page-title">API 用量与性能大盘</div>
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
    <el-row :gutter="16" class="section-sm">
      <el-col :span="6">
        <el-card shadow="never" class="data-card">
          <div class="stat-title">总调用次数</div>
          <div class="stat-value">{{ dashboard?.overview.total_calls || 0 }}</div>
          <div class="stat-desc">近24h: {{ dashboard?.overview.calls_last_24h || 0 }} 次</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="data-card">
          <div class="stat-title">总 Token 消耗</div>
          <div class="stat-value">{{ (dashboard?.overview.total_tokens || 0).toLocaleString() }}</div>
          <div class="stat-desc">输入/输出: {{ dashboard?.io_ratio.avg_prompt_tokens || 0 }} / {{ dashboard?.io_ratio.avg_completion_tokens || 0 }} (均值)</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="data-card">
          <div class="stat-title">平均耗时 (ms)</div>
          <div class="stat-value">{{ dashboard?.overview.avg_latency || 0 }}</div>
          <div class="stat-desc">P90耗时: {{ dashboard?.percentiles.p90 || 0 }} ms</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="data-card">
          <div class="stat-title">预估费用 (¥)</div>
          <div class="stat-value">{{ dashboard?.overview.estimated_cost || 0 }}</div>
          <div class="stat-desc">按 Qwen 官方标准费率估算</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第二层：性能、异常与趋势 -->
    <el-row :gutter="16" class="section-sm">
      <!-- 左侧：请求明细与 Token 趋势 -->
      <el-col :span="16">
        <el-card shadow="never" header="请求明细与 Token 趋势" class="h-full">
          <div ref="chartRef" style="height: 340px"></div>
        </el-card>
      </el-col>
      
      <!-- 右侧：分位数与监控垂直堆叠 -->
      <el-col :span="8">
        <el-card shadow="never" header="耗时分位数分布" style="margin-bottom: 16px">
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-label">P50 (中位数)</div>
              <div class="stat-num">{{ dashboard?.percentiles.p50 || 0 }}<small>ms</small></div>
            </div>
            <div class="stat-item">
              <div class="stat-label">P90</div>
              <div class="stat-num">{{ dashboard?.percentiles.p90 || 0 }}<small>ms</small></div>
            </div>
            <div class="stat-item">
              <div class="stat-label">P95</div>
              <div class="stat-num highlight">{{ dashboard?.percentiles.p95 || 0 }}<small>ms</small></div>
            </div>
          </div>
        </el-card>

        <el-card shadow="never" header="异常与失败监控">
          <div class="stat-grid">
            <div class="stat-item">
              <div class="stat-label">失败率</div>
              <div class="stat-num" :class="{ 'text-danger': (dashboard?.errors.failure_rate || 0) > 0.05, 'text-success': (dashboard?.errors.failure_rate || 0) <= 0.05 }">
                {{ ((dashboard?.errors.failure_rate || 0) * 100).toFixed(1) }}%
              </div>
            </div>
            <div class="stat-item">
              <div class="stat-label">总失败数</div>
              <div class="stat-num" :class="{ 'text-danger': (dashboard?.errors.total_failures || 0) > 0 }">
                {{ dashboard?.errors.total_failures || 0 }}
              </div>
            </div>
          </div>
          <div v-if="dashboard?.errors.top_failed_modules?.length" class="fail-list mt-2">
            <div class="fail-title">Top 失败模块:</div>
            <div v-for="err in dashboard.errors.top_failed_modules" :key="err.module" class="fail-item">
              <span>{{ getModuleLabel(err.module) }}</span>
              <el-tag type="danger" size="small" effect="plain">{{ err.failures }} 次</el-tag>
            </div>
          </div>
          <div v-else class="text-center mt-4 empty-hint">暂无失败记录</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 第三层：分布与对比 -->
    <el-row :gutter="16" class="section-sm">
      <el-col :span="18">
        <el-card shadow="never" header="模块 Token 占比">
          <div ref="pieChartRef" style="height: 300px"></div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" header="环比分析 (vs上一周期)" class="h-full">
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
    <el-card shadow="never" class="section" header="模型深度分析与对比">
      <el-table :data="dashboard?.models || []" size="small" style="width: 100%">
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
import { registerTheme } from '@/utils/echarts/theme'
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
    tooltip: { trigger: 'item', formatter: '{b}: {c} Tokens ({d}%)', confine: true },
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
  // 1. 基础排序，确保连线方向正确
  const sortedEvents = [...events.value].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )

  // 2. 聚合逻辑：将时间极其接近（比如 1s 内）的请求合并展示趋势，避免“锯齿”和“乱码”
  // 如果点数不多（< 50），保留原始明细点；如果点数多，进行桶聚合
  const useBucket = sortedEvents.length > 50
  const bucketSize = 1000 * 5 // 5s 一个桶

  let chartData: any[] = []
  if (useBucket) {
    const buckets = new Map<number, { tokens: number; count: number; models: Set<string> }>()
    sortedEvents.forEach(e => {
      const t = Math.floor(new Date(e.timestamp).getTime() / bucketSize) * bucketSize
      if (!buckets.has(t)) buckets.set(t, { tokens: 0, count: 0, models: new Set() })
      const b = buckets.get(t)!
      b.tokens += e.total_tokens
      b.count += 1
      b.models.add(e.model)
    })
    chartData = Array.from(buckets.entries()).map(([t, b]) => ({
      value: [t, b.tokens],
      count: b.count,
      isBucket: true,
      models: Array.from(b.models).join(', ')
    }))
  } else {
    chartData = sortedEvents.map((e) => ({
      value: [new Date(e.timestamp).getTime(), e.total_tokens],
      module: e.module,
      model: e.model,
      latency_ms: e.latency_ms,
      prompt_tokens: e.prompt_tokens,
      completion_tokens: e.completion_tokens,
      isBucket: false
    }))
  }

  return {
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: any) => {
        const p = params[0]
        const ts = p?.data?.value?.[0]
        const timeStr = ts ? format(new Date(ts), 'yyyy-MM-dd HH:mm:ss') : '-'
        
        if (p?.data?.isBucket) {
          return [
            `<div style="font-weight:600;margin-bottom:6px;">${timeStr} (聚合窗口)</div>`,
            `<div>请求次数：${p.data.count}</div>`,
            `<div>总 Token：${p.data.value[1]}</div>`,
            `<div>涉及模型：${p.data.models}</div>`
          ].join('')
        }

        const tokenVal = p?.data?.value?.[1]
        const moduleName = p?.data?.module ?? '-'
        const modelName = p?.data?.model ?? '-'
        const latency = p?.data?.latency_ms ?? 0
        const promptTokens = p?.data?.prompt_tokens ?? 0
        const completionTokens = p?.data?.completion_tokens ?? 0
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
      axisLabel: {
        hideOverlap: true
      }
    },
    yAxis: {
      type: 'value',
      name: useBucket ? 'Tokens (Sum/5s)' : 'Tokens',
      nameTextStyle: { padding: [0, 20, 0, 0] }
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
        showSymbol: !useBucket, // 聚合时隐藏点，只看趋势
        symbolSize: 6,
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(37, 99, 235, 0.3)' },
            { offset: 1, color: 'rgba(37, 99, 235, 0.05)' }
          ])
        },
        data: chartData
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
        registerTheme()
        chartInstance = echarts.init(chartRef.value, 'saas')
      }
      chartInstance.setOption(buildOption(), true)
    }

    if (pieChartRef.value && dashboard.value?.module_ratio) {
      if (!pieChartInstance) {
        registerTheme()
        pieChartInstance = echarts.init(pieChartRef.value, 'saas')
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

<style lang="scss" scoped>
.usage-page {
  .header-actions {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .page-title {
      font-size: var(--font-20, 20px);
      font-weight: var(--fw-600, 600);
      color: var(--text-1, #303133);
    }
  }

  .filters {
    display: flex;
    align-items: center;
  }

  .data-card {
    min-height: 140px;
    height: auto;
    border-radius: var(--radius-8, 8px);
    
    .stat-title {
      font-size: var(--font-14, 14px);
      color: var(--text-2, #909399);
      margin-bottom: 8px;
    }
    
    .stat-value {
      font-size: 28px;
      font-weight: bold;
      color: var(--text-1, #303133);
      margin-bottom: 8px;
    }
    
    .stat-desc {
      font-size: var(--font-12, 12px);
      color: var(--text-2, #909399);
    }
  }

  .stat-grid {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    
    .stat-item {
      flex: 1;
      
      .stat-label {
        font-size: var(--font-12, 12px);
        color: var(--text-2, #909399);
        margin-bottom: 4px;
      }
      
      .stat-num {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-1, #303133);
        
        small {
          font-size: 12px;
          font-weight: 400;
          margin-left: 2px;
          color: var(--text-3, #c0c4cc);
        }
        
        &.highlight {
          color: var(--warning-1, #f59e0b);
        }
        
        &.text-danger {
          color: var(--danger-1, #ef4444);
        }
        
        &.text-success {
          color: var(--success-1, #16a34a);
        }
      }
    }
  }

  .stat-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: var(--font-14, 14px);
    color: var(--text-1, #303133);
  }

  .mt-2 { margin-top: 8px; }
  .mt-4 { margin-top: 16px; }

  .fail-list {
    background: rgba(239, 68, 68, 0.05);
    border-radius: var(--radius-8, 8px);
    padding: 8px;
    
    .fail-title {
      font-size: var(--font-12, 12px);
      color: var(--text-2, #909399);
      margin-bottom: 4px;
    }
  }
  
  .fail-item {
    display: flex;
    justify-content: space-between;
    margin-top: 4px;
    color: var(--text-1, #303133);
  }
  
  .empty-hint {
    color: var(--text-2, #909399);
    font-size: var(--font-12, 12px);
  }

  .compare-item {
    margin-bottom: 16px;
    
    .c-label {
      font-size: var(--font-12, 12px);
      color: var(--text-2, #909399);
      margin-bottom: 4px;
    }
    
    .c-val {
      display: flex;
      align-items: baseline;
      
      .curr {
        font-size: var(--font-16, 16px);
        font-weight: var(--fw-600, 600);
        color: var(--text-1, #303133);
      }
      
      .vs {
        margin: 0 8px;
        font-size: var(--font-12, 12px);
        color: var(--border-1, #e5eaf0);
      }
      
      .prev {
        font-size: var(--font-14, 14px);
        color: var(--text-2, #909399);
      }
    }
  }
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid var(--border-1, #ebeef5);
  font-weight: var(--fw-600, 600);
  font-size: var(--font-14, 14px);
  color: var(--text-1, #303133);
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
