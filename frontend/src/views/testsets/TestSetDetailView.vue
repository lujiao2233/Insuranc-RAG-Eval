<template>
  <div class="page testset-detail-page" v-loading="loading">
    <el-page-header @back="$router.back()" class="section">
      <template #content>
        <span class="page-title">{{ testset?.name }}</span>
      </template>
    </el-page-header>
    
    <template v-if="testset">
      <el-row :gutter="24" class="section">
        <el-col :span="18">
          <el-card shadow="never">
            <template #header>
              <div class="card-header">
                <span class="card-title">问题列表</span>
                <div>
                  <el-button type="primary" @click="showAddDialog = true">
                    <el-icon><Plus /></el-icon>
                    添加问题
                  </el-button>
                  <el-dropdown split-button type="success" @click="generateQuestions" v-if="questions.length === 0">
                    <el-icon><MagicStick /></el-icon>
                    自动生成
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item @click="generateQuestionsWithParams(5)">生成5个问题</el-dropdown-item>
                        <el-dropdown-item @click="generateQuestionsWithParams(10)">生成10个问题</el-dropdown-item>
                        <el-dropdown-item @click="generateQuestionsWithParams(20)">生成20个问题</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </template>
            
            <!-- 问题筛选 -->
            <div class="filter-bar section-sm">
              <el-select 
                v-model="questionTypeFilter" 
                placeholder="问题类型" 
                clearable
                style="width: 150px;"
                @change="filterQuestions"
              >
                <el-option
                  v-for="minor in questionTypeOptions"
                  :key="minor"
                  :label="minor"
                  :value="minor"
                />
              </el-select>
              
              <el-select 
                v-model="categoryMajorFilter" 
                placeholder="主要分类" 
                clearable
                style="width: 150px;"
                @change="filterQuestions"
              >
                <el-option label="基础理解类" value="基础理解类" />
                <el-option label="推理与综合类" value="推理与综合类" />
                <el-option label="数值与计算类" value="数值与计算类" />
                <el-option label="鲁棒性/输入质量类" value="鲁棒性/输入质量类" />
                <el-option label="合规与安全类" value="合规与安全类" />
                <el-option label="多文档关联类" value="多文档关联类" />
              </el-select>
              
              <el-input
                v-model="questionSearch"
                placeholder="搜索问题"
                style="width: 200px;"
                @input="filterQuestions"
                clearable
              />
            </div>
            
            <el-table 
              :data="paginatedQuestions" 
              style="width: 100%"
              size="small"
              :default-sort="{ prop: 'question_type', order: 'ascending' }"
            >
              <el-table-column prop="question" label="问题" min-width="250">
                <template #default="{ row }">
                  <el-text truncated>{{ row.question }}</el-text>
                </template>
              </el-table-column>
              <el-table-column prop="category_major" label="主要分类" width="120">
                <template #default="{ row }">
                  <el-tag size="small" type="info" v-if="row.category_major">{{ row.category_major }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column prop="category_minor" label="次要分类" width="120">
                <template #default="{ row }">
                  <el-tag size="small" type="warning" v-if="row.category_minor">{{ row.category_minor }}</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column v-if="showModelAnswerColumn" prop="answer" label="模型答案" min-width="200">
                <template #default="{ row }">
                  <el-text truncated>{{ row.answer || '-' }}</el-text>
                </template>
              </el-table-column>
              <el-table-column prop="expected_answer" label="期望答案" min-width="200">
                <template #default="{ row }">
                  <el-text truncated>{{ row.expected_answer || '-' }}</el-text>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" fixed="right">
                <template #default="{ row }">
                  <div class="button-row">
                    <el-button link type="primary" size="small" @click="editQuestion(row)">
                      编辑
                    </el-button>
                    <el-button link type="danger" size="small" @click="deleteQuestion(row)">
                      删除
                    </el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container section-sm">
              <el-pagination
                v-model:current-page="currentPage"
                v-model:page-size="pageSize"
                :page-sizes="[10, 20, 50, 100]"
                :total="filteredQuestions.length"
                layout="total, sizes, prev, pager, next, jumper"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              />
            </div>
          </el-card>
        </el-col>
        
        <el-col :span="6">
          <el-card shadow="never" class="section">
            <template #header>
              <span class="card-title">操作</span>
            </template>
            
            <div class="action-buttons">
              <el-button type="primary" @click="startExecution">
                <el-icon><DataLine /></el-icon>
                执行测试
              </el-button>
              <el-button @click="exportTestset">
                <el-icon><Download /></el-icon>
                导出测试集
              </el-button>
              <el-button @click="showGenerateConfig = true">
                <el-icon><Setting /></el-icon>
                重新生成
              </el-button>
              <el-button type="danger" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                删除测试集
              </el-button>
            </div>
          </el-card>
          
          <el-card shadow="never" class="related-docs-card section">
            <template #header>
              <span class="card-title">关联文档</span>
            </template>
            
            <div class="document-list" v-if="relatedDocuments.length > 0">
              <div class="document-item" v-for="doc in relatedDocuments" :key="doc.id">
                <el-icon><Document /></el-icon>
                <span class="doc-name">{{ doc.filename }}</span>
              </div>
            </div>
            <div v-else class="no-document">
              <el-empty description="暂无关联文档" :image-size="60" />
            </div>
          </el-card>
        </el-col>
      </el-row>
    </template>
    
    <!-- 添加/编辑问题对话框 -->
    <el-dialog
      v-model="showAddDialog"
      :title="editingQuestion ? '编辑问题' : '添加问题'"
      width="700px"
    >
      <el-form
        ref="questionFormRef"
        :model="questionForm"
        :rules="questionRules"
        label-width="100px"
      >
        <el-form-item label="问题" prop="question">
          <el-input
            v-model="questionForm.question"
            type="textarea"
            :rows="3"
            placeholder="请输入问题"
          />
        </el-form-item>
        
        <el-form-item label="问题类型" prop="question_type">
          <el-select v-model="questionForm.question_type" style="width: 100%">
            <el-option
              v-for="minor in questionTypeOptions"
              :key="minor"
              :label="minor"
              :value="minor"
            />
          </el-select>
        </el-form-item>
        
        <el-form-item label="主要分类">
          <el-select v-model="questionForm.category_major" style="width: 100%" clearable>
            <el-option label="基础理解类" value="基础理解类" />
            <el-option label="推理与综合类" value="推理与综合类" />
            <el-option label="数值与计算类" value="数值与计算类" />
            <el-option label="鲁棒性/输入质量类" value="鲁棒性/输入质量类" />
            <el-option label="合规与安全类" value="合规与安全类" />
            <el-option label="多文档关联类" value="多文档关联类" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="次要分类">
          <el-select v-model="questionForm.category_minor" style="width: 100%" clearable>
            <el-option-group v-for="category in categoryGroups" :key="category.major" :label="category.major">
              <el-option 
                v-for="minor in category.minors" 
                :key="minor" 
                :label="minor" 
                :value="minor" 
              />
            </el-option-group>
          </el-select>
        </el-form-item>
        
        <el-form-item label="期望答案">
          <el-input
            v-model="questionForm.expected_answer"
            type="textarea"
            :rows="3"
            placeholder="请输入期望答案（可选）"
          />
        </el-form-item>
        
        <el-form-item label="上下文">
          <el-input
            v-model="questionForm.context"
            type="textarea"
            :rows="2"
            placeholder="请输入上下文（可选）"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveQuestion">
          保存
        </el-button>
      </template>
    </el-dialog>
    
    <!-- 重新生成配置对话框 -->
    <el-dialog
      v-model="showGenerateConfig"
      title="重新生成配置"
      width="500px"
    >
      <el-form
        ref="generateFormRef"
        :model="generateForm"
        label-width="120px"
      >
        <el-form-item label="生成问题数">
          <el-slider
            v-model="generateForm.num_questions"
            :min="1"
            :max="50"
            show-input
          />
        </el-form-item>
        
        <el-form-item label="问题类型">
          <el-checkbox-group v-model="generateForm.question_types">
            <el-checkbox v-for="minor in questionTypeOptions" :key="minor" :label="minor">
              {{ minor }}
            </el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      
      <template #footer>
        <el-button @click="showGenerateConfig = false">取消</el-button>
        <el-button type="primary" :loading="generating" @click="confirmGenerateQuestions">
          确认生成
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Plus, MagicStick, DataLine, Download, Delete, Setting, Document } from '@element-plus/icons-vue'
import { testsetApi } from '@/api/testsets'
import { documentApi } from '@/api/documents'
import { formatDateTime } from '@/utils/format'
import type { TestSet, Question, Document as DocumentType } from '@/types'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const testset = ref<TestSet | null>(null)
const questions = ref<Question[]>([])
const relatedDocuments = ref<DocumentType[]>([])
const filteredQuestions = ref<Question[]>([])
const currentPage = ref(1)
const pageSize = ref(10)

