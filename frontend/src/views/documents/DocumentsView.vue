<template>
  <div class="page documents-page">
    <el-card shadow="never" class="section" :body-style="{ padding: '16px' }">
      <template #header>
        <div class="card-header">
          <span class="page-title">文档管理</span>
          <el-button type="primary" @click="showUploadDialog = true">
            <el-icon><Upload /></el-icon>
            上传文档
          </el-button>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-input
          v-model="searchText"
          placeholder="搜索文档"
          style="width: 200px;"
          clearable
          @clear="handleSearch"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        
        <el-select
          v-model="statusFilter"
          placeholder="状态"
          clearable
          style="width: 140px;"
          @change="handleFilterChange"
        >
          <el-option label="全部" value="" />
          <el-option label="未分析" value="unanalyzed" />
          <el-option label="分析中" value="processing" />
          <el-option label="活跃" value="active" />
          <el-option label="停用" value="inactive" />
        </el-select>
        
        <el-select
          v-model="categoryFilter"
          placeholder="文档分类"
          clearable
          style="width: 150px;"
          @change="handleFilterChange"
          filterable
          allow-create
          default-first-option
        >
          <el-option label="全部" value="" />
          <el-option label="内部产品" value="内部产品" />
          <el-option label="外部产品" value="外部产品" />
          <el-option label="公司制度" value="公司制度" />
          <el-option label="公开文件" value="公开文件" />
          <el-option label="未分类" value="未分类" />
          <el-option label="自定义" value="custom" />
        </el-select>
      </div>
      
      <div class="table-toolbar section-sm">
        <el-select 
          v-model="batchOperation" 
          placeholder="选择操作"
          style="width: 120px;"
          :disabled="multipleSelection.length === 0"
        >
          <el-option label="分析" value="analyze" />
          <el-option label="启用" value="enable" />
          <el-option label="停用" value="disable" />
          <el-option label="删除" value="delete" />
        </el-select>
        <el-button 
          @click="handleBatchOperation"
          :disabled="multipleSelection.length === 0 || !batchOperation"
        >
          批量操作
        </el-button>
        <span class="selection-info" v-if="multipleSelection.length > 0">
          已选择 {{ multipleSelection.length }} 项
        </span>
      </div>
      
      <el-table
        v-loading="documentStore.loading"
        :data="documentStore.documents"
        style="width: 100%"
        size="small"
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="55" />
        <el-table-column prop="filename" label="文件名" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="viewDocument(row.id)">
              {{ row.filename }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="page_count" label="页数" width="80">
          <template #default="{ row }">
            {{ getPageCountText(row) }}
          </template>
        </el-table-column>
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag :type="getCategoryType(row.category)">
              {{ row.category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(getUnifiedStatus(row))">
              {{ getStatusText(getUnifiedStatus(row)) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="240" fixed="right">
          <template #default="{ row }">
            <div class="button-row">
              <el-button 
                link
                type="primary" 
                size="small"
                :disabled="isAnalyzing[row.id]"
                @click="viewDocument(row.id)"
              >
                查看
              </el-button>
              <el-button 
                link
                type="primary" 
                size="small"
                :loading="isDocumentProcessing(row)"
                :disabled="row.is_analyzed || isDocumentProcessing(row)"
                @click="analyzeDocument(row)"
              >
                {{ isDocumentProcessing(row) ? '分析中' : (row.is_analyzed ? '已分析' : '分析') }}
              </el-button>
              <el-button 
                link
                type="primary"
                size="small"
                @click="toggleDocumentStatus(row)"
              >
                {{ row.status === 'active' ? '停用' : '启用' }}
              </el-button>
              <el-button 
                link
                type="danger" 
                size="small"
                :disabled="isAnalyzing[row.id]"
                @click="handleDelete(row)"
              >
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="documentStore.pagination.size"
          :total="documentStore.pagination.total"
          layout="total, prev, pager, next"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <el-dialog
      v-model="showUploadDialog"
      title="上传文档"
      width="500px"
    >
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :multiple="true"
        :on-change="handleFileChange"
        :on-select="handleFileChange"
        accept=".pdf,.docx,.xlsx,.txt,.md"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 PDF、DOCX、XLSX 格式，最大 50MB
          </div>
        </template>
      </el-upload>
      
      <div class="upload-category-section" style="margin-top: 20px;">
        <label style="display: block; margin-bottom: 8px;">文档分类:</label>
        <el-select
          v-model="uploadCategory"
          placeholder="请选择文档分类"
          style="width: 70%; margin-right: 10px;"
          filterable
          allow-create
          default-first-option
        >
          <el-option label="内部产品" value="内部产品" />
          <el-option label="外部产品" value="外部产品" />
          <el-option label="公司制度" value="公司制度" />
          <el-option label="公开文件" value="公开文件" />
          <el-option label="自定义" value="custom" />
          <el-option label="未分类" value="未分类" />
        </el-select>
        <el-input
          v-if="uploadCategory === 'custom'"
          v-model="customCategory"
          placeholder="请输入自定义分类"
          style="width: 28%;"
        />
      </div>
      
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          上传
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Upload, Search, UploadFilled } from '@element-plus/icons-vue'
import { useDocumentStore } from '@/stores/document'
import { documentApi } from '@/api/documents'
import { useTaskStore } from '@/stores/task'
import { formatDateTime } from '@/utils/format'
import type { UploadFile } from 'element-plus'
import type { Document } from '@/types'

const router = useRouter()
const documentStore = useDocumentStore()
const taskStore = useTaskStore()

const searchText = ref('')
const statusFilter = ref('')
const categoryFilter = ref('')
const currentPage = ref(1)
const showUploadDialog = ref(false)
const uploading = ref(false)
const selectedFiles = ref<File[]>([])
const uploadRef = ref()
const isAnalyzing = ref<Record<string, boolean>>({})
const uploadCategory = ref('未分类')
const customCategory = ref('')
const multipleSelection = ref<Document[]>([])
const batchOperation = ref('')
let pollingTimer: any = null
let pollingStartedAt = 0
const MAX_POLLING_DURATION_MS = 15 * 60 * 1000

const updateDocumentTasksByTarget = (
  documentId: string,
  updates: { progress?: number; status?: 'running' | 'completed' | 'failed'; error?: string }
) => {
  const matchedTasks = taskStore.tasks.filter(
    task => task.type === 'document' && task.targetId === documentId
  )
  matchedTasks.forEach(task => taskStore.updateTask(task.id, updates))
}

const pollDocumentTaskStatus = (taskId: string, documentId: string) => {
  const poll = async () => {
    const currentTask = taskStore.getTask(taskId)
    if (!currentTask || !['running', 'pending', 'cancelling'].includes(currentTask.status)) {
      return
    }

    try {
      const task = await documentApi.getTaskStatus(taskId)
      taskStore.updateTask(taskId, {
        progress: typeof task.progress === 'number' ? Math.round(task.progress * 100) : 0,
        message: task.message,
        currentStep: task.current_step ?? undefined,
        totalSteps: task.total_steps ?? undefined,
      })

      if (task.status === 'finished') {
        isAnalyzing.value[documentId] = false
        taskStore.updateTask(taskId, { progress: 100, status: 'completed' })
        await documentStore.fetchDocuments({
          status: statusFilter.value === 'unanalyzed' ? 'active' : (statusFilter.value || undefined),
          is_analyzed: statusFilter.value === 'unanalyzed' ? false : (statusFilter.value === 'active' ? true : undefined),
          category: categoryFilter.value || undefined
        })
        return
      }

      if (task.status === 'cancelled') {
        isAnalyzing.value[documentId] = false
        taskStore.updateTask(taskId, { status: 'cancelled', error: task.error || '任务已取消' })
        await documentStore.fetchDocuments({
          status: statusFilter.value === 'unanalyzed' ? 'active' : (statusFilter.value || undefined),
          is_analyzed: statusFilter.value === 'unanalyzed' ? false : (statusFilter.value === 'active' ? true : undefined),
          category: categoryFilter.value || undefined
        })
        return
      }

      if (task.status === 'failed') {
        isAnalyzing.value[documentId] = false
        taskStore.updateTask(taskId, { status: 'failed', error: task.error || '文档分析失败' })
        await documentStore.fetchDocuments({
          status: statusFilter.value === 'unanalyzed' ? 'active' : (statusFilter.value || undefined),
          is_analyzed: statusFilter.value === 'unanalyzed' ? false : (statusFilter.value === 'active' ? true : undefined),
          category: categoryFilter.value || undefined
        })
        return
      }
    } catch {
      // 忽略单次查询失败，继续重试
    }

    window.setTimeout(poll, 2000)
  }

  poll()
}

const startPolling = () => {
  if (pollingTimer) return
  pollingStartedAt = Date.now()
  
  pollingTimer = setInterval(() => {
    const elapsed = Date.now() - pollingStartedAt
    if (elapsed > MAX_POLLING_DURATION_MS) {
      stopPolling()
      documentStore.documents
        .filter(doc => doc.status === 'processing')
        .forEach(doc => {
          isAnalyzing.value[doc.id] = false
          updateDocumentTasksByTarget(doc.id, { status: 'failed', error: '文档解析超时，请重试' })
        })
      ElMessage.warning('文档解析超时，已停止自动轮询，请刷新后重试解析')
      return
    }

    // 检查是否还有正在处理中的文档
    const hasProcessing = documentStore.documents.some(doc => doc.status === 'processing')
    if (hasProcessing) {
      documentStore.fetchDocuments({
        status: statusFilter.value === 'unanalyzed' ? 'active' : (statusFilter.value || undefined),
        is_analyzed: statusFilter.value === 'unanalyzed' ? false : (statusFilter.value === 'active' ? true : undefined),
        category: categoryFilter.value || undefined
      })
    } else {
      stopPolling()
    }
  }, 5000) // 每 5 秒轮询一次
}

const stopPolling = () => {
  if (pollingTimer) {
    clearInterval(pollingTimer)
    pollingTimer = null
  }
  pollingStartedAt = 0
}

// 监听文档列表，同步更新全局任务状态
watch(() => documentStore.documents, (newDocs, oldDocs) => {
  const hasProcessing = newDocs.some(doc => doc.status === 'processing')
  if (hasProcessing) {
    startPolling()
  } else {
    stopPolling()
  }
  
  // 对比新旧列表，同步状态到全局任务中心
  if (oldDocs) {
    oldDocs.forEach(oldDoc => {
      const newDoc = newDocs.find(d => d.id === oldDoc.id)
      const task = taskStore.getTask(oldDoc.id)
      
      if (task && newDoc) {
        // 从处理中变为完成或失败
        if (oldDoc.status === 'processing' && newDoc.status !== 'processing') {
          isAnalyzing.value[newDoc.id] = false
          if (newDoc.is_analyzed) {
            updateDocumentTasksByTarget(newDoc.id, { progress: 100, status: 'completed' })
          } else {
            updateDocumentTasksByTarget(newDoc.id, { status: 'failed', error: '文档分析失败或被中断' })
          }
        }
      }
    })
  }
}, { deep: true })

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    unanalyzed: 'info',
    active: 'success',
    processing: 'warning',
    inactive: 'danger',
    failed: 'danger'
  }
  return types[status] || 'info'
}

const getLatestDocumentTask = (documentId: string) => {
  return taskStore.tasks.find(task => task.type === 'document' && task.targetId === documentId)
}

const isDocumentProcessing = (doc: Document) => {
  if (isAnalyzing.value[doc.id]) return true
  const latestTask = getLatestDocumentTask(doc.id)
  if (latestTask) {
    if (latestTask.status === 'failed' || latestTask.status === 'cancelled' || latestTask.status === 'completed') {
      return false
    }
    if (latestTask.status === 'running' || latestTask.status === 'pending' || latestTask.status === 'cancelling') {
      return true
    }
  }
  return doc.status === 'processing'
}

const getUnifiedStatus = (doc: Document): 'unanalyzed' | 'processing' | 'active' | 'inactive' | 'failed' => {
  const latestTask = getLatestDocumentTask(doc.id)
  if (latestTask && latestTask.status === 'failed') return 'failed'
  if (isDocumentProcessing(doc)) return 'processing'
  if (doc.status === 'inactive') return 'inactive'
  if (!doc.is_analyzed) return 'unanalyzed'
  return 'active'
}

const getCategoryType = (category: string) => {
  const types: Record<string, string> = {
    '内部产品': 'primary',
    '外部产品': 'success',
    '公司制度': 'warning',
    '公开文件': 'info',
    '其他': 'info',
    '未分类': 'info'
  }
  return (types[category] || 'info') as any
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    unanalyzed: '未分析',
    active: '活跃',
    processing: '分析中',
    inactive: '停用',
    failed: '分析失败'
  }
  return texts[status] || status
}

const getPageCountText = (doc: Document) => {
  if (typeof doc.page_count === 'number' && doc.page_count > 0) {
    return doc.page_count
  }
  const meta = (doc.doc_metadata || {}) as Record<string, any>
  const fallback = meta.page_count ?? meta.total_pages ?? meta.pages
  return (typeof fallback === 'number' && fallback > 0) ? fallback : '-'
}

const handleSearch = () => {
  currentPage.value = 1
  fetchDocuments()
}

const handleFilterChange = () => {
  currentPage.value = 1
  fetchDocuments()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  documentStore.setPage(page)
}

const fetchDocuments = () => {
  return documentStore.fetchDocuments({
    status: statusFilter.value === 'unanalyzed' ? 'active' : (statusFilter.value || undefined),
    is_analyzed: statusFilter.value === 'unanalyzed' ? false : (statusFilter.value === 'active' ? true : undefined),
    category: categoryFilter.value || undefined
  })
}

const viewDocument = (id: string) => {
  router.push(`/documents/${id}`)
}

const handleSelectionChange = (val: Document[]) => {
  multipleSelection.value = val
}

const handleBatchOperation = async () => {
  if (multipleSelection.value.length === 0 || !batchOperation.value) {
    ElMessage.warning('请先选择文档和操作类型')
    return
  }
  
  const operationName = {
    'analyze': '分析',
    'enable': '启用',
    'disable': '停用',
    'delete': '删除'
  }[batchOperation.value] || '操作'
  
  try {
    await ElMessageBox.confirm(
      `确定要对选中的 ${multipleSelection.value.length} 个文档执行"${operationName}"操作吗？`,
      '操作确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    switch (batchOperation.value) {
      case 'analyze':
        await handleBatchAnalyze()
        break
      case 'enable':
        await handleBatchEnable()
        break
      case 'disable':
        await handleBatchDisable()
        break
      case 'delete':
        await handleBatchDelete()
        break
      default:
        ElMessage.error('未知的操作类型')
        return
    }
    
    // 重置选择和操作类型
    multipleSelection.value = []
    batchOperation.value = ''
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('批量操作失败')
    }
  }
}

