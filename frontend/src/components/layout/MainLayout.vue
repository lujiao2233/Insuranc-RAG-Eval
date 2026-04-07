<template>
  <el-container class="main-layout">
    <el-aside :width="isCollapsed ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <el-icon :size="32"><DataAnalysis /></el-icon>
        <span v-show="!isCollapsed" class="logo-text">RAG评估系统</span>
      </div>
      
      <el-menu
        :default-active="activeMenu"
        :collapse="isCollapsed"
        :router="true"
        background-color="#304156"
        text-color="#bfcbd9"
        active-text-color="#409eff"
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
          <el-icon><DataLine /></el-icon>
          <template #title>评估管理</template>
        </el-menu-item>
        
        <el-menu-item index="/reports">
          <el-icon><DocumentCopy /></el-icon>
          <template #title>报告中心</template>
        </el-menu-item>
        
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <template #title>系统配置</template>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
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
              <span class="username">{{ authStore.username || '用户' }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon>
                  个人中心
                </el-dropdown-item>
                <el-dropdown-item divided command="logout">
                  <el-icon><SwitchButton /></el-icon>
                  退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>
      
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
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { 
  HomeFilled, 
  Document, 
  Collection, 
  DataLine, 
  DocumentCopy,
  Setting, 
  UserFilled, 
  User,
  SwitchButton,
  Expand, 
  Fold,
  DataAnalysis
} from '@element-plus/icons-vue'

const authStore = useAuthStore()
const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const cachedViews = ref(['Documents', 'TestSets', 'Evaluations', 'Reports'])

const activeMenu = computed(() => {
  const path = route.path
  const match = path.match(/^\/[^/]+/)
  return match ? match[0] : path
})

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
  } else if (command === 'profile') {
    // 可以跳转到个人中心页面
  }
}

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
    overflow: hidden;
    
    .logo {
      height: 60px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #fff;
      font-size: 18px;
      font-weight: bold;
      border-bottom: 1px solid rgba(255, 255, 255, 0.1);
      
      .logo-text {
        margin-left: 12px;
        white-space: nowrap;
      }
    }
    
    .el-menu {
      border-right: none;
      background-color: transparent;
      
      .el-menu-item {
        &:hover {
          background-color: rgba(255, 255, 255, 0.1);
        }
        
        &.is-active {
          background-color: rgba(64, 158, 255, 0.2);
        }
      }
    }
  }
  
  .header {
    background-color: #fff;
    box-shadow: 0 1px 4px rgba(0, 21, 41, 0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    height: 60px;
    
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
        color: #606266;
        
        .username {
          @media (max-width: 768px) {
            display: none;
          }
        }
      }
    }
  }
  
  .main-content {
    background-color: #f5f7fa;
    padding: 20px;
    overflow-y: auto;
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
