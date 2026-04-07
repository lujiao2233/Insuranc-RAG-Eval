<template>
  <div class="documents-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>文档管理</span>
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
          style="width: 120px;"
          @change="handleFilterChange"
        >
          <el-option label="全部" value="" />
          <el-option label="活跃" value="active" />
          <el-option label="处理中" value="processing" />
          <el-option label="停用" value="inactive" />
        </el-select>
        
        <el-select
          v-model="analyzedFilter"
          placeholder="分析状态"
          clearable
          style="width: 120px;"
          @change="handleFilterChange"
        >
          <el-option label="已分析" :value="true" />
          <el-option label="未分析" :value="false" />
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
      
      <div class="table-toolbar">
        <el-select 
          v-model="batchOperation" 
          placeholder="选择操作"
          style="width: 120px; margin-right: 10px;"
          :disabled="multipleSelection.length === 0"
        >
          <el-option label="分析" value="analyze" />
          <el-option label="启用" value="enable" />
          <el-option label="停用" value="disable" />
          <el-option label="删除" value="delete" />
        </el-select>
        <el-button 
          @click="handleBatchOperation"
          type="primary"
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
        <el-table-column prop="file_type" label="类型" width="80" />
        <el-table-column prop="file_size" label="大小" width="100">
          <template #default="{ row }">
            {{ formatFileSize(row.file_size) }}
          </template>
        </el-table-column>
        <el-table-column prop="page_count" label="页数" width="80" />
        <el-table-column prop="category" label="分类" width="120">
          <template #default="{ row }">
            <el-tag :type="getCategoryType(row.category)">
              {{ row.category }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_analyzed" label="分析状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_analyzed ? 'success' : 'info'">
              {{ row.is_analyzed ? '已分析' : '未分析' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="upload_time" label="上传时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.upload_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="button-row">
              <el-button 
                type="primary" 
                size="small"
                :disabled="isAnalyzing[row.id]"
                @click="viewDocument(row.id)"
                class="fixed-width-btn"
              >
                查看
              </el-button>
              <el-button 
                type="warning" 
                size="small"
                :loading="isAnalyzing[row.id]" 
                :disabled="row.is_analyzed || isAnalyzing[row.id]"
                @click="analyzeDocument(row)"
                class="fixed-width-btn"
              >
                {{ isAnalyzing[row.id] ? '分析中' : (row.is_analyzed ? '已分析' : '分析') }}
              </el-button>
            </div>
            <div class="button-row">
              <el-button 
                :type="row.status === 'active' ? 'info' : 'success'"
                size="small"
                @click="toggleDocumentStatus(row)"
                class="fixed-width-btn"
              >
                {{ row.status === 'active' ? '停用' : '启用' }}
              </el-button>
              <el-button 
                type="danger" 
                size="small"
                :disabled="isAnalyzing[row.id]"
                @click="handleDelete(row)"
                class="fixed-width-btn"
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
import { formatFileSize, formatDateTime } from '@/utils/format'
import type { UploadFile } from 'element-plus'
import type { Document } from '@/types'

const router = useRouter()
const documentStore = useDocumentStore()

const searchText = ref('')
const statusFilter = ref('')
const analyzedFilter = ref<boolean | undefined>(undefined)
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

const startPolling = () => {
  if (pollingTimer) return
  
  pollingTimer = setInterval(() => {
    // 检查是否还有正在处理中的文档
    const hasProcessing = documentStore.documents.some(doc => doc.status === 'processing')
    if (hasProcessing) {
      documentStore.fetchDocuments({
        status: statusFilter.value || undefined,
        is_analyzed: analyzedFilter.value,
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
}

// 监听文档列表，如果有正在处理的文档，启动轮询
watch(() => documentStore.documents, (newDocs) => {
  const hasProcessing = newDocs.some(doc => doc.status === 'processing')
  if (hasProcessing) {
    startPolling()
  } else {
    stopPolling()
  }
}, { deep: true })

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    active: 'success',
    processing: 'warning',
    inactive: 'danger'
  }
  return types[status] || 'info'
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
    active: '活跃',
    processing: '处理中',
    inactive: '停用'
  }
  return texts[status] || status
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
  documentStore.fetchDocuments({
    status: statusFilter.value || undefined,
    is_analyzed: analyzedFilter.value,
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
  try {
    const deletePromises = multipleSelection.value.map(doc => documentStore.deleteDocument(doc.id))
    await Promise.all(deletePromises)
    
    ElMessage.success(`成功删除 ${multipleSelection.value.length} 个文档`)
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
    
    ElMessage.success(result.message || '文档分析已启动')
    
    fetchDocuments()
  } catch (error: any) {
    console.error('分析失败:', error)
    ElMessage.error(error?.response?.data?.detail || '启动分析失败')
  } finally {
    // 移除加载状态
    isAnalyzing.value[doc.id] = false
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
.documents-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .filter-bar {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }
  
  .table-toolbar {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
    
    .selection-info {
      color: #909399;
      font-size: 14px;
    }
  }
  
  .button-row {
    display: flex;
    gap: 4px;
    margin-bottom: 4px;
    
    &:last-child {
      margin-bottom: 0;
    }
  }
  
  .fixed-width-btn {
    min-width: 60px;
  }
  
  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 16px;
  }
}
</style>