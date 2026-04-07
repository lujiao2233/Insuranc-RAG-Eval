<template>
  <div class="dashboard-view">
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :sm="12" :md="8">
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
      
      <el-col :xs="24" :sm="12" :md="8">
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
      
      <el-col :xs="24" :sm="12" :md="8">
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
            <el-table-column prop="id" label="ID" width="200">
              <template #default="{ row }">
                {{ row.id.substring(0, 8) }}...
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="180">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
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
import { Document, Collection, DataLine, Upload, DocumentCopy } from '@element-plus/icons-vue'
import { documentApi } from '@/api/documents'
import { evaluationApi } from '@/api/evaluations'
import { testsetApi } from '@/api/testsets'
import { formatDate } from '@/utils/format'
import { useAuthStore } from '@/stores/auth'
import type { Evaluation, TestSet } from '@/types'

const authStore = useAuthStore()

const stats = ref({
  totalDocuments: 0,
  totalTestsets: 0,
  totalEvaluations: 0
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

const fetchDashboardData = async () => {
  if (!authStore.isAuthenticated) {
    return
  }
  
  try {
    const [docStatsRes, testsetRes, evalRes] = await Promise.allSettled([
      documentApi.getStats(),
      testsetApi.getTestSets({ limit: 5 }),
      evaluationApi.getEvaluations({ limit: 5 })
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
