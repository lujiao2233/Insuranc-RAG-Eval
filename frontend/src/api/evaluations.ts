import { request } from './index'
import type {
  Evaluation,
  EvaluationResult,
  TaskStatus,
  ConversationEvaluationCaseResult
} from '@/types'

export const evaluationApi = {
  getEvaluations(params?: { skip?: number; limit?: number; status?: string }): Promise<{
    items: Evaluation[]
    total: number
    page: number
    size: number
    pages: number
  }> {
    return request.get('/evaluations/', params)
  },

  getEvaluation(id: string): Promise<Evaluation> {
    return request.get(`/evaluations/${id}`)
  },

  createEvaluation(data: {
    testset_id: string
    evaluation_method?: string
    evaluation_metrics?: string[]
  }): Promise<{
    id: string
    task_id: string
    status: string
    message: string
  }> {
    return request.post('/evaluations/', data)
  },

  createConversationEvaluation(data: {
    testset_id: string
    evaluation_metrics?: string[]
  }): Promise<{
    id: string
    task_id: string
    status: string
    message: string
  }> {
    return request.post('/evaluations/conversation', data)
  },

  getTaskStatus(taskId: string): Promise<TaskStatus> {
    return request.get(`/evaluations/task/${taskId}`)
  },

  getEvaluationResults(evaluationId: string, params?: {
    skip?: number
    limit?: number
  }): Promise<{
    evaluation_id: string
    total: number
    items: EvaluationResult[]
    conversation_results?: ConversationEvaluationCaseResult[]
  }> {
    return request.get(`/evaluations/${evaluationId}/results`, params)
  },

  async getConversationResults(evaluationId: string): Promise<{
    evaluation_id: string
    total: number
    items: EvaluationResult[]
    conversation_results: ConversationEvaluationCaseResult[]
  }> {
    const response = await request.get(`/evaluations/${evaluationId}/results`)
    return {
      evaluation_id: response.evaluation_id,
      total: response.total,
      items: response.items || [],
      conversation_results: response.conversation_results || []
    }
  },

  getEvaluationSummary(evaluationId: string): Promise<{
    evaluation_id: string
    status: string
    total_questions: number
    evaluated_questions: number
    evaluation_time: number
    overall_metrics: Record<string, any>
  }> {
    return request.get(`/evaluations/${evaluationId}/summary`)
  },

  deleteEvaluation(id: string): Promise<void> {
    return request.delete(`/evaluations/${id}`)
  }
}
