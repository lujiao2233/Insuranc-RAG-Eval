import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    title?: string
    requiresAuth?: boolean
    permissions?: string[]
    keepAlive?: boolean
    breadcrumb?: { title: string; path?: string }[]
  }
}
