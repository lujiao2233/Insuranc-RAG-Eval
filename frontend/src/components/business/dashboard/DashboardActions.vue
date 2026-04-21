<template>
  <el-card class="dashboard-actions" shadow="never" :body-style="{ padding: '16px' }">
    <template #header>
      <div class="card-header">
        <span>快捷操作</span>
      </div>
    </template>

    <div class="quick-actions">
      <!-- 统一按钮视觉层级，核心流程用 primary，次要操作用 default -->
      <el-button @click="$emit('navigate', routes.DOCUMENTS)">
        <el-icon><Upload /></el-icon>
        上传文档
      </el-button>
      <el-button @click="$emit('navigate', routes.TESTSETS)">
        <el-icon><Collection /></el-icon>
        创建测试集
      </el-button>
      <el-button type="primary" @click="$emit('navigate', routes.EVALUATIONS)">
        <el-icon><DataLine /></el-icon>
        开始评估
      </el-button>
      <el-button @click="$emit('navigate', routes.REPORTS)">
        <el-icon><DocumentCopy /></el-icon>
        查看报告
      </el-button>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { Upload, Collection, DataLine, DocumentCopy } from '@element-plus/icons-vue'

defineProps<{
  routes: Record<string, string>
}>()

defineEmits(['navigate'])
</script>

<style lang="scss" scoped>
.dashboard-actions {
  .card-header {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .quick-actions {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    
    .el-button {
      margin-left: 0; /* 抵消 el-button 默认相邻元素的 margin-left */
    }
  }
}
</style>