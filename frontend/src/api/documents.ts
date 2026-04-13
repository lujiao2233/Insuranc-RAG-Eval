import { request } from './index'
import type { Document, PaginatedResponse } from '@/types'

export const documentApi = {
  getDocuments(params: {
    skip?: number
    limit?: number
    status?: string
    is_analyzed?: boolean
    category?: string
  }): Promise<PaginatedResponse<Document>> {
    return request.get('/documents/', params)
  },

  getDocument(id: string): Promise<Document> {
    return request.get(`/documents/${id}`)
  },

  uploadDocument(file: File, onProgress?: (percent: number) => void, category: string = '未分类'): Promise<Document> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('category', category)
    return request.post('/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (progressEvent) => {
        if (onProgress) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
          onProgress(percentCompleted)
        }
      }
    })
  }, 

  uploadDocumentsBatch(files: File[], category: string = '未分类'): Promise<Document[]> {
    const formData = new FormData()
    files.forEach(file => formData.append('files', file))
    formData.append('category', category)
    return request.post('/documents/upload-batch', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },

  deleteDocument(id: string): Promise<void> {
    return request.delete(`/documents/${id}`)
  },

  downloadDocument(id: string): Promise<Blob> {
    return request.get(`/documents/${id}/download`, {}, { responseType: 'blob' })
  },

  getStats(): Promise<{
    total_documents: number
    analyzed_documents: number
    unanalyzed_documents: number
    type_distribution: Record<string, number>
  }> {
    return request.get('/documents/stats/summary')
  },

  updateDocument(id: string, data: Partial<Document>): Promise<Document> {
    return request.put(`/documents/${id}`, data)
  },

  analyzeDocument(id: string): Promise<{ task_id: string; message: string }> {
    return request.post(`/documents/${id}/analyze`)
  },

  getDocumentChunks(id: string, params: { skip?: number; limit?: number; keyword?: string; entity_type?: string }): Promise<PaginatedResponse<any>> {
    return request.get(`/documents/${id}/chunks`, params)
  },

  getTaskStatus(taskId: string): Promise<any> {
    return request.get(`/testsets/tasks/${taskId}`)
  },

  analyzeDocumentsBatch(documentIds: string[]): Promise<{
    message: string
    results: Array<{
      document_id: string
      filename: string
      status: string
      message: string
      task_id?: string
    }>
    total: number
  }> {
    const params = new URLSearchParams()
    documentIds.forEach(id => params.append('document_ids', id))
    return request.post(`/documents/analyze-batch?${params.toString()}`)
  },

  getDocumentContent(id: string): Promise<{
    document_id: string
    filename: string
    content: string
    metadata: any
    is_analyzed: boolean
  }> {
    return request.get(`/documents/${id}/content`)
  }
}