// 筛选相关
const questionTypeFilter = ref('')
const categoryMajorFilter = ref('')
const questionSearch = ref('')

// 添加/编辑问题相关
const showAddDialog = ref(false)
const saving = ref(false)
const editingQuestion = ref<Question | null>(null)
const questionFormRef = ref<FormInstance>()

// 重新生成配置相关
const showGenerateConfig = ref(false)
const generating = ref(false)
const generateFormRef = ref<FormInstance>()

const questionForm = reactive({
  question: '',
  question_type: '事实召回',
  category_major: '',
  category_minor: '',
  expected_answer: '',
  context: ''
})

const generateForm = reactive({
  num_questions: 10,
  question_types: ['事实召回', '条件推理']
})

const questionRules: FormRules = {
  question: [{ required: true, message: '请输入问题', trigger: 'blur' }],
  question_type: [{ required: true, message: '请选择问题类型', trigger: 'change' }]
}

// 问题分类配置
const categoryGroups = [
  {
    major: '基础理解类',
    minors: ['定义解释', '术语对齐', '事实召回', '表格/字段理解', '流程识别']
  },
  {
    major: '推理与综合类',
    minors: ['因果推理', '条件推理', '例外与边界判断', '假设推理', '归纳总结']
  },
  {
    major: '数值与计算类',
    minors: ['数值提取', '单位换算', '比例与增长率计算', '日期时间计算', '区间与阈值判断']
  },
  {
    major: '鲁棒性/输入质量类',
    minors: ['错别字与拼写噪声', '意图模糊澄清', '指代消解', '多意图拆解与补问']
  },
  {
    major: '合规与安全类',
    minors: ['内容安全', '隐私与数据合规', '系统安全']
  },
  {
    major: '多文档关联类',
    minors: ['跨文档对比分析', '跨文档信息整合', '跨文档流程串联', '跨文档逻辑推理', '跨文档冲突消解', '跨文档证据归因', '跨文档规则一致性']
  }
]

