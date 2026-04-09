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
          <div class="task-status-bar">
            <el-popover
              placement="bottom-start"
              :width="350"
              trigger="click"
              popper-class="task-center-popover"
            >
              <template #reference>
                <div class="status-indicator" :class="[overallTaskStatus, { 'has-active': taskStore.hasActiveTasks }]">
                  <el-icon class="status-icon">
                    <Loading v-if="taskStore.activeTaskCount > 0" />
                    <CircleCheck v-else-if="overallTaskStatus === 'success'" />
                    <Warning v-else-if="overallTaskStatus === 'error'" />
                    <CircleCheck v-else />
                  </el-icon>
                  <span class="status-text">
                    {{ getOverallStatusText() }}
                  </span>
                </div>
              </template>

              <div class="task-center">
                <div class="task-header">
                  <span class="title">任务中心</span>
                  <el-button link type="primary" @click="taskStore.clearCompleted()">清除已完成</el-button>
                </div>
                <div class="task-list">
                  <template v-if="taskStore.tasks.length > 0">
                    <div v-for="task in taskStore.tasks" :key="task.id" class="task-item">
                      <div class="task-info">
                        <span class="task-name">{{ task.name }}</span>
                        <span class="task-time">{{ task.time }}</span>
                      </div>
                      <el-progress 
                        :percentage="task.progress" 
                        :status="task.status === 'failed' ? 'exception' : (task.status === 'completed' ? 'success' : '')"
                        :stroke-width="4"
                      />
                      <div class="task-footer">
                        <span class="task-status" :class="task.status">{{ getStatusText(task.status) }}</span>
                        <el-button 
                          v-if="task.status === 'running' || task.status === 'pending'" 
                          link 
                          type="danger" 
                          size="small"
                          @click="handleCancelTask(task)"
                        >取消</el-button>
                      </div>
                    </div>
                  </template>
                  <el-empty v-else description="暂无任务" :image-size="60" />
                </div>
              </div>
            </el-popover>
          </div>
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

      <div class="tags-view-container">
        <el-tabs
          v-model="activeTab"
          type="card"
          class="tags-view-wrapper"
          @tab-click="handleTabClick"
          @tab-remove="handleTabRemove"
        >
          <el-tab-pane
            v-for="tag in visitedViews"
            :key="tag.path"
            :label="tag.title"
            :name="tag.path"
            :closable="tag.path !== '/dashboard'"
          />
        </el-tabs>
      </div>
      
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
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useTaskStore, type AppTask } from '@/stores/task'
import { ElMessage } from 'element-plus'
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
  DataAnalysis,
  Loading,
  CircleCheck,
  Warning
} from '@element-plus/icons-vue'

interface TagView {
  path: string
  title: string
  name: string
}

const authStore = useAuthStore()
const taskStore = useTaskStore()
const route = useRoute()
const router = useRouter()

const isCollapsed = ref(false)
const cachedViews = ref([
  'DashboardView',
  'DocumentsView',
  'TestSetsView',
  'TestSetGenerationView',
  'TestSetExecutionView',
  'EvaluationsView',
  'EvaluationCreateView',
  'ReportsView',
  'ConfigView'
])
const visitedViews = ref<TagView[]>([
  { path: '/dashboard', title: '仪表盘', name: 'Dashboard' }
])
const activeTab = ref('/dashboard')

// 计算整体任务状态
const overallTaskStatus = computed(() => {
  if (taskStore.hasActiveTasks) return 'running'
  
  const tasks = taskStore.tasks
  if (tasks.length === 0) return 'normal'
  
  // 如果没有运行中的任务，检查是否有失败的任务
  const hasFailed = tasks.some(t => t.status === 'failed')
  if (hasFailed) return 'error'
  
  // 否则就是全部成功
  return 'success'
})

const getOverallStatusText = () => {
  if (taskStore.hasActiveTasks) {
    return `正在进行 ${taskStore.activeTaskCount} 个任务`
  }
  
  if (overallTaskStatus.value === 'error') {
    return '部分任务失败'
  }
  
  if (overallTaskStatus.value === 'success') {
    return '任务全部完成'
  }
  
  return '系统运行正常'
}

const getStatusText = (status: string) => {
  const map: Record<string, string> = {
    pending: '进行中',
    running: '进行中',
    completed: '已完成',
    failed: '失败'
  }
  return map[status] || status
}

const handleCancelTask = (task: AppTask) => {
  // 暂时只是移除展示，实际取消可能需要调接口
  taskStore.removeTask(task.id)
  ElMessage.success('已取消该任务')
}

