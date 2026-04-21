<template>
  <el-row :gutter="16" class="dashboard-stats">
    <el-col :xs="24" :sm="12" :lg="6" class="stat-col">
      <el-card class="stat-card" shadow="hover" :body-style="{ padding: '16px' }">
        <div class="stat-content">
          <div class="stat-icon stat-icon--doc">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalDocuments }}</div>
            <div class="stat-label">文档总数</div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :sm="12" :lg="6" class="stat-col">
      <el-card class="stat-card" shadow="hover" :body-style="{ padding: '16px' }">
        <div class="stat-content">
          <div class="stat-icon stat-icon--testset">
            <el-icon :size="24"><Collection /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalTestsets }}</div>
            <div class="stat-label">测试集</div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :sm="12" :lg="6" class="stat-col">
      <el-card class="stat-card" shadow="hover" :body-style="{ padding: '16px' }">
        <div class="stat-content">
          <div class="stat-icon stat-icon--eval">
            <el-icon :size="24"><DataLine /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalEvaluations }}</div>
            <div class="stat-label">评估任务</div>
          </div>
        </div>
      </el-card>
    </el-col>

    <el-col :xs="24" :sm="12" :lg="6" class="stat-col">
      <el-card
        class="stat-card stat-card--clickable"
        shadow="hover"
        :body-style="{ padding: '16px' }"
        @click="$emit('click-usage')"
      >
        <div class="stat-content">
          <div class="stat-icon stat-icon--usage">
            <el-icon :size="24"><Coin /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-value">{{ stats.totalTokens }}</div>
            <div class="stat-label">Token 用量 (点击趋势)</div>
          </div>
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { Document, Collection, DataLine, Coin } from '@element-plus/icons-vue'

defineProps<{
  stats: {
    totalDocuments: number
    totalTestsets: number
    totalEvaluations: number
    totalTokens: number
    totalCalls: number
    avgLatency: number
  }
}>()

defineEmits(['click-usage'])
</script>

<style lang="scss" scoped>
.dashboard-stats {
  margin-bottom: -16px;
}

.stat-col {
  margin-bottom: 16px;
}

.stat-card {
  height: 100%;
  border-radius: var(--radius-8, 8px);

  .stat-content {
    display: flex;
    align-items: center;
    gap: 16px;

    .stat-icon {
      width: 52px;
      height: 52px;
      border-radius: var(--radius-8, 8px);
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }

    .stat-info {
      overflow: hidden;

      .stat-value {
        font-size: 26px;
        font-weight: 600;
        color: var(--text-1, #303133);
        line-height: 1.2;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .stat-label {
        font-size: 13px;
        color: var(--text-2, #909399);
        margin-top: 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }
  }
}

/* 浅色底 + 深色图标（更现代） */
.stat-icon--doc {
  background: rgba(37, 99, 235, 0.12);
  color: var(--brand-1, #2563eb);
}
.stat-icon--testset {
  background: rgba(22, 163, 74, 0.12);
  color: var(--success-1, #16a34a);
}
.stat-icon--eval {
  background: rgba(245, 158, 11, 0.14);
  color: var(--warning-1, #f59e0b);
}
.stat-icon--usage {
  background: rgba(29, 78, 216, 0.12);
  color: var(--brand-2, #1d4ed8);
}

.stat-card--clickable {
  cursor: pointer;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;

  &:hover {
    box-shadow: var(--shadow-1, 0 1px 2px rgba(16, 24, 40, 0.06), 0 2px 6px rgba(16, 24, 40, 0.06));
    border-color: rgba(37, 99, 235, 0.35);
  }
}
</style>