import axios, { AxiosInstance, AxiosResponse, AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { tokenStorage } from '@/utils/storage'
import type { ApiError } from '@/types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const instance: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 1800000,
  headers: {
    'Content-Type': 'application/json'
  }
})

let refreshPromise: Promise<string | null> | null = null

const requestTokenRefresh = async (): Promise<string | null> => {
  const currentToken = tokenStorage.get()
  if (!currentToken) {
    return null
  }
  if (refreshPromise) {
    return refreshPromise
  }
  refreshPromise = (async () => {
    try {
      const resp = await axios.post(
        `${BASE_URL}/auth/refresh-token`,
        null,
        {
          headers: {
            Authorization: `Bearer ${currentToken}`,
            'Content-Type': 'application/json'
          }
        }
      )
      const newToken = resp?.data?.access_token
      if (newToken) {
        tokenStorage.set(newToken)
        return newToken
      }
      return null
    } catch {
      return null
    } finally {
      refreshPromise = null
    }
  })()
  return refreshPromise
}

const redirectToLogin = () => {
  tokenStorage.remove()
  if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
    window.location.href = '/login'
  }
}

instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = tokenStorage.get()
    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error: AxiosError<ApiError>) => {
    const { response, config } = error
    
    if (!response) {
      ElMessage.error('网络连接失败，请检查网络')
      return Promise.reject(error)
    }
    
    const { status, data } = response
    
    switch (status) {
      case 401:
        if (config && !String(config.url || '').includes('/auth/login')) {
          const retryConfig = config as InternalAxiosRequestConfig & { _retry?: boolean }
          if (!retryConfig._retry) {
            retryConfig._retry = true
            const newToken = await requestTokenRefresh()
            if (newToken) {
              retryConfig.headers = retryConfig.headers || {}
              retryConfig.headers.Authorization = `Bearer ${newToken}`
              return instance.request(retryConfig)
            }
          }
        }
        redirectToLogin()
        ElMessage.error('登录已过期，请重新登录')
        break
        
      case 403:
        ElMessage.error('没有权限执行此操作')
        break
        
      case 404:
        ElMessage.error(data?.detail || '请求的资源不存在')
        break
        
      case 422:
        ElMessage.error(data?.detail || '请求参数错误')
        break
        
      case 500:
        ElMessage.error(data?.detail || '服务器内部错误')
        break
        
      default:
        ElMessage.error(data?.detail || `请求失败 (${status})`)
    }
    
    return Promise.reject(error)
  }
)

export default instance

export const request = {
  get<T = any>(url: string, params?: any, config?: any): Promise<T> {
    return instance.get(url, { params, ...config })
  },
  
  post<T = any>(url: string, data?: any, config?: any): Promise<T> {
    return instance.post(url, data, config)
  },
  
  put<T = any>(url: string, data?: any, config?: any): Promise<T> {
    return instance.put(url, data, config)
  },
  
  delete<T = any>(url: string, config?: any): Promise<T> {
    return instance.delete(url, config)
  },
  
  upload<T = any>(url: string, file: File, onProgress?: (percent: number) => void): Promise<T> {
    const formData = new FormData()
    formData.append('file', file)
    return instance.post(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total)
          onProgress(percent)
        }
      }
    })
  }
}
