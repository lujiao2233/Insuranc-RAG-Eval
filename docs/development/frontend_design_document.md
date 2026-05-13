# RAG评估系统前端设计文档

## 目录
1. [系统架构概述](#1-系统架构概述)
2. [技术栈选型说明](#2-技术栈选型说明)
3. [组件设计与复用原则](#3-组件设计与复用原则)
4. [状态管理方案](#4-状态管理方案)
5. [路由配置策略](#5-路由配置策略)
6. [API接口交互规范](#6-api接口交互规范)
7. [响应式设计实现](#7-响应式设计实现)
8. [性能优化措施](#8-性能优化措施)
9. [错误处理机制](#9-错误处理机制)
10. [代码规范与质量保障](#10-代码规范与质量保障)

---

## 1. 系统架构概述

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        前端应用 (Vue 3)                          │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Views     │  │  Components │  │      Composables        │  │
│  │  (页面视图)  │  │  (UI组件)    │  │    (组合式函数)          │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Pinia Store (状态管理)                   │  │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐          │  │
│  │  │  auth   │ │document │ │testset  │ │evaluation│          │  │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                          │                                       │
│                          ▼                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    API Service Layer                       │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │              Axios HTTP Client                       │  │  │
│  │  │  • 请求拦截器 (Token注入)                             │  │  │
│  │  │  • 响应拦截器 (错误处理)                              │  │  │
│  │  └─────────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼ HTTP/REST
┌─────────────────────────────────────────────────────────────────┐
│                     后端 API (FastAPI)                           │
│  /api/v1/auth    /api/v1/documents   /api/v1/testsets          │
│  /api/v1/evaluations  /api/v1/reports  /api/v1/config          │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 功能模块划分

| 模块 | 功能描述 | 主要页面 |
|------|----------|----------|
| 认证模块 | 用户登录、注册、权限管理 | Login, Register |
| 文档管理 | 文档上传、列表、分析 | Documents, DocumentDetail |
| 测试集管理 | 测试集创建、问题管理 | TestSets, TestSetDetail |
| 评估执行 | 评估任务创建、进度监控 | Evaluations, EvaluationDetail |
| 报告查看 | 报告生成、下载、对比 | Reports, ReportDetail |
| 系统配置 | API配置、系统参数设置 | Configuration |

### 1.3 数据流图

```
用户操作 → View组件 → Action → API Service → 后端API
                ↓
           Pinia Store ← Response
                ↓
           View组件更新 ← State变化
```

---

## 2. 技术栈选型说明

### 2.1 核心技术栈

| 技术 | 版本 | 选型理由 |
|------|------|----------|
| Vue.js | 3.4+ | 组合式API、更好的TypeScript支持、性能优化 |
| TypeScript | 5.0+ | 类型安全、代码提示、重构友好 |
| Vite | 5.0+ | 快速开发服务器、优化的构建 |
| Pinia | 2.1+ | Vue官方推荐、简洁的API、TypeScript友好 |
| Vue Router | 4.2+ | 官方路由、支持组合式API |
| Element Plus | 2.4+ | 成熟的UI组件库、完善的文档 |
| Axios | 1.6+ | HTTP客户端、拦截器支持 |
| ECharts | 5.4+ | 数据可视化、图表展示 |
| VueUse | 10.0+ | 实用组合式函数集合 |

### 2.2 开发工具

| 工具 | 用途 |
|------|------|
| ESLint | 代码检查 |
| Prettier | 代码格式化 |
| Husky | Git钩子 |
| lint-staged | 暂存区代码检查 |

### 2.3 项目结构

```
frontend/
├── public/                 # 静态资源
├── src/
│   ├── api/               # API接口层
│   │   ├── index.ts       # Axios实例配置
│   │   ├── auth.ts        # 认证接口
│   │   ├── documents.ts   # 文档接口
│   │   ├── testsets.ts    # 测试集接口
│   │   ├── evaluations.ts # 评估接口
│   │   ├── reports.ts     # 报告接口
│   │   └── config.ts      # 配置接口
│   ├── assets/            # 资源文件
│   │   ├── styles/        # 全局样式
│   │   └── images/        # 图片资源
│   ├── components/        # 公共组件
│   │   ├── common/        # 通用组件
│   │   ├── layout/        # 布局组件
│   │   └── business/      # 业务组件
│   ├── composables/       # 组合式函数
│   │   ├── useAuth.ts
│   │   ├── useUpload.ts
│   │   └── usePolling.ts
│   ├── directives/        # 自定义指令
│   ├── router/            # 路由配置
│   │   └── index.ts
│   ├── stores/            # Pinia状态管理
│   │   ├── auth.ts
│   │   ├── document.ts
│   │   ├── testset.ts
│   │   ├── evaluation.ts
│   │   ├── report.ts
│   │   └── config.ts
│   ├── types/             # TypeScript类型定义
│   │   ├── api.ts
│   │   ├── models.ts
│   │   └── components.ts
│   ├── utils/             # 工具函数
│   │   ├── request.ts
│   │   ├── storage.ts
│   │   ├── format.ts
│   │   └── validate.ts
│   ├── views/             # 页面视图
│   │   ├── auth/
│   │   ├── documents/
│   │   ├── testsets/
│   │   ├── evaluations/
│   │   ├── reports/
│   │   └── config/
│   ├── App.vue
│   └── main.ts
├── .env.development       # 开发环境变量
├── .env.production        # 生产环境变量
├── vite.config.ts         # Vite配置
├── tsconfig.json          # TypeScript配置
└── package.json
```

---

## 3. 组件设计与复用原则

### 3.1 组件层次结构

```
App.vue
├── Layout/
│   ├── AppHeader.vue          # 顶部导航
│   ├── AppSidebar.vue         # 侧边栏菜单
│   └── AppContent.vue         # 内容区域
├── Common/
│   ├── Pagination.vue         # 分页组件
│   ├── SearchBar.vue          # 搜索栏
│   ├── FilterPanel.vue        # 筛选面板
│   ├── StatusBadge.vue        # 状态标签
│   ├── EmptyState.vue         # 空状态
│   ├── LoadingSpinner.vue     # 加载动画
│   └── ConfirmDialog.vue      # 确认对话框
├── Business/
│   ├── DocumentUploader.vue   # 文档上传
│   ├── QuestionEditor.vue     # 问题编辑器
│   ├── EvaluationProgress.vue # 评估进度
│   ├── MetricsChart.vue       # 指标图表
│   ├── ReportPreview.vue      # 报告预览
│   └── ConfigForm.vue         # 配置表单
└── Views/
    ├── LoginView.vue
    ├── DocumentsView.vue
    ├── TestSetsView.vue
    ├── EvaluationsView.vue
    ├── ReportsView.vue
    └── ConfigView.vue
```

### 3.2 组件设计原则

#### 3.2.1 单一职责原则
每个组件只负责一个功能，保持组件的简洁和可维护性。

```typescript
// 示例：StatusBadge组件 - 只负责显示状态
<template>
  <el-tag :type="tagType" :effect="effect">
    <slot>{{ displayText }}</slot>
  </el-tag>
</template>

<script setup lang="ts">
interface Props {
  status: 'pending' | 'running' | 'completed' | 'failed'
  size?: 'small' | 'default' | 'large'
}

const props = withDefaults(defineProps<Props>(), {
  size: 'default'
})

const statusConfig = {
  pending: { type: 'info', text: '待处理' },
  running: { type: 'warning', text: '执行中' },
  completed: { type: 'success', text: '已完成' },
  failed: { type: 'danger', text: '失败' }
}

const tagType = computed(() => statusConfig[props.status].type)
const displayText = computed(() => statusConfig[props.status].text)
</script>
```

#### 3.2.2 组合优于继承
使用组合式函数实现逻辑复用，而非组件继承。

```typescript
// composables/usePolling.ts - 轮询逻辑复用
export function usePolling(
  fetchFn: () => Promise<void>,
  interval: number = 3000,
  options: { immediate?: boolean; maxAttempts?: number } = {}
) {
  const isPolling = ref(false)
  const attempts = ref(0)
  let timer: number | null = null

  const start = () => {
    if (isPolling.value) return
    isPolling.value = true
    poll()
  }

  const poll = async () => {
    if (!isPolling.value) return
    
    try {
      await fetchFn()
      attempts.value++
      
      if (options.maxAttempts && attempts.value >= options.maxAttempts) {
        stop()
        return
      }
      
      timer = window.setTimeout(poll, interval)
    } catch (error) {
      stop()
      throw error
    }
  }

  const stop = () => {
    isPolling.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  onUnmounted(stop)

  if (options.immediate) {
    start()
  }

  return { isPolling, attempts, start, stop }
}
```

#### 3.2.3 Props向下，Events向上
遵循单向数据流原则。

```typescript
// DocumentUploader.vue
<template>
  <el-upload
    :action="uploadUrl"
    :headers="headers"
    :on-success="handleSuccess"
    :on-error="handleError"
    :before-upload="beforeUpload"
  >
    <el-button type="primary">上传文档</el-button>
    <template #tip>
      <div class="el-upload__tip">
        支持 PDF、DOCX、XLSX 格式，最大 50MB
      </div>
    </template>
  </el-upload>
</template>

<script setup lang="ts">
interface Props {
  uploadUrl: string
  maxSize?: number
  allowedTypes?: string[]
}

interface Emits {
  (e: 'success', file: UploadFile): void
  (e: 'error', error: Error): void
  (e: 'progress', percent: number): void
}

const props = withDefaults(defineProps<Props>(), {
  maxSize: 50 * 1024 * 1024,
  allowedTypes: () => ['.pdf', '.docx', '.xlsx']
})

const emit = defineEmits<Emits>()

const handleSuccess = (response: any, file: UploadFile) => {
  emit('success', { ...file, response })
}

const handleError = (error: Error) => {
  emit('error', error)
}
</script>
```

### 3.3 核心业务组件

#### 3.3.1 EvaluationProgress 组件

```vue
<template>
  <div class="evaluation-progress">
    <div class="progress-header">
      <span class="status-text">{{ statusText }}</span>
      <el-button 
        v-if="canCancel" 
        type="danger" 
        size="small"
        @click="handleCancel"
      >
        取消
      </el-button>
    </div>
    
    <el-progress 
      :percentage="progress" 
      :status="progressStatus"
      :stroke-width="20"
    />
    
    <div class="progress-details">
      <div class="detail-item">
        <span class="label">已评估:</span>
        <span class="value">{{ evaluatedCount }} / {{ totalCount }}</span>
      </div>
      <div class="detail-item">
        <span class="label">耗时:</span>
        <span class="value">{{ formatDuration(elapsedTime) }}</span>
      </div>
    </div>
    
    <div v-if="logs.length" class="progress-logs">
      <div 
        v-for="(log, index) in logs" 
        :key="index" 
        class="log-item"
      >
        {{ log }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { usePolling } from '@/composables/usePolling'

interface Props {
  taskId: string
  onComplete?: (result: any) => void
  onError?: (error: Error) => void
}

const props = defineProps<Props>()
const emit = defineEmits<{
  (e: 'complete', result: any): void
  (e: 'error', error: Error): void
  (e: 'cancel'): void
}>()

const progress = ref(0)
const status = ref<'pending' | 'running' | 'completed' | 'failed'>('pending')
const logs = ref<string[]>([])
const evaluatedCount = ref(0)
const totalCount = ref(0)
const elapsedTime = ref(0)

const statusText = computed(() => ({
  pending: '等待中...',
  running: '评估中...',
  completed: '评估完成',
  failed: '评估失败'
}[status.value]))

const progressStatus = computed(() => {
  if (status.value === 'completed') return 'success'
  if (status.value === 'failed') return 'exception'
  return undefined
})

const canCancel = computed(() => status.value === 'running')

const fetchTaskStatus = async () => {
  const response = await evaluationApi.getTaskStatus(props.taskId)
  
  progress.value = response.progress * 100
  status.value = response.status
  logs.value = response.logs || []
  evaluatedCount.value = response.evaluated_questions || 0
  totalCount.value = response.total_questions || 0
  
  if (status.value === 'completed') {
    stop()
    emit('complete', response.result)
  } else if (status.value === 'failed') {
    stop()
    emit('error', new Error(response.error || '评估失败'))
  }
}

const { start, stop } = usePolling(fetchTaskStatus, 2000, { immediate: true })

const handleCancel = () => {
  stop()
  emit('cancel')
}

const formatDuration = (seconds: number) => {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins}分${secs}秒`
}
</script>
```

#### 3.3.2 MetricsChart 组件

```vue
<template>
  <div class="metrics-chart" ref="chartRef"></div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import type { EChartsOption } from 'echarts'

interface MetricData {
  name: string
  value: number
  description?: string
}

interface Props {
  data: MetricData[]
  title?: string
  type?: 'radar' | 'bar' | 'gauge'
}

const props = withDefaults(defineProps<Props>(), {
  type: 'radar'
})

const chartRef = ref<HTMLElement>()
let chartInstance: echarts.ECharts | null = null

const getRadarOption = (): EChartsOption => ({
  title: {
    text: props.title,
    left: 'center'
  },
  tooltip: {
    trigger: 'item'
  },
  radar: {
    indicator: props.data.map(item => ({
      name: item.name,
      max: 1
    })),
    center: ['50%', '60%'],
    radius: '60%'
  },
  series: [{
    type: 'radar',
    data: [{
      value: props.data.map(item => item.value),
      name: '评估指标',
      areaStyle: {
        color: 'rgba(64, 158, 255, 0.3)'
      }
    }]
  }]
})

const getBarOption = (): EChartsOption => ({
  title: {
    text: props.title,
    left: 'center'
  },
  tooltip: {
    trigger: 'axis',
    axisPointer: { type: 'shadow' }
  },
  xAxis: {
    type: 'category',
    data: props.data.map(item => item.name)
  },
  yAxis: {
    type: 'value',
    max: 1
  },
  series: [{
    type: 'bar',
    data: props.data.map(item => ({
      value: item.value,
      itemStyle: {
        color: getScoreColor(item.value)
      }
    })),
    label: {
      show: true,
      position: 'top',
      formatter: '{c}'
    }
  }]
})

const getScoreColor = (score: number) => {
  if (score >= 0.8) return '#67C23A'
  if (score >= 0.6) return '#E6A23C'
  return '#F56C6C'
}

const initChart = () => {
  if (!chartRef.value) return
  
  chartInstance = echarts.init(chartRef.value)
  
  const option = props.type === 'radar' ? getRadarOption() : getBarOption()
  chartInstance.setOption(option)
}

const updateChart = () => {
  if (!chartInstance) return
  
  const option = props.type === 'radar' ? getRadarOption() : getBarOption()
  chartInstance.setOption(option)
}

watch(() => props.data, updateChart, { deep: true })

onMounted(() => {
  initChart()
  window.addEventListener('resize', () => chartInstance?.resize())
})

onUnmounted(() => {
  chartInstance?.dispose()
  window.removeEventListener('resize', () => chartInstance?.resize())
})
</script>

<style scoped>
.metrics-chart {
  width: 100%;
  height: 400px;
}
</style>
```

---

## 4. 状态管理方案

### 4.1 Pinia Store 架构

```
stores/
├── index.ts          # Store入口
├── auth.ts           # 认证状态
├── document.ts       # 文档状态
├── testset.ts        # 测试集状态
├── evaluation.ts     # 评估状态
├── report.ts         # 报告状态
└── config.ts         # 配置状态
```

### 4.2 状态管理流程图

```
┌─────────────────────────────────────────────────────────────┐
│                      Pinia Store                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                     State                            │    │
│  │  • data: 响应式数据                                   │    │
│  │  • loading: 加载状态                                  │    │
│  │  • error: 错误信息                                    │    │
│  │  • pagination: 分页信息                               │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Getters                            │    │
│  │  • filteredData: 过滤后的数据                        │    │
│  │  • hasData: 是否有数据                               │    │
│  │  • isLoading: 是否加载中                             │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   Actions                             │    │
│  │  • fetch(): 获取数据                                  │    │
│  │  • create(): 创建数据                                 │    │
│  │  • update(): 更新数据                                 │    │
│  │  • delete(): 删除数据                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 Store 实现示例

#### 4.3.1 认证 Store

```typescript
// stores/auth.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { tokenStorage } from '@/utils/storage'
import type { User, LoginForm, RegisterForm } from '@/types/models'

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<User | null>(null)
  const token = ref<string | null>(tokenStorage.get())
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  // Actions
  async function login(credentials: LoginForm) {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(credentials)
      token.value = response.access_token
      tokenStorage.set(response.access_token)
      
      await fetchCurrentUser()
      
      return true
    } catch (e: any) {
      error.value = e.message || '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterForm) {
    loading.value = true
    error.value = null
    
    try {
      await authApi.register(data)
      return await login({
        username: data.username,
        password: data.password
      })
    } catch (e: any) {
      error.value = e.message || '注册失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    
    try {
      const response = await authApi.getCurrentUser()
      user.value = response
    } catch (e) {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    tokenStorage.remove()
  }

  async function refreshToken() {
    if (!token.value) return false
    
    try {
      const response = await authApi.refreshToken()
      token.value = response.access_token
      tokenStorage.set(response.access_token)
      return true
    } catch (e) {
      logout()
      return false
    }
  }

  // 初始化时获取用户信息
  if (token.value) {
    fetchCurrentUser()
  }

  return {
    // State
    user,
    token,
    loading,
    error,
    
    // Getters
    isAuthenticated,
    isAdmin,
    username,
    
    // Actions
    login,
    register,
    logout,
    fetchCurrentUser,
    refreshToken
  }
})
```

#### 4.3.2 文档 Store

```typescript
// stores/document.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { documentApi } from '@/api/documents'
import type { Document, DocumentQuery } from '@/types/models'

export const useDocumentStore = defineStore('document', () => {
  // State
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    page: 1,
    size: 10,
    total: 0,
    pages: 0
  })
  const filters = ref<DocumentQuery>({
    status: undefined,
    is_analyzed: undefined
  })

  // Getters
  const hasDocuments = computed(() => documents.value.length > 0)
  const analyzedCount = computed(() => 
    documents.value.filter(d => d.is_analyzed).length
  )
  const unanalyzedCount = computed(() => 
    documents.value.filter(d => !d.is_analyzed).length
  )

  // Actions
  async function fetchDocuments(params?: Partial<DocumentQuery>) {
    loading.value = true
    error.value = null
    
    try {
      const query = { ...filters.value, ...params }
      const response = await documentApi.getDocuments({
        skip: (pagination.value.page - 1) * pagination.value.size,
        limit: pagination.value.size,
        ...query
      })
      
      documents.value = response.items
      pagination.value = {
        page: response.page,
        size: response.size,
        total: response.total,
        pages: response.pages
      }
    } catch (e: any) {
      error.value = e.message || '获取文档列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: string) {
    loading.value = true
    error.value = null
    
    try {
      currentDocument.value = await documentApi.getDocument(id)
    } catch (e: any) {
      error.value = e.message || '获取文档详情失败'
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File) {
    uploading.value = true
    error.value = null
    
    try {
      const document = await documentApi.uploadDocument(file)
      documents.value.unshift(document)
      pagination.value.total++
      return document
    } catch (e: any) {
      error.value = e.message || '上传文档失败'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(id: string) {
    try {
      await documentApi.deleteDocument(id)
      documents.value = documents.value.filter(d => d.id !== id)
      pagination.value.total--
    } catch (e: any) {
      error.value = e.message || '删除文档失败'
      throw e
    }
  }

  function setPage(page: number) {
    pagination.value.page = page
    fetchDocuments()
  }

  function setFilters(newFilters: Partial<DocumentQuery>) {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.page = 1
    fetchDocuments()
  }

  function clearFilters() {
    filters.value = { status: undefined, is_analyzed: undefined }
    pagination.value.page = 1
    fetchDocuments()
  }

  return {
    // State
    documents,
    currentDocument,
    loading,
    uploading,
    error,
    pagination,
    filters,
    
    // Getters
    hasDocuments,
    analyzedCount,
    unanalyzedCount,
    
    // Actions
    fetchDocuments,
    fetchDocument,
    uploadDocument,
    deleteDocument,
    setPage,
    setFilters,
    clearFilters
  }
})
```

#### 4.3.3 评估 Store

```typescript
// stores/evaluation.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { evaluationApi } from '@/api/evaluations'
import type { Evaluation, EvaluationCreate, EvaluationResult } from '@/types/models'

export const useEvaluationStore = defineStore('evaluation', () => {
  // State
  const evaluations = ref<Evaluation[]>([])
  const currentEvaluation = ref<Evaluation | null>(null)
  const evaluationResults = ref<EvaluationResult[]>([])
  const taskStatus = ref<{
    taskId: string
    status: string
    progress: number
    logs: string[]
  } | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const completedEvaluations = computed(() =>
    evaluations.value.filter(e => e.status === 'completed')
  )
  const runningEvaluations = computed(() =>
    evaluations.value.filter(e => e.status === 'running')
  )

  // Actions
  async function fetchEvaluations(params?: { status?: string }) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.getEvaluations(params)
      evaluations.value = response.items
    } catch (e: any) {
      error.value = e.message || '获取评估列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchEvaluation(id: string) {
    loading.value = true
    error.value = null
    
    try {
      currentEvaluation.value = await evaluationApi.getEvaluation(id)
    } catch (e: any) {
      error.value = e.message || '获取评估详情失败'
    } finally {
      loading.value = false
    }
  }

  async function createEvaluation(data: EvaluationCreate) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.createEvaluation(data)
      
      taskStatus.value = {
        taskId: response.task_id,
        status: 'pending',
        progress: 0,
        logs: []
      }
      
      return response
    } catch (e: any) {
      error.value = e.message || '创建评估失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskStatus(taskId: string) {
    try {
      const status = await evaluationApi.getTaskStatus(taskId)
      taskStatus.value = {
        taskId,
        status: status.status,
        progress: status.progress || 0,
        logs: status.logs || []
      }
      return status
    } catch (e: any) {
      error.value = e.message || '获取任务状态失败'
      throw e
    }
  }

  async function fetchEvaluationResults(evaluationId: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.getEvaluationResults(evaluationId)
      evaluationResults.value = response.items
    } catch (e: any) {
      error.value = e.message || '获取评估结果失败'
    } finally {
      loading.value = false
    }
  }

  async function deleteEvaluation(id: string) {
    try {
      await evaluationApi.deleteEvaluation(id)
      evaluations.value = evaluations.value.filter(e => e.id !== id)
    } catch (e: any) {
      error.value = e.message || '删除评估失败'
      throw e
    }
  }

  function clearTaskStatus() {
    taskStatus.value = null
  }

  return {
    // State
    evaluations,
    currentEvaluation,
    evaluationResults,
    taskStatus,
    loading,
    error,
    
    // Getters
    completedEvaluations,
    runningEvaluations,
    
    // Actions
    fetchEvaluations,
    fetchEvaluation,
    createEvaluation,
    fetchTaskStatus,
    fetchEvaluationResults,
    deleteEvaluation,
    clearTaskStatus
  }
})
```

---

## 5. 路由配置策略

### 5.1 路由结构

```typescript
// router/index.ts
import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false, title: '注册' }
  },
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '仪表盘' }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/documents/DocumentsView.vue'),
        meta: { title: '文档管理' }
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/documents/DocumentDetailView.vue'),
        meta: { title: '文档详情' }
      },
      {
        path: 'testsets',
        name: 'TestSets',
        component: () => import('@/views/testsets/TestSetsView.vue'),
        meta: { title: '测试集管理' }
      },
      {
        path: 'testsets/:id',
        name: 'TestSetDetail',
        component: () => import('@/views/testsets/TestSetDetailView.vue'),
        meta: { title: '测试集详情' }
      },
      {
        path: 'evaluations',
        name: 'Evaluations',
        component: () => import('@/views/evaluations/EvaluationsView.vue'),
        meta: { title: '评估管理' }
      },
      {
        path: 'evaluations/:id',
        name: 'EvaluationDetail',
        component: () => import('@/views/evaluations/EvaluationDetailView.vue'),
        meta: { title: '评估详情' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportsView.vue'),
        meta: { title: '报告中心' }
      },
      {
        path: 'reports/:id',
        name: 'ReportDetail',
        component: () => import('@/views/reports/ReportDetailView.vue'),
        meta: { title: '报告详情' }
      },
      {
        path: 'config',
        name: 'Configuration',
        component: () => import('@/views/config/ConfigView.vue'),
        meta: { title: '系统配置' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  // 设置页面标题
  document.title = `${to.meta.title || 'RAG评估系统'} - RAG评估系统`
  
  // 检查认证
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  // 已登录用户访问登录页，重定向到首页
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

export default router
```

### 5.2 路由元信息

```typescript
// types/router.d.ts
import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    permissions?: string[]
    keepAlive?: boolean
    breadcrumb?: { title: string; path?: string }[]
  }
}
```

---

## 6. API接口交互规范

### 6.1 Axios 实例配置

```typescript
// api/index.ts
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, AxiosError } from 'axios'
import { ElMessage } from 'element-plus'
import { tokenStorage } from '@/utils/storage'
import router from '@/router'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const instance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
instance.interceptors.request.use(
  (config) => {
    const token = tokenStorage.get()
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error: AxiosError<any>) => {
    const { response, config } = error
    
    if (!response) {
      ElMessage.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }
    
    const { status, data } = response
    
    switch (status) {
      case 401:
        // Token过期，尝试刷新
        if (config.url !== '/auth/refresh-token') {
          try {
            const authStore = await import('@/stores/auth').then(m => m.useAuthStore())
            const refreshed = await authStore.refreshToken()
            if (refreshed && config.headers) {
              config.headers.Authorization = `Bearer ${tokenStorage.get()}`
              return instance.request(config)
            }
          } catch (e) {
            // 刷新失败，跳转登录
          }
        }
        tokenStorage.remove()
        router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
        ElMessage.error('登录已过期，请重新登录')
        break
        
      case 403:
        ElMessage.error('没有权限执行此操作')
        break
        
      case 404:
        ElMessage.error(data?.detail || '请求的资源不存在')
        break
        
      case 422:
        ElMessage.error(data?.detail || '请求参数错误')
        break
        
      case 500:
        ElMessage.error(data?.detail || '服务器内部错误')
        break
        
      default:
        ElMessage.error(data?.detail || `请求失败 (${status})`)
    }
    
    return Promise.reject(error)
  }
)

export default instance
```

### 6.2 API 模块封装

```typescript
// api/documents.ts
import request from './index'
import type { Document, PaginatedResponse } from '@/types/models'

export const documentApi = {
  // 获取文档列表
  getDocuments(params: {
    skip?: number
    limit?: number
    status?: string
    is_analyzed?: boolean
  }): Promise<PaginatedResponse<Document>> {
    return request.get('/documents/', { params })
  },

  // 获取单个文档
  getDocument(id: string): Promise<Document> {
    return request.get(`/documents/${id}`)
  },

  // 上传文档
  uploadDocument(file: File): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 批量上传
  uploadDocumentsBatch(files: File[]): Promise<Document[]> {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    return request.post('/documents/upload-batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  // 删除文档
  deleteDocument(id: string): Promise<void> {
    return request.delete(`/documents/${id}`)
  },

  // 下载文档
  downloadDocument(id: string): Promise<Blob> {
    return request.get(`/documents/${id}/download`, {
      responseType: 'blob'
    })
  },

  // 获取统计信息
  getStats(): Promise<{
    total_documents: number
    analyzed_documents: number
    unanalyzed_documents: number
    type_distribution: Record<string, number>
  }> {
    return request.get('/documents/stats/summary')
  }
}
```

```typescript
// api/evaluations.ts
import request from './index'
import type { Evaluation, EvaluationCreate, EvaluationResult } from '@/types/models'

export const evaluationApi = {
  // 获取评估列表
  getEvaluations(params?: { skip?: number; limit?: number; status?: string }): Promise<{
    items: Evaluation[]
    total: number
  }> {
    return request.get('/evaluations/', { params })
  },

  // 获取评估详情
  getEvaluation(id: string): Promise<Evaluation> {
    return request.get(`/evaluations/${id}`)
  },

  // 创建评估
  createEvaluation(data: EvaluationCreate): Promise<{
    id: string
    task_id: string
    status: string
    message: string
  }> {
    return request.post('/evaluations/', data)
  },

  // 获取任务状态
  getTaskStatus(taskId: string): Promise<{
    task_id: string
    status: string
    progress: number
    logs: string[]
    result?: any
    error?: string
  }> {
    return request.get(`/evaluations/task/${taskId}`)
  },

  // 获取评估结果
  getEvaluationResults(evaluationId: string, params?: {
    skip?: number
    limit?: number
  }): Promise<{
    evaluation_id: string
    total: number
    items: EvaluationResult[]
  }> {
    return request.get(`/evaluations/${evaluationId}/results`, { params })
  },

  // 获取评估摘要
  getEvaluationSummary(evaluationId: string): Promise<{
    evaluation_id: string
    status: string
    total_questions: number
    evaluated_questions: number
    evaluation_time: number
    overall_metrics: Record<string, any>
  }> {
    return request.get(`/evaluations/${evaluationId}/summary`)
  },

  // 删除评估
  deleteEvaluation(id: string): Promise<void> {
    return request.delete(`/evaluations/${id}`)
  }
}
```

### 6.3 类型定义

```typescript
// types/models.ts
export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user'
  full_name?: string
  created_at: string
  updated_at?: string
  last_login?: string
  is_active: boolean
}

export interface Document {
  id: string
  user_id?: string
  filename: string
  file_path: string
  file_type: string
  file_size: number
  page_count?: number
  status: 'active' | 'inactive' | 'processing'
  is_analyzed: boolean
  doc_metadata?: Record<string, any>
  outline?: Record<string, any>
  upload_time: string
  analyzed_at?: string
  created_at: string
  updated_at?: string
}

export interface TestSet {
  id: string
  document_id: string
  user_id?: string
  name: string
  description?: string
  question_count: number
  question_types?: Record<string, number>
  generation_method: string
  file_path?: string
  metadata?: Record<string, any>
  create_time: string
  created_at: string
  updated_at?: string
}

export interface Question {
  id: string
  testset_id: string
  question: string
  question_type: 'factual' | 'reasoning' | 'creative'
  category_major?: string
  category_minor?: string
  expected_answer?: string
  answer?: string
  context?: string
  metadata?: Record<string, any>
  created_at: string
  updated_at?: string
}

export interface Evaluation {
  id: string
  user_id?: string
  testset_id?: string
  evaluation_method: 'ragas_official' | 'deepeval'
  total_questions: number
  evaluated_questions: number
  evaluation_time?: number
  timestamp: string
  evaluation_metrics?: string[]
  overall_metrics?: Record<string, any>
  eval_config?: Record<string, any>
  status: 'pending' | 'running' | 'completed' | 'failed'
  error_message?: string
  created_at: string
  updated_at?: string
}

export interface EvaluationResult {
  id: string
  evaluation_id: string
  question_id?: string
  question_text: string
  expected_answer?: string
  generated_answer?: string
  context?: string
  metrics?: Record<string, number>
  created_at: string
  updated_at?: string
}

export interface Configuration {
  id: string
  user_id: string
  config_key: string
  config_value?: string
  description?: string
  created_at: string
  updated_at?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
  pages: number
}
```

---

## 7. 响应式设计实现

### 7.1 断点设计

```scss
// assets/styles/_variables.scss
$breakpoints: (
  xs: 576px,
  sm: 768px,
  md: 992px,
  lg: 1200px,
  xl: 1920px
);

@mixin respond-to($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (max-width: map-get($breakpoints, $breakpoint)) {
      @content;
    }
  }
}

@mixin respond-from($breakpoint) {
  @if map-has-key($breakpoints, $breakpoint) {
    @media (min-width: map-get($breakpoints, $breakpoint) + 1) {
      @content;
    }
  }
}
```

### 7.2 响应式布局组件

```vue
<!-- components/layout/MainLayout.vue -->
<template>
  <el-container class="main-layout">
    <!-- 侧边栏 -->
    <el-aside 
      :width="isCollapsed ? '64px' : '220px'"
      class="sidebar"
    >
      <div class="logo">
        <img src="@/assets/images/logo.png" alt="Logo" />
        <span v-show="!isCollapsed">RAG评估系统</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        router
      >
        <el-menu-item index="/dashboard">
          <el-icon><HomeFilled /></el-icon>
          <template #title>仪表盘</template>
        </el-menu-item>
        
        <el-menu-item index="/documents">
          <el-icon><Document /></el-icon>
          <template #title>文档管理</template>
        </el-menu-item>
        
        <el-menu-item index="/testsets">
          <el-icon><Collection /></el-icon>
          <template #title>测试集</template>
        </el-menu-item>
        
        <el-menu-item index="/evaluations">
          <el-icon><DataAnalysis /></el-icon>
          <template #title>评估管理</template>
        </el-menu-item>
        
        <el-menu-item index="/reports">
          <el-icon><Document /></el-icon>
          <template #title>报告中心</template>
        </el-menu-item>
        
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <template #title>系统配置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <!-- 主内容区 -->
    <el-container>
      <!-- 顶部导航 -->
      <el-header class="header">
        <div class="header-left">
          <el-button 
            :icon="isCollapsed ? Expand : Fold"
            @click="toggleSidebar"
            text
          />
          <el-breadcrumb separator="/">
            <el-breadcrumb-item 
              v-for="item in breadcrumbs" 
              :key="item.path"
              :to="item.path"
            >
              {{ item.title }}
            </el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32" :icon="UserFilled" />
              <span class="username">{{ authStore.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人中心</el-dropdown-item>
                <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
      <!-- 内容区域 -->
      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <keep-alive :include="cachedViews">
              <component :is="Component" />
            </keep-alive>
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { HomeFilled, Document, Collection, DataAnalysis, Setting, UserFilled, Expand, Fold } from '@element-plus/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const cachedViews = ref(['Documents', 'TestSets', 'Evaluations', 'Reports'])

const activeMenu = computed(() => route.path)

const breadcrumbs = computed(() => {
  const matched = route.matched.filter(item => item.meta.title)
  return matched.map(item => ({
    path: item.path,
    title: item.meta.title as string
  }))
})

const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value
}

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}

// 响应式处理
const handleResize = () => {
  if (window.innerWidth < 768) {
    isCollapsed.value = true
  }
}

onMounted(() => {
  window.addEventListener('resize', handleResize)
  handleResize()
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
})
</script>

<style lang="scss" scoped>
.main-layout {
  height: 100vh;
  
  .sidebar {
    background-color: #304156;
    transition: width 0.3s;
    
    .logo {
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 18px;
      font-weight: bold;
      
      img {
        width: 32px;
        height: 32px;
        margin-right: 8px;
      }
    }
    
    .el-menu {
      border-right: none;
      background-color: transparent;
    }
  }
  
  .header {
    background-color: #fff;
    box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    
    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;
    }
    
    .header-right {
      .user-info {
        display: flex;
        align-items: center;
        gap: 8px;
        cursor: pointer;
      }
    }
  }
  
  .main-content {
    background-color: #f5f7fa;
    padding: 20px;
    overflow-y: auto;
  }
}

// 响应式样式
@include respond-to(sm) {
  .main-layout {
    .sidebar {
      position: fixed;
      left: 0;
      top: 0;
      height: 100vh;
      z-index: 1000;
    }
    
    .header {
      .username {
        display: none;
      }
    }
  }
}

// 过渡动画
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
```

---

## 8. 性能优化措施

### 8.1 代码分割

```typescript
// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'element-plus': ['element-plus'],
          'echarts': ['echarts'],
          'vendor': ['vue', 'vue-router', 'pinia']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
```

### 8.2 懒加载策略

```typescript
// 路由懒加载
const routes = [
  {
    path: '/documents',
    component: () => import(
      /* webpackChunkName: "documents" */
      '@/views/documents/DocumentsView.vue'
    )
  }
]

// 组件懒加载
const MetricsChart = defineAsyncComponent(() =>
  import('@/components/business/MetricsChart.vue')
)
```

### 8.3 虚拟滚动

```vue
<!-- 大列表虚拟滚动 -->
<template>
  <el-table-v2
    :columns="columns"
    :data="data"
    :width="700"
    :height="400"
    :row-height="50"
    fixed
  />
</template>
```

### 8.4 图片优化

```typescript
// composables/useImageLazy.ts
export function useImageLazy() {
  const observer = ref<IntersectionObserver | null>(null)
  
  const observe = (el: HTMLImageElement) => {
    if (!observer.value) {
      observer.value = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement
            img.src = img.dataset.src || ''
            observer.value?.unobserve(img)
          }
        })
      })
    }
    observer.value.observe(el)
  }
  
  onUnmounted(() => {
    observer.value?.disconnect()
  })
  
  return { observe }
}
```

### 8.5 缓存策略

```typescript
// composables/useCache.ts
export function useCache<T>(key: string, fetchFn: () => Promise<T>, ttl: number = 5 * 60 * 1000) {
  const cache = ref<Map<string, { data: T; timestamp: number }>>(new Map())
  
  const get = async (): Promise<T> => {
    const cached = cache.value.get(key)
    
    if (cached && Date.now() - cached.timestamp < ttl) {
      return cached.data
    }
    
    const data = await fetchFn()
    cache.value.set(key, { data, timestamp: Date.now() })
    
    return data
  }
  
  const invalidate = () => {
    cache.value.delete(key)
  }
  
  return { get, invalidate }
}
```

---

## 9. 错误处理机制

### 9.1 全局错误处理

```typescript
// main.ts
import { createApp } from 'vue'
import App from './App.vue'

const app = createApp(App)

// 全局错误处理
app.config.errorHandler = (err, instance, info) => {
  console.error('Global error:', err)
  console.error('Component:', instance)
  console.error('Info:', info)
  
  // 上报错误
  // reportError(err, instance, info)
}

// Promise未捕获错误
window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled rejection:', event.reason)
  event.preventDefault()
})

app.mount('#app')
```

### 9.2 错误边界组件

```vue
<!-- components/common/ErrorBoundary.vue -->
<template>
  <slot v-if="!error" />
  <div v-else class="error-boundary">
    <el-result
      icon="error"
      title="出错了"
      :sub-title="error.message"
    >
      <template #extra>
        <el-button type="primary" @click="resetError">
          重试
        </el-button>
      </template>
    </el-result>
  </div>
</template>

<script setup lang="ts">
const error = ref<Error | null>(null)

const resetError = () => {
  error.value = null
}

onErrorCaptured((err) => {
  error.value = err
  return false
})
</script>
```

### 9.3 API错误处理

```typescript
// utils/error.ts
export class ApiError extends Error {
  constructor(
    public status: number,
    public message: string,
    public detail?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export function handleApiError(error: unknown): never {
  if (error instanceof AxiosError) {
    const { response } = error
    throw new ApiError(
      response?.status || 0,
      response?.data?.detail || '请求失败',
      response?.data
    )
  }
  throw error
}
```

---

## 10. 代码规范与质量保障

### 10.1 ESLint 配置

```javascript
// .eslintrc.cjs
module.exports = {
  root: true,
  env: {
    browser: true,
    es2021: true,
    node: true
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended',
    'plugin:@typescript-eslint/recommended',
    '@vue/eslint-config-typescript',
    '@vue/eslint-config-prettier'
  ],
  parserOptions: {
    ecmaVersion: 'latest',
    parser: '@typescript-eslint/parser',
    sourceType: 'module'
  },
  plugins: ['vue', '@typescript-eslint'],
  rules: {
    'vue/multi-word-component-names': 'off',
    'vue/no-unused-vars': 'error',
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/no-explicit-any': 'warn',
    'no-console': process.env.NODE_ENV === 'production' ? 'warn' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'warn' : 'off'
  }
}
```

### 10.2 Prettier 配置

```javascript
// .prettierrc
module.exports = {
  semi: false,
  singleQuote: true,
  tabWidth: 2,
  trailingComma: 'none',
  printWidth: 100,
  vueIndentScriptAndStyle: true,
  endOfLine: 'lf'
}
```

### 10.3 Git Hooks

```json
// package.json
{
  "scripts": {
    "lint": "eslint . --ext .vue,.js,.jsx,.cjs,.mjs,.ts,.tsx --fix",
    "format": "prettier --write src/"
  },
  "lint-staged": {
    "*.{vue,js,ts}": ["eslint --fix", "prettier --write"]
  }
}
```

### 10.4 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `DocumentUploader.vue` |
| 组合式函数 | camelCase + use前缀 | `usePolling.ts` |
| Store文件 | camelCase | `document.ts` |
| API文件 | camelCase | `documents.ts` |
| 类型文件 | camelCase | `models.ts` |
| CSS类名 | kebab-case | `.document-list` |
| 常量 | UPPER_SNAKE_CASE | `API_BASE_URL` |

### 10.5 目录规范

```
feature/
├── FeatureView.vue      # 页面组件
├── FeatureDetail.vue    # 详情组件
├── components/          # 页面专属组件
│   └── FeatureCard.vue
├── composables/         # 页面专属组合函数
│   └── useFeature.ts
└── types.ts             # 页面专属类型
```

---

## 附录

### A. 环境变量配置

```env
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_APP_TITLE=RAG评估系统

# .env.production
VITE_API_BASE_URL=/api/v1
VITE_APP_TITLE=RAG评估系统
```

### B. 主要依赖版本

```json
{
  "dependencies": {
    "vue": "^3.4.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "element-plus": "^2.4.0",
    "axios": "^1.6.0",
    "echarts": "^5.4.0",
    "@vueuse/core": "^10.0.0"
  },
  "devDependencies": {
    "typescript": "^5.0.0",
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^5.0.0",
    "eslint": "^8.0.0",
    "prettier": "^3.0.0",
    "sass": "^1.69.0"
  }
}
```

### C. 快速启动命令

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 代码检查
npm run lint

# 代码格式化
npm run format
```

---

**文档版本**: 1.0.0  
**最后更新**: 2026-03-20  
**维护团队**: RAG评估系统开发组
