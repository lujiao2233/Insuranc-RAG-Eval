<template>
  <div class="page dashboard-page">
    <DashboardStats 
      class="section" 
      :stats="stats" 
      @click-usage="goUsage" 
    />
    
    <DashboardActions 
      class="section" 
      :routes="routes"
      @navigate="handleNavigate" 
    />
    
    <DashboardRecentLists 
      class="section"
      :routes="routes"
      :recent-testsets="recentTestsets" 
      :recent-evaluations="recentEvaluations" 
      @navigate="handleNavigate" 
    />
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { documentApi } from '@/api/documents'
import { evaluationApi } from '@/api/evaluations'
import { testsetApi } from '@/api/testsets'
import { usageApi } from '@/api/usage'
import { useAuthStore } from '@/stores/auth'
import type { Evaluation, TestSet } from '@/types'

import DashboardStats from '@/components/business/dashboard/DashboardStats.vue'
import DashboardActions from '@/components/business/dashboard/DashboardActions.vue'
import DashboardRecentLists from '@/components/business/dashboard/DashboardRecentLists.vue'

const authStore = useAuthStore()
const router = useRouter()

// 集中管理路由路径
const routes = {
  USAGE: '/usage',
  DOCUMENTS: '/documents',
  TESTSETS: '/testsets',
  EVALUATIONS: '/evaluations',
  REPORTS: '/reports'
}

export interface DashboardStatsModel {
  totalDocuments: number
  totalTestsets: number
  totalEvaluations: number
  totalTokens: number
  totalCalls: number
  avgLatency: number
}

const stats = ref<DashboardStatsModel>({
  totalDocuments: 0,
  totalTestsets: 0,
  totalEvaluations: 0,
  totalTokens: 0,
  totalCalls: 0,
  avgLatency: 0
})

const recentTestsets = ref<TestSet[]>([])
const recentEvaluations = ref<Evaluation[]>([])

const goUsage = () => {
  router.push(routes.USAGE)
}

const handleNavigate = (path: string) => {
  router.push(path)
}

const fetchDashboardData = async () => {
  if (!authStore.isAuthenticated) {
    return
  }
  
  try {
    const [docStatsRes, testsetRes, evalRes, usageRes] = await Promise.allSettled([
      documentApi.getStats(),
      testsetApi.getTestSets({ limit: 5 }),
      evaluationApi.getEvaluations({ limit: 5 }),
      usageApi.getStats(30)
    ])
    
    if (docStatsRes.status === 'fulfilled') {
      stats.value.totalDocuments = docStatsRes.value.total_documents
    } else {
      stats.value.totalDocuments = 0
    }
    
    if (testsetRes.status === 'fulfilled') {
      stats.value.totalTestsets = testsetRes.value.total
      recentTestsets.value = testsetRes.value.items
    } else {
      stats.value.totalTestsets = 0
      recentTestsets.value = []
    }
    
    if (evalRes.status === 'fulfilled') {
      stats.value.totalEvaluations = evalRes.value.total
      recentEvaluations.value = evalRes.value.items
    } else {
      stats.value.totalEvaluations = 0
      recentEvaluations.value = []
    }
    
    if (usageRes.status === 'fulfilled') {
      stats.value.totalTokens = usageRes.value.data?.summary?.total_tokens || 0
      stats.value.totalCalls = usageRes.value.data?.summary?.total_calls || 0
      
      // Calculate overall average latency from module stats
      const modules = usageRes.value.data?.modules || []
      if (modules.length > 0) {
        const totalCalls = modules.reduce((sum, m) => sum + m.calls, 0)
        const totalWeightedLatency = modules.reduce((sum, m) => sum + (m.avg_latency * m.calls), 0)
        stats.value.avgLatency = totalCalls > 0 ? Math.round(totalWeightedLatency / totalCalls) : 0
      } else {
        stats.value.avgLatency = 0
      }
    } else {
      stats.value.totalTokens = 0
      stats.value.totalCalls = 0
      stats.value.avgLatency = 0
    }
    
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  }
}

watch(
  () => authStore.isAuthenticated,
  (isAuthenticated) => {
    if (isAuthenticated) {
      fetchDashboardData()
    }
  },
  { immediate: true }
)
</script>

<style lang="scss" scoped>
.dashboard-page {
  /* Dashboard 专属布局样式可放在这里，目前均已通过全局 class (.page, .section) 解决 */
}
</style>