const handleBatchAnalyze = async () => {
  // 过滤掉已经分析过的文档
  const unanalyzedDocs = multipleSelection.value.filter(doc => !doc.is_analyzed)
  
  if (unanalyzedDocs.length === 0) {
    ElMessage.info('选中的文档都已经分析过了')
    return
  }
  
  try {
    const documentIds = unanalyzedDocs.map(doc => doc.id)
    const result = await documentApi.analyzeDocumentsBatch(documentIds)
    
    // 添加批量分析任务到全局任务列表（使用真实 task_id）
    result.results.forEach(item => {
      if (item.status !== 'processing' || !item.task_id) return
      taskStore.addTask({
        id: item.task_id,
        name: `解析文档: ${item.filename}`,
        type: 'document',
        progress: 0,
        status: 'running',
        targetId: item.document_id
      })
      pollDocumentTaskStatus(item.task_id, item.document_id)
    })

    ElMessage.success(result.message)
    
    // 更新UI显示
    fetchDocuments()
  } catch (error: any) {
    console.error('批量分析失败:', error)
    ElMessage.error(error?.response?.data?.detail || '批量分析失败')
  }
}

const handleBatchEnable = async () => {
  try {
    // 这里需要调用后端API来启用文档
    const updatePromises = multipleSelection.value.map(doc => 
      documentApi.updateDocument(doc.id, { status: 'active' })
    )
    await Promise.all(updatePromises)
    
    ElMessage.success(`成功启用 ${multipleSelection.value.length} 个文档`)
  } catch (error: any) {
    console.error('启用失败:', error)
    ElMessage.error(`启用失败: ${error?.response?.data?.detail || '操作失败'}`)
  }
  fetchDocuments()
}

