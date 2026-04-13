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
  }>
  trend: Array<{
    date: string
    calls: number
    tokens: number
  }>
}

export const usageApi = {
  getStats(days: number = 7): Promise<{ success: boolean; data: UsageStats }> {
    return request.get('/usage/stats', { days })
  }
}