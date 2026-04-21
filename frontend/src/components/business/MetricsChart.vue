<template>
  <div class="metrics-chart" ref="chartContainer">
    <div v-if="title" class="chart-title">{{ title }}</div>
    <div ref="chartRef" class="chart-content" :style="{ height: `${height}px` }"></div>
    <div v-if="showLegend && type !== 'gauge'" class="chart-legend">
      <div
        v-for="(item, index) in legendData"
        :key="index"
        class="legend-item"
      >
        <span class="legend-color" :style="{ backgroundColor: item.color }"></span>
        <span class="legend-label">{{ item.name }}</span>
        <span class="legend-value">{{ formatValue(item.value) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import type { ECharts, EChartsOption } from 'echarts'
import { registerTheme } from '@/utils/echarts/theme'

interface MetricData {
  name: string
  value: number
  description?: string
  color?: string
}

interface LegendItem {
  name: string
  value: number
  color: string
}

interface Props {
  data: MetricData[]
  title?: string
  type?: 'radar' | 'bar' | 'gauge' | 'line'
  height?: number
  showLegend?: boolean
  colors?: string[]
  maxValue?: number
  showValue?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'radar',
  height: 400,
  showLegend: true,
  colors: () => ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#00d4ff'],
  maxValue: 1,
  showValue: true
})

const emit = defineEmits<{
  (e: 'click', params: any): void
}>()

const chartRef = ref<HTMLElement>()
const chartContainer = ref<HTMLElement>()
let chartInstance: ECharts | null = null

const legendData = computed((): LegendItem[] => {
  return props.data.map((item, index) => ({
    name: item.name,
    value: item.value,
    color: item.color || props.colors[index % props.colors.length]
  }))
})

const getScoreColor = (score: number) => {
  if (score >= 0.8) return '#67c23a'
  if (score >= 0.6) return '#e6a23c'
  return '#f56c6c'
}

const formatValue = (value: number) => {
  if (value >= 1) {
    return value.toFixed(0)
  }
  return (value * 100).toFixed(1) + '%'
}

const getRadarOption = (): EChartsOption => {
  const indicator = props.data.map(item => ({
    name: item.name,
    max: props.maxValue
  }))

  return {
    tooltip: {
      trigger: 'item',
      confine: true,
      formatter: (params: any) => {
        const values = params.value
        let html = `<div style="font-weight:600;margin-bottom:8px;">${params.name}</div>`
        props.data.forEach((item, index) => {
          html += `<div>${item.name}: ${formatValue(values[index])}</div>`
        })
        return html
      }
    },
    radar: {
      indicator,
      center: ['50%', '55%'],
      radius: '65%'
    },
    series: [{
      type: 'radar',
      data: [{
        value: props.data.map(item => item.value),
        name: '评估指标',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: {
          width: 2,
          color: props.colors[0] || '#2563eb'
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `${props.colors[0] || '#2563eb'}80` },
            { offset: 1, color: `${props.colors[0] || '#2563eb'}20` }
          ])
        },
        itemStyle: {
          color: props.colors[0] || '#2563eb'
        }
      }]
    }]
  }
}