const handleBatchDisable = async () => {
  try {
    // 这里需要调用后端API来停用文档
    const updatePromises = multipleSelection.value.map(doc => 
      documentApi.updateDocument(doc.id, { status: 'inactive' })
    )
    await Promise.all(updatePromises)
    
    ElMessage.success(`成功停用 ${multipleSelection.value.length} 个文档`)
  } catch (error: any) {
    console.error('停用失败:', error)
    ElMessage.error(`停用失败: ${error?.response?.data?.detail || '操作失败'}`)
  }
  fetchDocuments()
}

const handleBatchDelete = async () => {
  const selectedDocs = [...multipleSelection.value]
  const selectedCount = selectedDocs.length
  if (selectedCount === 0) {
    ElMessage.warning('请先选择要删除的文档')
    return
  }

  try {
    const deletePromises = selectedDocs.map(doc => documentStore.deleteDocument(doc.id))
    await Promise.all(deletePromises)

    // 删除后重新拉取列表，避免出现“总数有值但当前页空数据”的分页越界
    await fetchDocuments()
    if (documentStore.documents.length === 0 && documentStore.pagination.total > 0 && currentPage.value > 1) {
      currentPage.value -= 1
      await documentStore.setPage(currentPage.value)
    }

    ElMessage.success(`成功删除 ${selectedCount} 个文档`)
  } catch (error: any) {
    console.error('删除失败:', error)
    ElMessage.error(`删除失败: ${error?.response?.data?.detail || '删除失败'}`)
  }
}

