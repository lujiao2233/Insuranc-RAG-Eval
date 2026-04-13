<template>
  <div class="dashboard-view">
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff;">
              <el-icon :size="24"><Document /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalDocuments }}</div>
              <div class="stat-label">文档总数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a;">
              <el-icon :size="24"><Collection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalTestsets }}</div>
              <div class="stat-label">测试集</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c;">
              <el-icon :size="24"><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalEvaluations }}</div>
              <div class="stat-label">评估任务</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #9c27b0;">
              <el-icon :size="24"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalTokens }}</div>
              <div class="stat-label">消耗 Token</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c;">
              <el-icon :size="24"><Cpu /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalCalls }}</div>
              <div class="stat-label">API 调用次数</div>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="4">
        <el-card class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #00bcd4;">
              <el-icon :size="24"><Timer /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.avgLatency }} ms</div>
              <div class="stat-label">平均耗时</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="module-row">
      <el-col :span="24">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>快捷操作</span>
            </div>
          </template>
          <div class="quick-actions">
            <el-button type="primary" @click="$router.push('/documents')">
              <el-icon><Upload /></el-icon>
              上传文档
            </el-button>
            <el-button type="success" @click="$router.push('/testsets')">
              <el-icon><Collection /></el-icon>
              创建测试集
            </el-button>
            <el-button type="warning" @click="$router.push('/evaluations')">
              <el-icon><DataLine /></el-icon>
              开始评估
            </el-button>
            <el-button type="info" @click="$router.push('/reports')">
              <el-icon><DocumentCopy /></el-icon>
              查看报告
            </el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="module-row">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近测试集</span>
              <el-link type="primary" @click="$router.push('/testsets')">查看全部</el-link>
            </div>
          </template>
          <el-table :data="recentTestsets" style="width: 100%">
            <el-table-column prop="name" label="测试集名称" />
            <el-table-column prop="question_count" label="问题数" width="90" />
            <el-table-column prop="create_time" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.create_time) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
      
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>最近评估</span>
              <el-link type="primary" @click="$router.push('/evaluations')">查看全部</el-link>
            </div>
          </template>
          <el-table :data="recentEvaluations" style="width: 100%">
            <el-table-column prop="testset_name" label="测试集名称" min-width="180">
              <template #default="{ row }">
                {{ row.testset_name || '未知测试集' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ getStatusText(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at || row.timestamp) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Document, Collection, DataLine, Upload, DocumentCopy, Coin, Timer, Cpu } from '@element-plus/icons-vue'
import { documentApi } from '@/api/documents'
import { evaluationApi } from '@/api/evaluations'
import { testsetApi } from '@/api/testsets'
import { usageApi } from '@/api/usage'
import { formatDate, formatDateTime } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { Evaluation, TestSet } from '@/types'

const authStore = useAuthStore()

const stats = ref({
  totalDocuments: 0,
  totalTestsets: 0,
  totalEvaluations: 0,
  totalTokens: 0,
  totalCalls: 0,
  avgLatency: 0
})

const recentTestsets = ref<TestSet[]>([])
const recentEvaluations = ref<Evaluation[]>([])

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
    running: '进行中',
    pending: '待处理',
    failed: '失败'
  }
  return texts[status] || status
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

onMounted(() => {
  fetchDashboardData()
})
</script>

<style lang="scss" scoped>
.dashboard-view {
  .stats-row {
    margin-bottom: 4px;
  }

  .module-row {
    margin-top: 20px;
  }

  .stat-card {
    .stat-content {
      display: flex;
      align-items: center;
      
      .stat-icon {
        width: 56px;
        height: 56px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: #fff;
        margin-right: 16px;
      }
      
      .stat-info {
        .stat-value {
          font-size: 28px;
          font-weight: bold;
          color: #303133;
        }
        
        .stat-label {
          font-size: 14px;
          color: #909399;
          margin-top: 4px;
        }
      }
    }
  }
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .quick-actions {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }
}
</style>
