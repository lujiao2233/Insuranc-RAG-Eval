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

export interface UsageDashboard {
  overview: {
    total_calls: number
    total_tokens: number
    avg_latency: number
    calls_last_24h: number
    estimated_cost: number
  }
  module_ratio: Array<{
    module: string
    calls: number
    tokens: number
  }>
  percentiles: {
    p50: number
    p90: number
    p95: number
  }
  errors: {
    total_failures: number
    failure_rate: number
    top_failed_modules: Array<{
      module: string
      failures: number
    }>
  }
  io_ratio: {
    avg_prompt_tokens: number
    avg_completion_tokens: number
  }
  models: Array<{
    model: string
    calls: number
    tokens: number
    latency: number
    cost: number
    avg_tokens: number
    avg_latency: number
  }>
  trend_compare: {
    current_period: {
      calls: number
      tokens: number
      cost: number
      failure_rate: number
    }
    previous_period: {
      calls: number
      tokens: number
      cost: number
      failure_rate: number
    }
  }
}

export const usageApi = {
  getDashboard(params?: { start?: string; end?: string }): Promise<{ success: boolean; data: UsageDashboard }> {
    return request.get('/usage/dashboard', params)
  },

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
