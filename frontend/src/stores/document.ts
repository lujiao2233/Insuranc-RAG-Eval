import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { documentApi } from '@/api/documents'
import type { Document, PaginatedResponse } from '@/types'

export const useDocumentStore = defineStore('document', () => {
  const documents = ref<Document[]>([])
  const currentDocument = ref<Document | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const error = ref<string | null>(null)
  const pagination = ref({
    page: 1,
    size: 10,
    total: 0,
    pages: 0
  })
  const filters = ref({
    status: undefined as string | undefined,
    is_analyzed: undefined as boolean | undefined
  })

  const hasDocuments = computed(() => documents.value.length > 0)
  const analyzedCount = computed(() => 
    documents.value.filter(d => d.is_analyzed).length
  )
  const unanalyzedCount = computed(() => 
    documents.value.filter(d => !d.is_analyzed).length
  )

  async function fetchDocuments(params?: { status?: string; is_analyzed?: boolean }) {
    loading.value = true
    error.value = null
    
    try {
      const query = { ...filters.value, ...params }
      const response: PaginatedResponse<Document> = await documentApi.getDocuments({
        skip: (pagination.value.page - 1) * pagination.value.size,
        limit: pagination.value.size,
        ...query
      })
      
      documents.value = response.items
      pagination.value = {
        page: response.page,
        size: response.size,
        total: response.total,
        pages: response.pages
      }
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取文档列表失败'
    } finally {
      loading.value = false
    }
  }

  async function fetchDocument(id: string) {
    loading.value = true
    error.value = null
    
    try {
      currentDocument.value = await documentApi.getDocument(id)
    } catch (e: any) {
      error.value = e.response?.data?.detail || '获取文档详情失败'
    } finally {
      loading.value = false
    }
  }

  async function uploadDocument(file: File, onProgress?: (percent: number) => void, category: string = '未分类') {
    uploading.value = true
    error.value = null
    
    try {
      const document = await documentApi.uploadDocument(file, onProgress, category)
      // 检查文档是否已存在于列表中，避免重复添加
      const existingIndex = documents.value.findIndex(d => d.id === document.id)
      if (existingIndex === -1) {
        documents.value.unshift(document)
        pagination.value.total++
      }
      return document
    } catch (e: any) {
      error.value = e.response?.data?.detail || '上传文档失败'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function deleteDocument(id: string) {
    try {
      await documentApi.deleteDocument(id)
      documents.value = documents.value.filter(d => d.id !== id)
      pagination.value.total--
    } catch (e: any) {
      error.value = e.response?.data?.detail || '删除文档失败'
      throw e
    }
  }

  async function uploadDocumentsBatch(files: File[], category: string = '未分类', analyzeImmediately: boolean = false) {
    uploading.value = true
    error.value = null
    
    try {
      // 使用新的API，支持立即分析
      const formData = new FormData()
      files.forEach(file => formData.append('files', file))
      formData.append('category', category)
      formData.append('analyze', analyzeImmediately.toString())
      
      const newDocuments = await documentApi.uploadDocumentsBatch(files, category)
      // 避免重复添加文档
      for (const newDoc of newDocuments) {
        const existingIndex = documents.value.findIndex(d => d.id === newDoc.id)
        if (existingIndex === -1) {
          documents.value.unshift(newDoc)
        }
      }
      pagination.value.total += newDocuments.length
      return newDocuments
    } catch (e: any) {
      error.value = e.response?.data?.detail || '批量上传文档失败'
      throw e
    } finally {
      uploading.value = false
    }
  }

  function setPage(page: number) {
    pagination.value.page = page
    fetchDocuments()
  }

  function setFilters(newFilters: Partial<typeof filters.value>) {
    filters.value = { ...filters.value, ...newFilters }
    pagination.value.page = 1
    fetchDocuments()
  }

  function clearFilters() {
    filters.value = { status: undefined, is_analyzed: undefined }
    pagination.value.page = 1
    fetchDocuments()
  }

  return {
    documents,
    currentDocument,
    loading,
    uploading,
    error,
    pagination,
    filters,
    hasDocuments,
    analyzedCount,
    unanalyzedCount,
    fetchDocuments,
    fetchDocument,
    uploadDocument,
    uploadDocumentsBatch,
    deleteDocument,
    setPage,
    setFilters,
    clearFilters
  }
})
