<template>
  <div class="dashboard-view">
    <el-row :gutter="20" class="stats-row">
      <el-col :xs="24" :md="12">
        <el-card class="stat-card stat-card--clickable" @click="goUsage">
          <div class="stat-content">
            <div class="stat-icon" style="background: #9c27b0;">
              <el-icon :size="24"><Coin /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats.totalTokens }}</div>
              <div class="stat-label">Token 用量（点击查看趋势）</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Coin } from '@element-plus/icons-vue'
import { usageApi } from '@/api/usage'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const router = useRouter()

const stats = ref({
  totalTokens: 0
})

const goUsage = () => {
  router.push('/usage')
}

const fetchUsage = async () => {
  if (!authStore.isAuthenticated) {
    return
  }
  
  try {
    const usageRes = await usageApi.getStats(30)
    stats.value.totalTokens = usageRes?.data?.summary?.total_tokens || 0
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
    stats.value.totalTokens = 0
  }
}

onMounted(() => {
  fetchUsage()
})
</script>

<style lang="scss" scoped>
.dashboard-view {
  .stats-row {
    margin-bottom: 4px;
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

  .stat-card--clickable {
    cursor: pointer;
  }

  .stat-card--clickable:hover {
    border-color: var(--el-color-primary-light-5);
  }
}
</style>
