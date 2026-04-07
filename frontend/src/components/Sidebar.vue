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
}

.sidebar-menu:not(.el-menu--collapse) {
  width: 200px;
  min-height: 400px;
}
</style>