const analyzeDocument = async (doc: Document) => {
  // 设置按钮为加载状态
  isAnalyzing.value[doc.id] = true
  
  try {
    const result = await documentApi.analyzeDocument(doc.id)
    
    // 添加到全局任务列表
    taskStore.addTask({
      id: result.task_id,
      name: `解析文档: ${doc.filename}`,
      type: 'document',
      progress: 0,
      status: 'running',
      targetId: doc.id
    })
    pollDocumentTaskStatus(result.task_id, doc.id)
    
    ElMessage.success(result.message || '文档分析已启动')
    
    fetchDocuments()
  } catch (error: any) {
    console.error('分析失败:', error)
    ElMessage.error(error?.response?.data?.detail || '启动分析失败')
  } finally {
    // 注意：如果是异步任务，不要立即移除按钮加载状态，让轮询来接管
    // 只有在同步出错时才重置状态
    if (!taskStore.tasks.some(task => task.type === 'document' && task.targetId === doc.id && (task.status === 'running' || task.status === 'pending'))) {
      isAnalyzing.value[doc.id] = false
    }
  }
}

const toggleDocumentStatus = async (doc: Document) => {
  try {
    const newStatus = doc.status === 'active' ? 'inactive' : 'active'
    const actionText = doc.status === 'active' ? '停用' : '启用'
    
    await ElMessageBox.confirm(
      `确定要${actionText}文档 "${doc.filename}" 吗？`,
      '状态确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await documentApi.updateDocument(doc.id, { status: newStatus })
    ElMessage.success(`${actionText}成功`)
    fetchDocuments()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('操作失败')
    }
  }
}

