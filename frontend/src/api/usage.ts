import { request } from './index'

export interface UsageStats {
  summary: {
    total_calls: number
    total_tokens: number
  }
  modules: Array<{
    module: string
    calls: number
    tokens: number
    avg_latency: number
  }>
  trend: Array<{
    date: string
    calls: number
    tokens: number
    avg_latency: number
  }>
}

export interface UsageEvent {
  timestamp: string
  module: string
  model: string
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
  latency_ms: number
}

export const usageApi = {
  getStats(days: number = 7): Promise<{ success: boolean; data: UsageStats }> {
    return request.get('/usage/stats', { days })
  },

  getEvents(params: {
    start?: string
    end?: string
    limit?: number
    module_name?: string
    model_name?: string
  }): Promise<{ success: boolean; data: UsageEvent[] }> {
    return request.get('/usage/events', params)
  }
}
