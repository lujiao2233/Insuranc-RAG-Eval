import { request } from './index'
import type { ConversationCase, ConversationExecution, ConversationTurnResult } from '@/types'

export const conversationApi = {
  getConversationCases(testsetId: string): Promise<{ items: ConversationCase[]; total: number }> {
    return request.get(`/testsets/${testsetId}/conversation_cases`)
  },

  getConversationCase(testsetId: string, caseId: string): Promise<ConversationCase> {
    return request.get(`/testsets/${testsetId}/conversation_cases/${caseId}`)
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
