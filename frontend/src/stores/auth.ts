import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import { tokenStorage } from '@/utils/storage'
import type { User, LoginForm, RegisterForm } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const token = ref<string | null>(tokenStorage.get())
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  async function login(credentials: LoginForm) {
    loading.value = true
    error.value = null
    
    try {
      const response = await authApi.login(credentials)
      token.value = response.access_token
      tokenStorage.set(response.access_token)
      
      await fetchCurrentUser()
      
      return true
    } catch (e: any) {
      error.value = e.response?.data?.detail || '登录失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function register(data: RegisterForm) {
    loading.value = true
    error.value = null
    
    try {
      await authApi.register(data)
      return await login({
        username: data.username,
        password: data.password
      })
    } catch (e: any) {
      error.value = e.response?.data?.detail || '注册失败'
      return false
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    if (!token.value) return
    
    try {
      const response = await authApi.getCurrentUser()
      user.value = response
    } catch {
      logout()
    }
  }

  function logout() {
    user.value = null
    token.value = null
    tokenStorage.remove()
  }

  async function refreshToken() {
    if (!token.value) return false
    
    try {
      const response = await authApi.refreshToken()
      token.value = response.access_token
      tokenStorage.set(response.access_token)
      return true
    } catch {
      logout()
      return false
    }
  }

  if (token.value) {
    fetchCurrentUser()
  }

  return {
    user,
    token,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    username,
    login,
    register,
    logout,
    fetchCurrentUser,
    refreshToken
  }
})
