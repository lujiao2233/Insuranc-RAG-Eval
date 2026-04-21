<template>
  <div class="sidebar">
    <el-menu
      :default-active="$route.path"
      class="sidebar-menu"
      :unique-opened="true"
      :collapse="isCollapse"
      router
    >
      <el-menu-item index="/dashboard">
        <el-icon><House /></el-icon>
        <span>仪表板</span>
      </el-menu-item>

      <el-menu-item index="/usage">
        <el-icon><DataAnalysis /></el-icon>
        <span>用量统计</span>
      </el-menu-item>
      
      <el-sub-menu index="/documents">
        <template #title>
          <el-icon><Document /></el-icon>
          <span>文档管理</span>
        </template>
        <el-menu-item index="/documents/upload">上传文档</el-menu-item>
        <el-menu-item index="/documents/list">文档列表</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="/testsets">
        <template #title>
          <el-icon><Collection /></el-icon>
          <span>测试集管理</span>
        </template>
        <el-menu-item index="/testsets/create">创建测试集</el-menu-item>
        <el-menu-item index="/testsets/list">测试集列表</el-menu-item>
      </el-sub-menu>
      
      <el-sub-menu index="/evaluations">
        <template #title>
          <el-icon><Histogram /></el-icon>
          <span>评估管理</span>
        </template>
        <el-menu-item index="/evaluations/run">运行评估</el-menu-item>
        <el-menu-item index="/evaluations/results">评估结果</el-menu-item>
      </el-sub-menu>
      
      <el-menu-item index="/reports">
        <el-icon><Tickets /></el-icon>
        <span>报告分析</span>
      </el-menu-item>
    </el-menu>
  </div>
</template>

<script>
import { 
  House, 
  DataAnalysis,
  Document, 
  Collection, 
  Histogram, 
  Tickets,
  Menu as IconMenu,
  Location,
  Setting 
} from '@element-plus/icons-vue'

export default {
  name: 'Sidebar',
  data() {
    return {
      isCollapse: false
    }
  },
  setup() {
    return {
      House,
      DataAnalysis,
      Document,
      Collection,
      Histogram,
      Tickets,
      IconMenu,
      Location,
      Setting
    }
  }
}
</script>

<style scoped>
.sidebar {
  height: 100%;
  background-color: var(--bg-card, #ffffff);
  border-right: 1px solid var(--border-1, #e5eaf0);
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
  min-height: 400px;
}

:deep(.el-menu) {
  border-right: none;
  background-color: transparent;
  
  .el-menu-item, .el-sub-menu__title {
    color: var(--text-2, #606266);
    
    &:hover {
      background-color: var(--bg-app, #f5f7fa);
      color: var(--brand-1, #2563eb);
    }
  }
  
  .el-menu-item.is-active {
    background-color: rgba(37, 99, 235, 0.1);
    color: var(--brand-1, #2563eb);
    font-weight: 600;
  }
}
</style>
