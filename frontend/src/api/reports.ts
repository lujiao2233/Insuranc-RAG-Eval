import { request } from './index'
import type { PaginatedResponse } from '@/types'

export interface Report {
  evaluation_id: string
  testset_name?: string
  evaluation_method?: string
  status?: string
  total_questions?: number
  evaluated_questions?: number
  evaluation_time?: number
  created_at?: string
  timestamp?: string
  overall_score?: number
  performance_level?: string
}

export const reportApi = {
  getReports(params?: { skip?: number; limit?: number }): Promise<PaginatedResponse<Report>> {
    return request.get('/reports/', params)
  },

  getReport(evaluationId: string): Promise<Report> {
    return request.get(`/reports/${evaluationId}`)
  },

  getReportSummary(evaluationId: string): Promise<{
    evaluation_id: string
    overall_score: number | null
    performance_level: string
    total_questions: number
    evaluated_questions: number
    evaluation_time: number
    key_findings: string[]
    recommendations: string[]
  }> {
    return request.get(`/reports/${evaluationId}/summary`)
  },

  getReportMetrics(evaluationId: string): Promise<{
    evaluation_id: string
    quality_metrics: Record<string, any>
    safety_metrics: Record<string, any>
    overall_score: Record<string, any>
    metrics: Record<string, any>
  }> {
    return request.get(`/reports/${evaluationId}/metrics`)
  },

  generateReport(evaluationId: string, format: 'pdf' | 'html' = 'html'): Promise<{
    message: string
    report_path: string
    format: string
  }> {
    return request.post(`/reports/${evaluationId}/generate?format=${format}`)
  },

  downloadReport(evaluationId: string, format: 'pdf' | 'html' = 'pdf'): Promise<Blob> {
    return request.get(`/reports/${evaluationId}/download?format=${format}`, {}, { responseType: 'blob' })
  },

  deleteReport(evaluationId: string) {
    // 报告是评估结果的呈现，删除报告等价于删除该评估记录
    return request.delete(`/evaluations/${evaluationId}`)
  }
}