const questionTypeOptions = computed(() => {
  return categoryGroups.flatMap(category => category.minors)
})

const getQuestionTypeText = (type: string) => {
  return type || '-'
}

const fetchTestset = async () => {
  const id = route.params.id as string
  loading.value = true
  
  try {
    testset.value = await testsetApi.getTestSet(id)
    await fetchQuestions()
    await fetchRelatedDocuments()
    filterQuestions()
  } catch (error) {
    ElMessage.error('获取测试集详情失败')
    router.back()
  } finally {
    loading.value = false
  }
}

const fetchRelatedDocuments = async () => {
  if (!testset.value) {
    relatedDocuments.value = []
    return
  }
  
  try {
    const metadataDocIds = Array.isArray(testset.value.metadata?.document_ids)
      ? testset.value.metadata.document_ids.map((id: string) => String(id).trim()).filter(Boolean)
      : []
    const fallbackDocIds = (testset.value.document_id || '')
      .split(',')
      .map(id => id.trim())
      .filter(Boolean)
    const questionDocIds = questions.value
      .map((q: any) => {
        const meta = (q?.metadata || {}) as Record<string, any>
        return String(meta.doc_id || meta.document_id || meta.source_doc_id || '').trim()
      })
      .filter(Boolean)

    const docIds = Array.from(new Set([...metadataDocIds, ...fallbackDocIds, ...questionDocIds]))

    if (docIds.length === 0) {
      relatedDocuments.value = []
      return
    }

    const docs = await Promise.allSettled(docIds.map(id => documentApi.getDocument(id)))
    relatedDocuments.value = docs
      .filter((item): item is PromiseFulfilledResult<any> => item.status === 'fulfilled')
      .map(item => item.value)
  } catch (error) {
    console.error('Failed to fetch related documents:', error)
    relatedDocuments.value = []
  }
}

