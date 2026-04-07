import { request } from './index'
import type { PaginatedResponse } from '@/types'

export interface Report {
  id: string
  evaluation_id: string
  testset_name?: string
  status: string
  created_at: string
  report_path?: string
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
    metrics: Record<string, any>
    recommendations: string[]
  }> {
    return request.get(`/reports/${evaluationId}/summary`)
  },

  getReportMetrics(evaluationId: string): Promise<{
    evaluation_id: string
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

  compareReports(evaluationId1: string, evaluationId2: string): Promise<{
    evaluation_1: Record<string, any>
    evaluation_2: Record<string, any>
    comparison: Record<string, any>
  }> {
    return request.get(`/reports/${evaluationId1}/compare/${evaluationId2}`)
  }
}