// 监听路由变化
watch(
  () => route.path,
  (path) => {
    activeTab.value = path
    addTag()
  },
  { immediate: true }
)

function addTag() {
  const { path, meta, name } = route
  if (!path || !meta.title) return

  const isExist = visitedViews.value.some((tag) => tag.path === path)
  if (!isExist) {
    visitedViews.value.push({
      path,
      title: meta.title as string,
      name: name as string
    })
  }
}

const handleTabClick = (tab: any) => {
  router.push(tab.props.name)
}

const handleTabRemove = (path: string) => {
  const index = visitedViews.value.findIndex((tag) => tag.path === path)
  if (index === -1) return

  const removedTag = visitedViews.value.splice(index, 1)[0]
  
  if (activeTab.value === removedTag.path) {
    const nextTag = visitedViews.value[index] || visitedViews.value[index - 1]
    if (nextTag) {
      router.push(nextTag.path)
    } else {
      router.push('/dashboard')
    }
  }
}

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

    .task-status-bar {
      .status-indicator {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 4px 12px;
        border-radius: 16px;
        background: #f0f2f5;
        cursor: pointer;
        transition: all 0.3s;
        border: 1px solid transparent;

        &:hover {
          background: #e6e8eb;
          border-color: #dcdfe6;
        }

        &.has-active {
          background: #ecf5ff;
          color: #409eff;
          
          .status-icon {
            animation: rotating 2s linear infinite;
          }
        }

        &.success {
          background: #f0f9eb;
          color: #67c23a;
          border-color: #e1f3d8;
        }

        &.error {
          background: #fef0f0;
          color: #f56c6c;
          border-color: #fde2e2;
        }

        .status-icon {
          font-size: 16px;
        }

        .status-text {
          font-size: 13px;
          font-weight: 500;
        }
      }
    }

    .tags-view-container {
      height: 34px;
      width: 100%;
      background: #fff;
      border-bottom: 1px solid #d8dce5;
      box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.12), 0 0 3px 0 rgba(0, 0, 0, 0.04);
      
      .tags-view-wrapper {
        :deep(.el-tabs__header) {
          margin: 0;
          border-bottom: none;
          
          .el-tabs__nav {
            border: none;
          }

          .el-tabs__item {
            height: 34px;
            line-height: 34px;
            border: none;
            border-right: 1px solid #d8dce5;
            color: #495060;
            background: #fff;
            padding: 0 15px;
            font-size: 12px;
            transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);

            &:first-child {
              margin-left: 15px;
              border-left: 1px solid #d8dce5;
            }

            &.is-active {
              background-color: #42b983;
              color: #fff;
              border-color: #42b983;

              &::before {
                content: '';
                background: #fff;
                display: inline-block;
                width: 8px;
                height: 8px;
                border-radius: 50%;
                position: relative;
                margin-right: 5px;
              }
            }

            &:hover {
              color: #42b983;
            }

            .is-icon-close {
              width: 12px;
              height: 12px;
              vertical-align: -2px;
              border-radius: 50%;
              text-align: center;
              transition: all 0.3s cubic-bezier(0.645, 0.045, 0.355, 1);
              transform-origin: 100% 50%;

              &:before {
                transform: scale(0.6);
                display: inline-block;
                vertical-align: -3px;
              }

              &:hover {
                background-color: #b4bccc;
                color: #fff;
              }
            }
          }
        }
      }
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

.task-center-popover {
  padding: 0 !important;
}

.task-center {
  .task-header {
    padding: 12px 16px;
    border-bottom: 1px solid #f0f0f0;
    display: flex;
    justify-content: space-between;
    align-items: center;

    .title {
      font-weight: bold;
      font-size: 14px;
    }
  }

  .task-list {
    max-height: 400px;
    overflow-y: auto;
    padding: 8px 0;

    .task-item {
      padding: 12px 16px;
      transition: background 0.3s;

      &:hover {
        background: #f9f9f9;
      }

      .task-info {
        display: flex;
        justify-content: space-between;
        margin-bottom: 8px;

        .task-name {
          font-size: 13px;
          color: #303133;
          font-weight: 500;
        }

        .task-time {
          font-size: 12px;
          color: #909399;
        }
      }

      .task-footer {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 6px;

        .task-status {
          font-size: 12px;
          
          &.running { color: #409eff; }
          &.completed { color: #67c23a; }
          &.failed { color: #f56c6c; }
        }
      }
    }
  }
}

@keyframes rotating {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