const fetchQuestions = async () => {
  if (!testset.value) return
  
  try {
    const response = await testsetApi.getQuestions(testset.value.id)
    questions.value = response.items
    filterQuestions() // 获取后重新过滤
  } catch (error) {
    console.error('Failed to fetch questions:', error)
  }
}

const filterQuestions = () => {
  let result = [...questions.value]
  
  // 按问题类型过滤
  if (questionTypeFilter.value) {
    result = result.filter(q => q.question_type === questionTypeFilter.value)
  }
  
  // 按主要分类过滤
  if (categoryMajorFilter.value) {
    result = result.filter(q => q.category_major === categoryMajorFilter.value)
  }
  
  // 按问题内容搜索
  if (questionSearch.value) {
    const searchLower = questionSearch.value.toLowerCase()
    result = result.filter(q => 
      q.question.toLowerCase().includes(searchLower) ||
      (q.expected_answer && q.expected_answer.toLowerCase().includes(searchLower))
    )
  }
  
  filteredQuestions.value = result
  currentPage.value = 1 // 重置到第一页
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

// 分页后的数据
const paginatedQuestions = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredQuestions.value.slice(start, end)
})

const showModelAnswerColumn = computed(() => {
  return questions.value.some(q => !!(q.answer && String(q.answer).trim()))
})

const editQuestion = (question: Question) => {
  editingQuestion.value = question
  questionForm.question = question.question
  questionForm.question_type = question.question_type || '事实召回'
  questionForm.category_major = question.category_major || ''
  questionForm.category_minor = question.category_minor || ''
  questionForm.expected_answer = question.expected_answer || ''
  questionForm.context = question.context || ''
  showAddDialog.value = true
}