const getBarOption = (): EChartsOption => {
  return {
    tooltip: {
      trigger: 'axis',
      confine: true,
      axisPointer: {
        type: 'shadow'
      },
      formatter: (params: any) => {
        const item = params[0]
        return `<div style="font-weight:600;">${item.name}</div>
                <div>得分: ${formatValue(item.value)}</div>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.data.map(item => item.name),
      axisLabel: {
        color: '#606266',
        fontSize: 11,
        rotate: props.data.length > 6 ? 30 : 0
      },
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      }
    },
    yAxis: {
      type: 'value',
      max: props.maxValue,
      axisLabel: {
        color: '#909399',
        formatter: (value: number) => formatValue(value)
      },
      splitLine: {
        lineStyle: {
          color: '#ebeef5'
        }
      }
    },
    series: [{
      type: 'bar',
      data: props.data.map((item, index) => ({
        value: item.value,
        itemStyle: {
          color: item.color || props.colors[index % props.colors.length],
          borderRadius: [4, 4, 0, 0]
        }
      })),
      barWidth: '50%',
      label: props.showValue ? {
        show: true,
        position: 'top',
        formatter: (params: any) => formatValue(params.value),
        color: '#606266',
        fontSize: 12
      } : undefined
    }]
  }
}

const getGaugeOption = (): EChartsOption => {
  const avgValue = props.data.reduce((sum, item) => sum + item.value, 0) / props.data.length

  return {
    series: [{
      type: 'gauge',
      center: ['50%', '60%'],
      radius: '80%',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: props.maxValue,
      splitNumber: 10,
      itemStyle: {
        color: getScoreColor(avgValue)
      },
      progress: {
        show: true,
        width: 20
      },
      pointer: {
        show: false
      },
      axisLine: {
        lineStyle: {
          width: 20,
          color: [[1, '#ebeef5']]
        }
      },
      axisTick: {
        show: false
      },
      splitLine: {
        show: false
      },
      axisLabel: {
        show: false
      },
      anchor: {
        show: false
      },
      title: {
        show: false
      },
      detail: {
        valueAnimation: true,
        width: '60%',
        lineHeight: 40,
        borderRadius: 8,
        offsetCenter: [0, '-15%'],
        fontSize: 32,
        fontWeight: 'bolder',
        formatter: (value: number) => formatValue(value),
        color: getScoreColor(avgValue)
      },
      data: [{
        value: avgValue
      }]
    },
    {
      type: 'gauge',
      center: ['50%', '60%'],
      radius: '60%',
      startAngle: 200,
      endAngle: -20,
      min: 0,
      max: props.maxValue,
      itemStyle: {
        color: '#909399'
      },
      progress: {
        show: false
      },
      pointer: {
        show: false
      },
      axisLine: {
        show: false
      },
      axisTick: {
        show: false
      },
      splitLine: {
        show: false
      },
      axisLabel: {
        show: false
      },
      detail: {
        show: false
      },
      data: []
    }]
  }
}

const getLineOption = (): EChartsOption => {
  return {
    tooltip: {
      trigger: 'axis',
      confine: true,
      formatter: (params: any) => {
        const item = params[0]
        return `<div style="font-weight:600;">${item.name}</div>
                <div>得分: ${formatValue(item.value)}</div>`
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      top: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: props.data.map(item => item.name),
      axisLabel: {
        color: '#606266',
        fontSize: 11,
        rotate: props.data.length > 6 ? 30 : 0
      },
      axisLine: {
        lineStyle: {
          color: '#dcdfe6'
        }
      }
    },
    yAxis: {
      type: 'value',
      max: props.maxValue,
      axisLabel: {
        color: '#909399',
        formatter: (value: number) => formatValue(value)
      },
      splitLine: {
        lineStyle: {
          color: '#ebeef5'
        }
      }
    },
    series: [{
      type: 'line',
      data: props.data.map((item, index) => ({
        value: item.value,
        itemStyle: {
          color: item.color || props.colors[index % props.colors.length]
        }
      })),
      smooth: true,
      symbol: 'circle',
      symbolSize: 8,
      lineStyle: {
        width: 3,
        color: props.colors[0]
      },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${props.colors[0]}40` },
          { offset: 1, color: `${props.colors[0]}05` }
        ])
      },
      label: props.showValue ? {
        show: true,
        position: 'top',
        formatter: (params: any) => formatValue(params.value),
        color: '#606266',
        fontSize: 11
      } : undefined
    }]
  }
}

const getOption = (): EChartsOption => {
  switch (props.type) {
    case 'bar':
      return getBarOption()
    case 'gauge':
      return getGaugeOption()
    case 'line':
      return getLineOption()
    default:
      return getRadarOption()
  }
}

const initChart = () => {
  if (!chartRef.value) return

  registerTheme()
  chartInstance = echarts.init(chartRef.value, 'saas')
  chartInstance.setOption(getOption())

  chartInstance.on('click', (params) => {
    emit('click', params)
  })
}

const updateChart = () => {
  if (!chartInstance) return
  chartInstance.setOption(getOption(), true)
}

const resizeChart = () => {
  chartInstance?.resize()
}

watch(() => props.data, () => {
  nextTick(updateChart)
}, { deep: true })

watch(() => props.type, () => {
  nextTick(updateChart)
})

onMounted(() => {
  nextTick(initChart)
  window.addEventListener('resize', resizeChart)
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', resizeChart)
})

defineExpose({
  resize: resizeChart,
  getInstance: () => chartInstance
})
</script>

<style lang="scss" scoped>
.metrics-chart {
  background-color: var(--bg-card, #ffffff);
  border-radius: var(--radius-8, 8px);
  padding: 16px;

  .chart-title {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-1, #ebeef5);
  }

  .chart-content {
    width: 100%;
  }

  .chart-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 16px;
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border-1, #ebeef5);

    .legend-item {
      display: flex;
      align-items: center;
      gap: 8px;

      .legend-color {
        width: 12px;
        height: 12px;
        border-radius: 2px;
      }

      .legend-label {
        font-size: var(--font-14, 14px);
        color: var(--text-2, #606266);
      }

      .legend-value {
        font-size: var(--font-14, 14px);
        font-weight: var(--fw-600, 600);
        color: var(--text-1, #303133);
      }
    }
  }
}
</style>
