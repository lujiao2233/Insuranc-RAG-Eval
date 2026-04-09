<template>
  <div class="document-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">{{ document?.filename }}</span>
      </template>
    </el-page-header>

    <div v-if="analysisTask" class="analysis-progress mt-4">
      <el-alert
        :title="`文档分析中: ${analysisTask.message || '正在处理...'}`"
        type="info"
        :closable="false"
        show-icon
      >
        <el-progress 
          :percentage="Math.round(analysisTask.progress * 100)" 
          :status="analysisTask.status === 'finished' ? 'success' : analysisTask.status === 'failed' ? 'exception' : ''"
          class="mt-2"
        />
      </el-alert>
    </div>
    
    <el-divider />
    
    <el-row :gutter="20" v-if="document">
      <el-col :span="18">
        <el-tabs v-model="activeTab" type="border-card">
          <el-tab-pane label="基本信息" name="info">
            <el-descriptions :column="2" border>
              <el-descriptions-item label="文件名">{{ document.filename }}</el-descriptions-item>
              <el-descriptions-item label="文件类型">{{ document.file_type }}</el-descriptions-item>
              <el-descriptions-item label="文件大小">{{ formatFileSize(document.file_size) }}</el-descriptions-item>
              <el-descriptions-item label="页数">{{ getPageCountDisplay(document) }}</el-descriptions-item>
              <el-descriptions-item label="分析状态">
                <el-tag :type="document.is_analyzed ? 'success' : 'info'">
                  {{ document.is_analyzed ? '已分析' : '未分析' }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="上传时间">{{ formatDateTime(document.upload_time) }}</el-descriptions-item>
              <el-descriptions-item label="产品实体" :span="2" v-if="document.product_entities">
                <el-tag 
                  v-for="entity in document.product_entities" 
                  :key="entity" 
                  class="mr-2"
                  size="small"
                >
                  {{ entity }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>

            <div class="mt-4" v-if="document.doc_metadata">
              <h4>元数据详情</h4>
              <el-descriptions :column="2" border>
                <el-descriptions-item
                  v-for="(value, key) in document.doc_metadata"
                  :key="key"
                  :label="getMetadataLabel(key)"
                >
                  {{ typeof value === 'object' ? JSON.stringify(value) : value }}
                </el-descriptions-item>
              </el-descriptions>
            </div>
          </el-tab-pane>

          <el-tab-pane label="智能提纲" name="outline" v-if="document.is_analyzed">
            <div class="outline-tree">
              <el-tree 
                :data="document.outline" 
                :props="{ label: 'title', children: 'children' }"
                default-expand-all
              >
                <template #default="{ node, data }">
                  <div class="custom-tree-node">
                    <span class="node-title">{{ data.title }}</span>
                    <el-tooltip :content="data.summary" placement="right" v-if="data.summary">
                      <el-icon class="ml-2"><InfoFilled /></el-icon>
                    </el-tooltip>
                  </div>
                </template>
              </el-tree>
            </div>
          </el-tab-pane>

          <el-tab-pane label="已切片段" name="chunks" v-if="document.is_analyzed">
            <div class="chunk-filters mb-4">
              <el-input
                v-model="chunkQuery.keyword"
                placeholder="搜索片段关键词..."
                style="width: 300px"
                clearable
                @keyup.enter="fetchChunks"
              >
                <template #append>
                  <el-button @click="fetchChunks"><el-icon><Search /></el-icon></el-button>
                </template>
              </el-input>
              
            </div>

            <el-table 
              :data="chunks" 
              stripe 
              style="width: 100%" 
              v-loading="chunksLoading"
              @row-click="showChunkDetail"
              class="clickable-table"
            >
              <el-table-column prop="sequence_number" label="序号" width="80" />
              <el-table-column label="片段内容">
                <template #default="{ row }">
                  <div class="chunk-content-preview" v-html="truncateText(row.content, 200)"></div>
                  <div class="chunk-meta mt-2">
                    <el-tag size="small" type="info">MD5: {{ row.md5 }}</el-tag>
                    <el-tag size="small" type="warning" class="ml-2">位置: {{ row.start_char }} - {{ row.end_char }}</el-tag>
                    <template v-if="row.metadata?.knowledge_type">
                      <el-tag 
                        v-if="Array.isArray(row.metadata.knowledge_type)"
                        v-for="(type, index) in row.metadata.knowledge_type" 
                        :key="index"
                        size="small" 
                        type="success" 
                        class="ml-2"
                      >
                        {{ type }}
                      </el-tag>
                      <el-tag 
                        v-else
                        size="small" 
                        type="success" 
                        class="ml-2"
                      >
                        {{ row.metadata.knowledge_type }}
                      </el-tag>
                    </template>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container mt-4">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :total="totalChunks"
                layout="total, prev, pager, next"
                @current-change="handlePageChange"
              />
            </div>
          </el-tab-pane>
        </el-tabs>
      </el-col>
      
      <el-col :span="6">
        <el-card>
          <template #header>
            <span>操作</span>
          </template>
          
          <div class="action-buttons">
            <el-button type="primary" @click="handleDownload">
              <el-icon><Download /></el-icon>
              下载文档
            </el-button>
            <el-button 
              type="warning" 
              @click="startAnalysis" 
              :disabled="document.is_analyzed || document.status === 'processing'"
            >
              <el-icon><DataAnalysis /></el-icon>
              {{ document.is_analyzed ? '已分析' : '开始分析' }}
            </el-button>
            <el-button type="success" @click="createTestset" v-if="document.is_analyzed">
              <el-icon><Plus /></el-icon>
              创建测试集
            </el-button>
            <el-button type="danger" @click="handleDelete">
              <el-icon><Delete /></el-icon>
              删除文档
            </el-button>
          </div>
        </el-card>
        
        <el-card class="mt-4">
          <template #header>
            <span>关联测试集</span>
          </template>
          <el-empty v-if="!testsets.length" description="暂无关联测试集" />
          <div v-else>
            <div
              v-for="testset in testsets"
              :key="testset.id"
              class="testset-item"
              @click="$router.push(`/testsets/${testset.id}`)"
            >
              <span>{{ testset.name }}</span>
              <el-icon><ArrowRight /></el-icon>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 切片详情对话框 -->
    <el-dialog
      v-model="chunkDetailVisible"
      title="切片详情"
      width="800px"
      destroy-on-close
    >
      <div v-if="selectedChunk" class="chunk-detail-content">
        <div class="detail-section">
          <h4>片段内容</h4>
          <div class="full-content-box">
            <pre>{{ selectedChunk.content }}</pre>
          </div>
        </div>

        <el-divider />

        <div class="detail-section">
          <h4>元数据信息</h4>
          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="序号">{{ selectedChunk.sequence_number }}</el-descriptions-item>
            <el-descriptions-item label="MD5">{{ selectedChunk.md5 }}</el-descriptions-item>
            <el-descriptions-item label="起始字符">{{ selectedChunk.start_char }}</el-descriptions-item>
            <el-descriptions-item label="截止字符">{{ selectedChunk.end_char }}</el-descriptions-item>
            <el-descriptions-item label="知识类型" v-if="selectedChunk.metadata?.knowledge_type">
              <template v-if="Array.isArray(selectedChunk.metadata.knowledge_type)">
                <el-tag 
                  v-for="(type, index) in selectedChunk.metadata.knowledge_type" 
                  :key="index"
                  size="small" 
                  type="success"
                  class="mr-1"
                >
                  {{ type }}
                </el-tag>
              </template>
              <el-tag v-else size="small" type="success">{{ selectedChunk.metadata.knowledge_type }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="所在路径" :span="2" v-if="selectedChunk.metadata?.breadcrumb_path">
              {{ selectedChunk.metadata.breadcrumb_path }}
            </el-descriptions-item>
            <el-descriptions-item label="核心术语" :span="2" v-if="selectedChunk.metadata?.key_terms?.length">
              <el-tag v-for="term in selectedChunk.metadata.key_terms" :key="term" size="small" class="mr-1">
                {{ term }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="章节摘要" :span="2" v-if="selectedChunk.metadata?.section_summary">
              {{ selectedChunk.metadata.section_summary }}
            </el-descriptions-item>
          </el-descriptions>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Plus, Delete, ArrowRight, DataAnalysis, InfoFilled, Search } from '@element-plus/icons-vue'
import { documentApi } from '@/api/documents'
import { testsetApi } from '@/api/testsets'
import { formatFileSize, formatDateTime } from '@/utils/format'
import type { Document, TestSet } from '@/types'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const document = ref<any>(null)
const testsets = ref<TestSet[]>([])
const activeTab = ref('info')

// 切片相关
const chunks = ref<any[]>([])
const chunksLoading = ref(false)
const totalChunks = ref(0)
const currentPage = ref(1)
const pageSize = ref(10)
const chunkQuery = reactive({
  keyword: '',
  entity_type: ''
})

// 切片详情
const chunkDetailVisible = ref(false)
const selectedChunk = ref<any>(null)

const showChunkDetail = (row: any) => {
  selectedChunk.value = row
  chunkDetailVisible.value = true
}

const truncateText = (text: string, length: number) => {
  if (!text) return ''
  if (text.length <= length) return text
  return text.substring(0, length) + '...'
}

const METADATA_LABEL_MAP: Record<string, string> = {
  _chunking_short_merge_threshold: '短段落合并阈值',
  _chunking_max_chunk_chars: '切片最大字符数',
  doc_type: '文档类型',
  purpose_summary: '用途摘要',
  page_count: '页数',
  total_pages: '总页数',
  pages: '页数'
}

const getMetadataLabel = (key: string) => METADATA_LABEL_MAP[key] || key

const getPageCountDisplay = (doc: any) => {
  if (typeof doc?.page_count === 'number' && doc.page_count > 0) {
    return doc.page_count
  }
  const meta = (doc?.doc_metadata || {}) as Record<string, any>
  const fallback = meta.page_count ?? meta.total_pages ?? meta.pages
  if (typeof fallback === 'number' && fallback > 0) {
    return fallback
  }
  return '-'
}

// 任务相关
const analysisTask = ref<any>(null)
let timer: any = null

const fetchDocument = async () => {
  const id = route.params.id as string
  loading.value = true
  
  try {
    const res = await documentApi.getDocument(id)
    document.value = res
    
    // 如果文档未分析，则自动触发分析 (存量文档逻辑)
    if (!res.is_analyzed && res.status !== 'processing') {
      await startAnalysis()
    } else if (res.status === 'processing' && res.task_id) {
      startPolling(res.task_id)
    }
    
    await fetchTestsets()
  } catch (error) {
    ElMessage.error('获取文档详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const startPolling = (taskId: string) => {
  if (timer) clearInterval(timer)
  timer = setInterval(async () => {
    try {
      const task = await documentApi.getTaskStatus(taskId)
      analysisTask.value = task
      if (task.status === 'finished') {
        clearInterval(timer)
        ElMessage.success('分析完成')
        // 重新获取文档信息以刷新状态
        const res = await documentApi.getDocument(route.params.id as string)
        document.value = res
        if (activeTab.value === 'chunks') fetchChunks()
      } else if (task.status === 'failed') {
        clearInterval(timer)
        ElMessage.error(`分析失败: ${task.error || '未知错误'}`)
      }
    } catch (e) {
      console.error('Polling error:', e)
    }
  }, 2000)
}

const startAnalysis = async () => {
  if (!document.value) return
  try {
    const res = await documentApi.analyzeDocument(document.value.id)
    ElMessage.success('分析任务已启动')
    if (res.task_id) {
      startPolling(res.task_id)
    }
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '启动分析失败')
  }
}

const fetchChunks = async () => {
  if (!document.value || !document.value.is_analyzed) return
  chunksLoading.value = true
  try {
    const res = await documentApi.getDocumentChunks(document.value.id, {
      skip: (currentPage.value - 1) * pageSize.value,
      limit: pageSize.value,
      keyword: chunkQuery.keyword,
      entity_type: chunkQuery.entity_type
    })
    chunks.value = res.items
    totalChunks.value = res.total
  } catch (e) {
    ElMessage.error('获取切片失败')
  } finally {
    chunksLoading.value = false
  }
}

const getStatusType = (status: string) => {
  const types: Record<string, string> = {
    active: 'success',
    processing: 'warning',
    analyzed: 'success',
    failed: 'danger',
    inactive: 'info'
  }
  return types[status] || 'info'
}

const getStatusText = (status: string) => {
  const texts: Record<string, string> = {
    active: '活跃',
    processing: '分析中',
    analyzed: '已分析',
    failed: '分析失败',
    inactive: '停用'
  }
  return texts[status] || status
}

const fetchTestsets = async () => {
  if (!document.value) return
  
  try {
    const response = await testsetApi.getTestSets({
      document_id: document.value.id
    })
    testsets.value = response.items
  } catch (error) {
    console.error('Failed to fetch testsets:', error)
  }
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchChunks()
}

const handleDownload = async () => {
  if (!document.value) return
  
  try {
    const blob = await documentApi.downloadDocument(document.value.id)
    if (!blob || blob.size === 0) {
      ElMessage.error('下载失败：文件内容为空')
      return
    }
    const url = window.URL.createObjectURL(blob)
    const a = window.document.createElement('a')
    a.href = url
    a.download = document.value.filename
    window.document.body.appendChild(a)
    a.click()
    window.document.body.removeChild(a)
    // 延迟释放，避免浏览器尚未开始下载时 URL 被过早回收
    setTimeout(() => window.URL.revokeObjectURL(url), 1000)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '下载失败')
  }
}

const createTestset = () => {
  router.push(`/testsets?document_id=${document.value?.id}`)
}

const handleDelete = async () => {
  if (!document.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除文档 "${document.value.filename}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await documentApi.deleteDocument(document.value.id)
    ElMessage.success('删除成功')
    router.push('/documents')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

watch(activeTab, (val) => {
  if (val === 'chunks' && chunks.value.length === 0) {
    fetchChunks()
  }
})

onUnmounted(() => {
  if (timer) clearInterval(timer)
})

onMounted(async () => {
  await fetchDocument()
})
</script>

<style lang="scss" scoped>
.document-detail {
  .action-buttons {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
    
    .el-button {
      width: 100%;
      justify-content: flex-start;
      text-align: left;
    }

    .el-button + .el-button {
      margin-left: 0;
    }

    .el-button :deep(.el-icon) {
      width: 16px;
      min-width: 16px;
      margin-right: 8px;
      display: inline-flex;
      justify-content: center;
    }
  }
  
  .testset-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
    
    &:hover {
      background-color: #f5f7fa;
    }
  }
  
  .outline-content {
    max-height: 400px;
    overflow: auto;
    
    pre {
      margin: 0;
      font-size: 12px;
    }
  }

  .clickable-table {
    :deep(.el-table__row) {
      cursor: pointer;
      transition: background-color 0.2s;
      
      &:hover {
        background-color: #f5f7fa !important;
      }
    }
  }

  .chunk-content-preview {
    font-size: 14px;
    line-height: 1.6;
    color: #606266;
    max-height: 100px;
    overflow: hidden;
  }

  .full-content-box {
    background-color: #f8f9fa;
    padding: 16px;
    border-radius: 4px;
    border: 1px solid #e4e7ed;
    max-height: 400px;
    overflow-y: auto;
    
    pre {
      margin: 0;
      white-space: pre-wrap;
      word-wrap: break-word;
      font-family: inherit;
      font-size: 14px;
      line-height: 1.8;
    }
  }

  .detail-section {
    h4 {
      margin-top: 0;
      margin-bottom: 12px;
      color: #303133;
      border-left: 4px solid #409eff;
      padding-left: 8px;
    }
  }
}
</style>