const handleDelete = async (doc: Document) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${doc.filename}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await documentStore.deleteDocument(doc.id)
    ElMessage.success('删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleFileChange = (file: UploadFile) => {
  console.log('handleFileChange called:', file)
  console.log('file.raw:', file?.raw)
  // 不再单独设置 selectedFile，而是收集所有文件
  if (file.raw) {
    // 如果是新文件，添加到数组中
    if (!selectedFiles.value.some(f => f.name === file.raw!.name && f.size === file.raw!.size)) {
      selectedFiles.value.push(file.raw!)
    }
  } else {
    console.log('file.raw is undefined!')
  }
}

const handleUpload = async () => {
  console.log('handleUpload called')
  console.log('selectedFiles:', selectedFiles.value)
  
  if (!selectedFiles.value || selectedFiles.value.length === 0) {
    ElMessage.warning('请选择要上传的文件')
    return
  }
  
  uploading.value = true
  console.log('Starting upload for:', selectedFiles.value.length, 'files')
  
  // 确定要使用的分类
  let finalCategory = uploadCategory.value
  if (uploadCategory.value === 'custom' && customCategory.value.trim()) {
    finalCategory = customCategory.value.trim()
  } else if (uploadCategory.value === 'custom' && !customCategory.value.trim()) {
    // 如果选择了自定义但没有输入，则使用默认值
    finalCategory = '未分类'
  } else if (!uploadCategory.value) {
    finalCategory = '未分类'
  }
  
  try {
    // 使用批量上传方法，支持立即分析
    const formData = new FormData()
    selectedFiles.value.forEach(file => formData.append('files', file))
    formData.append('category', finalCategory)
    formData.append('analyze', 'false') // 默认不立即分析，用户可以在上传后选择分析
    
    await documentStore.uploadDocumentsBatch(selectedFiles.value, finalCategory)
    
    ElMessage.success(`成功上传 ${selectedFiles.value.length} 个文件`)
    showUploadDialog.value = false
    selectedFiles.value = [] // 清空文件列表
    uploadCategory.value = '未分类' // 重置分类选择
    customCategory.value = '' // 清空自定义分类
    uploadRef.value?.clearFiles()
    fetchDocuments()
  } catch (error) {
    console.error('Upload error:', error)
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

onUnmounted(() => {
  stopPolling()
})

onMounted(() => {
  fetchDocuments()
})
</script>

<style lang="scss" scoped>
.documents-page {
  .page-title {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: var(--space-16, 16px);
    flex-wrap: wrap;
  }
  
  .table-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .selection-info {
      color: var(--text-2, #909399);
      font-size: var(--font-14, 14px);
    }
  }
  
  .button-row {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 4px;
    align-items: center;
    width: 100%;
    white-space: nowrap;
  }

  .button-row :deep(.el-button) {
    width: 100%;
    margin: 0;
    min-width: 0;
    padding: 0;
    justify-content: center;
  }
  
  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: var(--space-16, 16px);
  }
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid var(--border-1, #ebeef5);
}

:deep(.el-table) {
  --el-table-header-bg-color: var(--bg-app, #f8fafc);
  --el-table-header-text-color: var(--text-2, #606266);
  border-radius: var(--radius-8, 8px);
  overflow: hidden;
  
  th.el-table__cell {
    font-weight: 500;
  }
}
</style>
