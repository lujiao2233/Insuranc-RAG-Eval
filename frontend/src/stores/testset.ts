import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { testsetApi } from '@/api/testsets'
import type { TestSet, Question, PaginatedResponse } from '@/types'

export const useTestSetStore = defineStore('testset', () => {
  const testSets = ref<TestSet[]>([])
  const currentTestSet = ref<TestSet | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    page: 1,
    size: 10,
    total: 0,
    pages: 0
  })
  const filters = ref({
    document_id: undefined as string | undefined
  })

  const hasTestSets = computed(() => testSets.value.length > 0)

  async function fetchTestSets(params?: { document_id?: string }) {
    loading.value = true
    error.value = null
    
    try {
      const query = { ...filters.value, ...params }
      const response: PaginatedResponse<TestSet> = await testsetApi.getTestSets({
        skip: (pagination.value.page - 1) * pagination.value.size,
        limit: pagination.value.size,
        ...query
      })
      
      testSets.value = response.items
      pagination.value = {
        page: response.page,
        size: response.size,
        total: response.total,
        pages: response.pages
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取测试集列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchTestSet(id: string) {
    loading.value = true
    error.value = null
    
    try {
      currentTestSet.value = await testsetApi.getTestSet(id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取测试集详情失败'
    } finally {
      loading.value = false
    }
  }

  async function createTestSet(data: { document_id: string; name: string; description?: string }) {
    loading.value = true
    error.value = null
    
    try {
      const testSet = await testsetApi.createTestSet(data)
      // 添加到列表顶部
      testSets.value.unshift(testSet)
      pagination.value.total++
      return testSet
    } catch (e: any) {
      error.value = e.response?.data?.detail || '创建测试集失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateTestSet(id: string, data: Partial<TestSet>) {
    loading.value = true
    error.value = null
    
    try {
      const updatedTestSet = await testsetApi.updateTestSet(id, data)
      const index = testSets.value.findIndex(ts => ts.id === id)
      if (index !== -1) {
        testSets.value[index] = updatedTestSet
      }
      currentTestSet.value = updatedTestSet
      return updatedTestSet
    } catch (e: any) {
      error.value = e.response?.data?.detail || '更新测试集失败'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteTestSet(id: string) {
    try {
      await testsetApi.deleteTestSet(id)
      testSets.value = testSets.value.filter(ts => ts.id !== id)
      pagination.value.total--
      if (currentTestSet.value?.id === id) {
        currentTestSet.value = null
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || '删除测试集失败'
      throw e
    }
  }

  function setPage(page: number) {
    pagination.value.page = page
    fetchTestSets()
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.page = 1
    fetchTestSets()
  }

  function clearFilters() {
    filters.value = { document_id: undefined }
    pagination.value.page = 1
    fetchTestSets()
  }

  return {
    testSets,
    currentTestSet,
    loading,
    error,
    pagination,
    filters,
    hasTestSets,
    fetchTestSets,
    fetchTestSet,
    createTestSet,
    updateTestSet,
    deleteTestSet,
    setPage,
    setFilters,
    clearFilters
  }
})