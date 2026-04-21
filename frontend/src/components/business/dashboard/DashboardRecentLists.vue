<template>
  <el-row :gutter="16" class="dashboard-lists">
    <el-col :xs="24" :lg="12" class="list-col">
      <el-card class="list-card" shadow="never" :body-style="{ padding: '0 16px 16px' }">
        <template #header>
          <div class="card-header">
            <span>最近测试集</span>
            <el-link type="primary" @click="$emit('navigate', routes.TESTSETS)">查看全部</el-link>
          </div>
        </template>

        <template v-if="recentTestsets.length">
          <el-table :data="recentTestsets" size="small" style="width: 100%">
            <el-table-column prop="name" label="测试集名称" show-overflow-tooltip />
            <el-table-column prop="question_count" label="问题数" width="90" />
            <el-table-column prop="create_time" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.create_time) }}
              </template>
            </el-table-column>
          </el-table>
        </template>
        <div v-else class="empty-wrap">
          <el-empty description="暂无测试集" :image-size="60" />
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :lg="12" class="list-col">
      <el-card class="list-card" shadow="never" :body-style="{ padding: '0 16px 16px' }">
        <template #header>
          <div class="card-header">
            <span>最近评估</span>
            <el-link type="primary" @click="$emit('navigate', routes.EVALUATIONS)">查看全部</el-link>
          </div>
        </template>

        <template v-if="recentEvaluations.length">
          <el-table :data="recentEvaluations" size="small" style="width: 100%">
            <el-table-column prop="testset_name" label="测试集名称" min-width="150" show-overflow-tooltip>
              <template #default="{ row }">
                {{ row.testset_name || '未知测试集' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small" disable-transitions>
                  {{ getStatusText(row.status) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="created_at" label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDateTime(row.created_at || row.timestamp) }}
              </template>
            </el-table-column>
          </el-table>
        </template>
        <div v-else class="empty-wrap">
          <el-empty description="暂无评估记录" :image-size="60" />
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import type { Evaluation, TestSet } from '@/types'
import { formatDate, formatDateTime } from '@/utils/format'

defineProps<{
  recentTestsets: TestSet[]
  recentEvaluations: Evaluation[]
  routes: Record<string, string>
}>()

defineEmits(['navigate'])

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    completed: 'success',
    running: 'primary',
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
</script>

<style lang="scss" scoped>
.dashboard-lists {
  margin-bottom: -16px; // 抵消 col 的 margin-bottom
}

.list-col {
  margin-bottom: 16px;
}

.list-card {
  height: 100%;

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
}

.empty-wrap {
  padding: 16px 0;
}
</style>