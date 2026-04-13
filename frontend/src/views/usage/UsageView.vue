<template>
  <div class="usage-view">
    <el-card>
      <template #header>
        <div class="header">
          <div class="title">Token 消耗趋势</div>
          <div class="filters">
            <el-select v-model="rangePreset" style="width: 140px" @change="onRangePresetChange">
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
              style="width: 360px"
              @change="fetchData"
            />
            <el-button type="primary" :loading="loading" @click="fetchData">刷新</el-button>
          </div>
        </div>
      </template>
      <div ref="chartRef" class="chart" v-loading="loading"></div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import { format } from 'date-fns'
import { usageApi, type UsageEvent } from '@/api/usage'

type RangePreset = '1h' | '24h' | '7d' | 'custom'

const chartRef = ref<HTMLElement>()
let chartInstance: ECharts | null = null

const loading = ref(false)
const rangePreset = ref<RangePreset>('24h')
const customRange = ref<[Date, Date] | null>(null)
const events = ref<UsageEvent[]>([])

const getRange = () => {
  const now = new Date()
  if (rangePreset.value === 'custom' && customRange.value) {
    return { start: customRange.value[0].toISOString(), end: customRange.value[1].toISOString() }
  }

  const end = now.toISOString()
  const startDate = new Date(now.getTime())
  if (rangePreset.value === '1h') startDate.setHours(startDate.getHours() - 1)
  if (rangePreset.value === '24h') startDate.setHours(startDate.getHours() - 24)
  if (rangePreset.value === '7d') startDate.setDate(startDate.getDate() - 7)
  const start = startDate.toISOString()
  return { start, end }
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
    grid: { left: 50, right: 20, top: 20, bottom: 50 },
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
          `<div>模块：${moduleName}</div>`,
          `<div>模型：${modelName}</div>`,
          `<div>Token：${tokenVal}</div>`,
          `<div>Prompt/Completion：${promptTokens}/${completionTokens}</div>`,
          `<div>耗时：${latency} ms</div>`
        ].join('')
      }
    },
    xAxis: {
      type: 'time',
      axisLabel: { color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      splitLine: { lineStyle: { color: '#ebeef5' } }
    },
    yAxis: {
      type: 'value',
      name: 'tokens',
      nameTextStyle: { color: '#909399' },
      axisLabel: { color: '#909399' },
      axisLine: { lineStyle: { color: '#dcdfe6' } },
      splitLine: { lineStyle: { color: '#ebeef5' } }
    },
    dataZoom: [
      { type: 'inside', xAxisIndex: 0 },
      { type: 'slider', xAxisIndex: 0, height: 20, bottom: 10 }
    ],
    series: [
      {
        type: 'line',
        name: 'Token',
        data,
        showSymbol: true,
        symbolSize: 6,
        smooth: false,
        sampling: 'lttb',
        lineStyle: { width: 2, color: '#6250f9' },
        itemStyle: { color: '#6250f9' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(98,80,249,0.35)' },
            { offset: 1, color: 'rgba(98,80,249,0.05)' }
          ])
        }
      }
    ]
  }
}

const renderChart = async () => {
  await nextTick()
  if (!chartRef.value) return
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
  }
  chartInstance.setOption(buildOption(), true)
}

const fetchData = async () => {
  const { start, end } = getRange()
  loading.value = true
  try {
    const resp = await usageApi.getEvents({ start, end, limit: 5000 })
    events.value = resp?.data || []
    await renderChart()
  } finally {
    loading.value = false
  }
}

const onRangePresetChange = () => {
  if (rangePreset.value !== 'custom') {
    customRange.value = null
    fetchData()
  }
}

const handleResize = () => {
  chartInstance?.resize()
}

onMounted(async () => {
  await fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
  chartInstance = null
})
</script>

<style scoped lang="scss">
.usage-view {
  .header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .title {
    font-weight: 600;
    font-size: 14px;
    color: #303133;
  }

  .filters {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .chart {
    height: 360px;
    width: 100%;
  }
}
</style>
