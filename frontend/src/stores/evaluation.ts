import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { evaluationApi } from '@/api/evaluations'
import type { Evaluation, EvaluationResult, TaskStatus } from '@/types'

export const useEvaluationStore = defineStore('evaluation', () => {
  const evaluations = ref<Evaluation[]>([])
  const currentEvaluation = ref<Evaluation | null>(null)
  const evaluationResults = ref<EvaluationResult[]>([])
  const taskStatus = ref<TaskStatus | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const completedEvaluations = computed(() =>
    evaluations.value.filter(e => e.status === 'completed')
  )
  const runningEvaluations = computed(() =>
    evaluations.value.filter(e => e.status === 'running')
  )

  async function fetchEvaluations(params?: { status?: string }) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.getEvaluations(params)
      evaluations.value = response.items
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取评估列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchEvaluation(id: string) {
    loading.value = true
    error.value = null
    
    try {
      currentEvaluation.value = await evaluationApi.getEvaluation(id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取评估详情失败'
    } finally {
      loading.value = false
    }
  }

  async function createEvaluation(data: { testset_id: string; evaluation_method?: string; evaluation_metrics?: string[] }) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.createEvaluation(data)
      
      taskStatus.value = {
        id: response.task_id,
        type: 'evaluation',
        status: 'pending',
        progress: 0,
        message: response.message || '',
        logs: []
      }
      
      return response
    } catch (e: any) {
      error.value = e.response?.data?.detail || '创建评估失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTaskStatus(taskId: string) {
    try {
      const status = await evaluationApi.getTaskStatus(taskId)
      taskStatus.value = status
      return status
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取任务状态失败'
      throw e
    }
  }

  async function fetchEvaluationResults(evaluationId: string) {
    loading.value = true
    error.value = null
    
    try {
      const response = await evaluationApi.getEvaluationResults(evaluationId)
      evaluationResults.value = response.items
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取评估结果失败'
    } finally {
      loading.value = false
    }
  }

  async function deleteEvaluation(id: string) {
    try {
      await evaluationApi.deleteEvaluation(id)
      evaluations.value = evaluations.value.filter(e => e.id !== id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '删除评估失败'
      throw e
    }
  }

  function clearTaskStatus() {
    taskStatus.value = null
  }

  return {
    evaluations,
    currentEvaluation,
    evaluationResults,
    taskStatus,
    loading,
    error,
    completedEvaluations,
    runningEvaluations,
    fetchEvaluations,
    fetchEvaluation,
    createEvaluation,
    fetchTaskStatus,
    fetchEvaluationResults,
    deleteEvaluation,
    clearTaskStatus
  }
})
