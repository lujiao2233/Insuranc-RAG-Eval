import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { tokenStorage } from '@/utils/storage'

export function useAuth() {
  const router = useRouter()
  const authStore = useAuthStore()
  
  const isLoggedIn = computed(() => authStore.isAuthenticated)
  const currentUser = computed(() => authStore.user)
  const isLoading = computed(() => authStore.loading)
  const error = computed(() => authStore.error)

  const login = async (username: string, password: string) => {
    const success = await authStore.login({ username, password })
    if (success) {
      router.push('/dashboard')
    }
    return success
  }

  const logout = () => {
    authStore.logout()
    router.push('/login')
  }

  const register = async (data: { username: string; email: string; password: string; full_name?: string }) => {
    const success = await authStore.register(data)
    if (success) {
      router.push('/dashboard')
    }
    return success
  }

  const checkAuth = () => {
    return !!tokenStorage.get()
  }

  return {
    isLoggedIn,
    currentUser,
    isLoading,
    error,
    login,
    logout,
    register,
    checkAuth
  }
}
