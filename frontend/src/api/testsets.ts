import { request } from './index'
import type {
  TestSet,
  Question,
  PaginatedResponse,
  TaskStatus,
  ConversationCase,
  ConversationTurn,
  ConversationExecution,
  ConversationTurnResult
} from '@/types'

export const testsetApi = {
  getTestSets(params?: { skip?: number; limit?: number; document_id?: string; stage?: 'base' | 'evaluation' | 'report' }): Promise<PaginatedResponse<TestSet>> {
    return request.get('/testsets/', params)
  },

  getTestSet(id: string): Promise<TestSet> {
    return request.get(`/testsets/${id}`)
  },

  createTestSet(data: {
    document_id: string
    name: string
    description?: string
    generation_method?: string
    metadata?: Record<string, any>
  }): Promise<TestSet> {
    return request.post('/testsets/', data)
  },

  updateTestSet(id: string, data: Partial<TestSet>): Promise<TestSet> {
    return request.put(`/testsets/${id}`, data)
  },

  deleteTestSet(id: string): Promise<void> {
    return request.delete(`/testsets/${id}`)
  },

  getQuestions(testsetId: string, params?: {
    skip?: number
    limit?: number
    question_type?: string
  }): Promise<PaginatedResponse<Question>> {
    return request.get(`/testsets/${testsetId}/questions`, params)
  },

  getConversationCases(testsetId: string): Promise<{ items: ConversationCase[]; total: number }> {
    return request.get(`/testsets/${testsetId}/conversation_cases`)
  },

  getConversationCase(testsetId: string, caseId: string): Promise<ConversationCase> {
    return request.get(`/testsets/${testsetId}/conversation_cases/${caseId}`)
  },

  updateConversationTurn(
    testsetId: string,
    caseId: string,
    turnId: string,
    data: Partial<ConversationTurn>
  ): Promise<ConversationTurn> {
    return request.put(`/testsets/${testsetId}/conversation_cases/${caseId}/turns/${turnId}`, data)
  },

  addQuestion(testsetId: string, data: Partial<Question>): Promise<Question> {
    return request.post(`/testsets/${testsetId}/questions`, data)
  },

  updateQuestion(testsetId: string, questionId: string, data: Partial<Question>): Promise<Question> {
    return request.put(`/testsets/${testsetId}/questions/${questionId}`, data)
  },

  deleteQuestion(testsetId: string, questionId: string): Promise<void> {
    return request.delete(`/testsets/${testsetId}/questions/${questionId}`)
  },

  generateQuestions(testsetId: string, params: {
    num_questions?: number
    question_types?: string | string[]
    generation_mode?: 'advanced'
    enable_safety_robustness?: boolean
    multi_doc_ratio?: number
    document_ids?: string[]
    persona_list?: Array<Record<string, any>>
  }): Promise<{ task_id: string; message: string }> {
    const normalizedParams = {
      ...params,
      question_types: Array.isArray(params.question_types)
        ? params.question_types.join(',')
        : params.question_types
    }
    return request.post(`/testsets/${testsetId}/generate`, normalizedParams)
  },

  generateQuestionsAsync(testsetId: string, params: {
    num_questions?: number
    question_types?: string
    generation_mode?: 'advanced'
    enable_safety_robustness?: boolean
    multi_doc_ratio?: number
    document_ids?: string[]
    persona_list?: Array<Record<string, any>>
    distribution_mode?: 'per_doc' | 'total'
    questions_per_doc?: number
  }): Promise<{ task_id: string; message: string }> {
    return request.post(`/testsets/${testsetId}/generate_async`, params)
  },

  generateConversationQuestions(testsetId: string, params: {
    num_cases?: number
    turn_range?: [number, number]
    case_type_ratio?: {
      single_chunk_deep: number
      same_doc_chain: number
      cross_doc_assoc: number
    }
    document_ids?: string[]
  }): Promise<{ task_id: string; message: string }> {
    return request.post(`/testsets/${testsetId}/generate_conversation`, params)
  },

  getTaskStatus(taskId: string): Promise<TaskStatus> {
    return request.get(`/testsets/tasks/${taskId}`)
  },

  generateAdvancedQuestions(testsetId: string, params: {
    num_questions?: number
    question_types?: string | string[]
  }): Promise<{ task_id: string; message: string }> {
    return this.generateQuestions(testsetId, {
      ...params,
      generation_mode: 'advanced'
    })
  },

  getAdvancedConfig(): Promise<{
    taxonomy: Array<{ major: string; minors: string[] }>
    strategies: Array<{ id: string; name: string; description: string }>
    features: Record<string, boolean>
  }> {
    return request.get('/testsets/advanced/config')
  },

  exportTestSet(id: string, params?: { evaluation_id?: string }): Promise<Blob> {
    return request.get(`/testsets/${id}/export`, params || {}, { responseType: 'blob' })
  },

  importTestSetCsv(params: {
    file: File
    name?: string
    description?: string
    document_id?: string
  }): Promise<TestSet> {
    const formData = new FormData()
    formData.append('file', params.file)
    if (params.name) {
      formData.append('name', params.name)
    }
    if (params.description) {
      formData.append('description', params.description)
    }
    if (params.document_id) {
      formData.append('document_id', params.document_id)
    }
    return request.post('/testsets/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  sendExecutionVerifyCode(testsetId: string, data: { mobile: string }) {
    return request.post(`/testsets/${testsetId}/execution/send-code`, data)
  },

  startExecution(testsetId: string, data: { mobile: string; verify_code: string; bot_id: string }) {
    return request.post<{ task_id: string; message: string; execution_testset_id?: string }>(`/testsets/${testsetId}/execution/start`, data)
  },

  startConversationExecution(testsetId: string, data: { mobile: string; verify_code: string; bot_id: string }) {
    return request.post<{
      task_id: string
      message: string
      execution_id: string
      execution_evaluation_id?: string
      execution_testset_id?: string
    }>(`/testsets/${testsetId}/conversation_execution/start`, data)
  },

  getConversationExecution(executionId: string): Promise<ConversationExecution> {
    return request.get(`/testsets/conversation_executions/${executionId}`)
  },

  getConversationTurnResults(executionId: string): Promise<{
    execution: ConversationExecution
    items: ConversationTurnResult[]
    total: number
  }> {
    return request.get(`/testsets/conversation_executions/${executionId}/turn_results`)
  }
}
