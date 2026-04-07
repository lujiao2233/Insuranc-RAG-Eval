import { request } from './index'
import type { Configuration } from '@/types'

export const configApi = {
  getAllConfig(): Promise<{
    qwen: Record<string, any>
    evaluation: Record<string, any>
    thresholds: Record<string, any>
    system: Record<string, any>
  }> {
    return request.get('/config/all')
  },

  getConfigs(): Promise<{ items: Configuration[]; total: number }> {
    return request.get('/config/')
  },

  getConfig(configKey: string): Promise<Configuration> {
    return request.get(`/config/${encodeURIComponent(configKey)}`)
  },

  createConfig(data: {
    config_key: string
    config_value: string
    description?: string
  }): Promise<Configuration> {
    return request.post('/config/', data)
  },

  updateConfig(configKey: string, data: {
    config_value: string
    description?: string
  }): Promise<Configuration> {
    return request.put(`/config/${encodeURIComponent(configKey)}`, data)
  },

  deleteConfig(configKey: string): Promise<void> {
    return request.delete(`/config/${encodeURIComponent(configKey)}`)
  },

  batchUpdateConfigs(configs: Record<string, any>): Promise<{
    updated: string[]
    errors: any[]
    total_updated: number
    total_errors: number
  }> {
    return request.post('/config/batch', { configs })
  },

  getConfigGroup(prefix: string): Promise<{
    prefix: string
    configs: Record<string, any>
  }> {
    return request.get(`/config/group/${encodeURIComponent(prefix)}`)
  },

  getApiStatus(): Promise<{ api_status: Record<string, string> }> {
    return request.get('/config/api/status')
  },

  setApiKey(service: string, apiKey: string): Promise<{ message: string }> {
    return request.post('/config/api/key', { service, api_key: apiKey })
  },

  testApiConnection(service: string = 'qwen'): Promise<{
    status: string
    message: string
    response?: string
  }> {
    return request.post(`/config/api/test?service=${service}`)
  },

  getQwenConfig(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/qwen/all')
  },

  getEvaluationConfig(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/evaluation/all')
  },

  getRagConfig(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/rag/all')
  },

  getThresholds(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/thresholds/all')
  },

  getSystemConfig(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/system/all')
  },

  resetToDefaults(prefix?: string): Promise<{ message: string; count: number }> {
    const url = prefix ? `/config/reset?prefix=${encodeURIComponent(prefix)}` : '/config/reset'
    return request.post(url)
  },

  exportConfigs(): Promise<{ configs: Record<string, any> }> {
    return request.get('/config/export')
  },

  importConfigs(configs: Record<string, any>, overwrite: boolean = true): Promise<{
    imported: string[]
    skipped: string[]
    errors: any[]
    total_imported: number
    total_skipped: number
  }> {
    return request.post('/config/import', { configs, overwrite })
  }
}