const deleteQuestion = async (question: Question) => {
  if (!testset.value) return
  
  try {
    await ElMessageBox.confirm('确定要删除此问题吗？', '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await testsetApi.deleteQuestion(testset.value.id, question.id)
    ElMessage.success('删除成功')
    fetchQuestions()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const saveQuestion = async () => {
  if (!questionFormRef.value || !testset.value) return
  
  await questionFormRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      if (editingQuestion.value) {
        await testsetApi.updateQuestion(testset.value!.id, editingQuestion.value.id, {
          question: questionForm.question,
          question_type: questionForm.question_type,
          category_major: questionForm.category_major || undefined,
          category_minor: questionForm.category_minor || undefined,
          expected_answer: questionForm.expected_answer || undefined,
          context: questionForm.context || undefined
        })
      } else {
        await testsetApi.addQuestion(testset.value!.id, {
          question: questionForm.question,
          question_type: questionForm.question_type,
          category_major: questionForm.category_major || undefined,
          category_minor: questionForm.category_minor || undefined,
          expected_answer: questionForm.expected_answer || undefined,
          context: questionForm.context || undefined
        })
      }
      
      ElMessage.success('保存成功')
      showAddDialog.value = false
      editingQuestion.value = null
      resetQuestionForm()
      fetchQuestions()
    } catch (error) {
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const resetQuestionForm = () => {
  questionForm.question = ''
  questionForm.question_type = '事实召回'
  questionForm.category_major = ''
  questionForm.category_minor = ''
  questionForm.expected_answer = ''
  questionForm.context = ''
}

const sleep = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

const waitGenerationTaskFinished = async (taskId: string) => {
  const maxAttempts = 300
  for (let i = 0; i < maxAttempts; i++) {
    const task = await testsetApi.getTaskStatus(taskId)
    if (task.status === 'finished') {
      return task
    }
    if (task.status === 'cancelled') {
      throw new Error(task.error || task.message || '任务已取消')
    }
    if (task.status === 'failed') {
      throw new Error(task.error || task.message || '任务执行失败')
    }
    await sleep(2000)
  }
  throw new Error('任务执行超时，请稍后在任务中心查看结果')
}

const startGenerateByTask = async (
  loadingText: string,
  params: {
    num_questions?: number
    question_types?: string | string[]
    generation_mode?: 'advanced'
    enable_safety_robustness?: boolean
    multi_doc_ratio?: number
  }
) => {
  if (!testset.value) return
  const loadingInstance = ElLoading.service({
    lock: true,
    text: loadingText,
    background: 'rgba(255, 255, 255, 0.7)'
  })

  try {
    const { task_id, message } = await testsetApi.generateQuestions(testset.value.id, params)
    ElMessage.info(message || '生成任务已创建，正在处理中...')
    await waitGenerationTaskFinished(task_id)
    await fetchQuestions()
    ElMessage.success('问题生成完成')
  } finally {
    loadingInstance.close()
  }
}

const generateQuestions = async () => {
  if (!testset.value) return
  
  try {
    await startGenerateByTask('正在生成问题...', {
      num_questions: 10,
      question_types: ['事实召回', '条件推理']
    })
  } catch (error: any) {
    ElMessage.error(error?.message || '生成问题失败')
  }
}

const generateQuestionsWithParams = async (num: number) => {
  if (!testset.value) return
  
  try {
    await startGenerateByTask(`正在生成${num}个问题...`, {
      num_questions: num,
      question_types: ['事实召回', '条件推理', '定义解释']
    })
  } catch (error: any) {
    ElMessage.error(error?.message || '生成问题失败')
  }
}

const confirmGenerateQuestions = async () => {
  if (!testset.value || !generateFormRef.value) return
  
  try {
    await startGenerateByTask('正在生成问题...', {
      num_questions: generateForm.num_questions,
      question_types: generateForm.question_types.join(',')
    })
    showGenerateConfig.value = false
  } catch (error: any) {
    ElMessage.error(error?.message || '生成问题失败')
  }
}

const startExecution = () => {
  if (!testset.value?.id) return
  router.push(`/testsets/${testset.value.id}/execute`)
}

const exportTestset = async () => {
  if (!testset.value) return
  
  try {
    const blob = await testsetApi.exportTestSet(testset.value.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${testset.value.name}.csv`
    a.click()
    window.URL.revokeObjectURL(url)
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const handleDelete = async () => {
  if (!testset.value) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除测试集 "${testset.value.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await testsetApi.deleteTestSet(testset.value.id)
    ElMessage.success('删除成功')
    router.push('/testsets')
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchTestset()
})
</script>

<style lang="scss" scoped>
.testset-detail-page {
  .page-title {
    font-size: var(--font-20, 20px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .card-title {
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
    gap: 10px;
    align-items: center;
  }
  
  .button-row {
    display: flex;
    gap: 8px;
    align-items: center;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 12px;

    .el-button {
      width: 100%;
      justify-content: flex-start;
      text-align: left;
      margin-left: 0;
    }
  }
  
  .document-list {
    .document-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 0;
      border-bottom: 1px solid var(--border-1, #ebeef5);
      color: var(--text-1, #303133);

      &:last-child {
        border-bottom: none;
      }

      .el-icon {
        color: var(--brand-1, #2563eb);
        font-size: 16px;
      }

      .doc-name {
        flex: 1;
        white-space: normal;
        word-break: break-all;
        overflow-wrap: anywhere;
        line-height: 1.4;
        font-size: var(--font-14, 14px);
      }
    }
  }

  .no-document {
    padding: 20px 0;
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

:deep(.el-card) {
  border-radius: var(--radius-8, 8px);
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
