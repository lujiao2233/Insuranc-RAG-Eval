import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/LoginView.vue'),
    meta: { requiresAuth: false, title: '登录' }
  },
  {
    path: '/register',
    name: 'Register',
    component: () => import('@/views/auth/RegisterView.vue'),
    meta: { requiresAuth: false, title: '注册' }
  },
  {
    path: '/',
    component: () => import('@/components/layout/MainLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/DashboardView.vue'),
        meta: { title: '仪表盘', keepAlive: true }
      },
      {
        path: 'documents',
        name: 'Documents',
        component: () => import('@/views/documents/DocumentsView.vue'),
        meta: { title: '文档管理', keepAlive: true }
      },
      {
        path: 'documents/:id',
        name: 'DocumentDetail',
        component: () => import('@/views/documents/DocumentDetailView.vue'),
        meta: { title: '文档详情' }
      },
      {
        path: 'testsets',
        name: 'TestSets',
        component: () => import('@/views/testsets/TestSetsView.vue'),
        meta: { title: '测试集管理', keepAlive: true }
      },
      {
        path: 'testsets/:id',
        name: 'TestSetDetail',
        component: () => import('@/views/testsets/TestSetDetailView.vue'),
        meta: { title: '测试集详情' }
      },
      {
        path: 'evaluations',
        name: 'Evaluations',
        component: () => import('@/views/evaluations/EvaluationsView.vue'),
        meta: { title: '评估管理', keepAlive: true }
      },
      {
        path: 'evaluations/:id',
        name: 'EvaluationDetail',
        component: () => import('@/views/evaluations/EvaluationDetailView.vue'),
        meta: { title: '评估详情' }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportsView.vue'),
        meta: { title: '报告中心', keepAlive: true }
      },
      {
        path: 'reports/:id',
        name: 'ReportDetail',
        component: () => import('@/views/reports/ReportDetailView.vue'),
        meta: { title: '报告详情' }
      },
      {
        path: 'config',
        name: 'Configuration',
        component: () => import('@/views/config/ConfigView.vue'),
        meta: { title: '系统配置', keepAlive: true }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'NotFound',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { title: '页面不存在' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    } else if (to.hash) {
      return { el: to.hash, behavior: 'smooth' }
    } else {
      return { top: 0 }
    }
  }
})

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  document.title = `${to.meta.title || 'RAG评估系统'} - RAG评估系统`
  
  if (to.meta.requiresAuth !== false && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }
  
  if ((to.name === 'Login' || to.name === 'Register') && authStore.isAuthenticated) {
    next({ name: 'Dashboard' })
    return
  }
  
  next()
})

router.afterEach((to) => {
  // 可以在这里添加页面访问统计等逻辑
})

export default router
