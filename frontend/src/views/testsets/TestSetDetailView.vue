<template>
  <div class="testset-detail" v-loading="loading">
    <el-page-header @back="$router.back()">
      <template #content>
        <span class="text-large font-600 mr-3">{{ testset?.name }}</span>
      </template>
    </el-page-header>
    
    <el-divider />
    
    <template v-if="testset">
      <el-row :gutter="20">
        <el-col :span="18">
          <el-card>
            <template #header>
              <div class="card-header">
                <span>问题列表</span>
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
            <div class="filter-bar mb-3">
              <el-select 
                v-model="questionTypeFilter" 
                placeholder="问题类型" 
                clearable
                style="width: 150px; margin-right: 10px;"
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
                style="width: 150px; margin-right: 10px;"
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
                style="width: 200px; margin-right: 10px;"
                @input="filterQuestions"
                clearable
              />
            </div>
            
            <el-table 
              :data="filteredQuestions" 
              style="width: 100%"
              :default-sort="{ prop: 'question_type', order: 'ascending' }"
            >
              <el-table-column prop="question" label="问题" min-width="250">
                <template #default="{ row }">
                  <el-text truncated>{{ row.question }}</el-text>
                </template>
              </el-table-column>
              <el-table-column prop="question_type" label="类型" width="100">
                <template #default="{ row }">
                  <el-tag size="small">{{ getQuestionTypeText(row.question_type) }}</el-tag>
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
              <el-table-column prop="expected_answer" label="期望答案" min-width="200">
                <template #default="{ row }">
                  <el-text truncated>{{ row.expected_answer || '-' }}</el-text>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="150" fixed="right">
                <template #default="{ row }">
                  <el-button type="primary" text @click="editQuestion(row)">
                    编辑
                  </el-button>
                  <el-button type="danger" text @click="deleteQuestion(row)">
                    删除
                  </el-button>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container mt-4">
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
          <el-card>
            <template #header>
              <span>测试集信息</span>
            </template>
            
            <el-descriptions :column="1" border>
              <el-descriptions-item label="名称">{{ testset.name }}</el-descriptions-item>
              <el-descriptions-item label="描述">{{ testset.description || '-' }}</el-descriptions-item>
              <el-descriptions-item label="问题数">{{ testset.question_count }}</el-descriptions-item>
              <el-descriptions-item label="生成方式">{{ testset.generation_method }}</el-descriptions-item>
              <el-descriptions-item label="创建时间">{{ formatDateTime(testset.create_time) }}</el-descriptions-item>
            </el-descriptions>
          </el-card>
          
          <el-card class="mt-4">
            <template #header>
              <span>操作</span>
            </template>
            
            <div class="action-buttons">
              <el-button type="primary" @click="startEvaluation">
                <el-icon><DataLine /></el-icon>
                开始评估
              </el-button>
              <el-button type="success" @click="exportTestset">
                <el-icon><Download /></el-icon>
                导出测试集
              </el-button>
              <el-button type="warning" @click="showGenerateConfig = true">
                <el-icon><Setting /></el-icon>
                重新生成
              </el-button>
              <el-button type="danger" @click="handleDelete">
                <el-icon><Delete /></el-icon>
                删除测试集
              </el-button>
            </div>
          </el-card>
          
          <el-card class="mt-4">
            <template #header>
              <span>问题统计</span>
            </template>
            
            <div class="stats-container">
              <div class="stat-item">
                <span class="stat-label">总问题数:</span>
                <span class="stat-value">{{ questions.length }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">已分类:</span>
                <span class="stat-value">{{ stats.categorized }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">未分类:</span>
                <span class="stat-value">{{ stats.uncategorized }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">分类完整率:</span>
                <span class="stat-value">{{ stats.total ? Math.round((stats.categorized / stats.total) * 100) : 0 }}%</span>
              </div>
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
import { Plus, MagicStick, DataLine, Download, Delete, Setting } from '@element-plus/icons-vue'
import { testsetApi } from '@/api/testsets'
import { formatDateTime } from '@/utils/format'
import type { TestSet, Question } from '@/types'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const testset = ref<TestSet | null>(null)
const questions = ref<Question[]>([])
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

// 计算属性
const stats = computed(() => {
  const result = {
    total: questions.value.length,
    categorized: 0,
    uncategorized: 0
  }
  questions.value.forEach(q => {
    if (q.category_major && q.category_minor) result.categorized++
    else result.uncategorized++
  })
  return result
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
    filterQuestions() // 初始化过滤
  } catch (error) {
    ElMessage.error('获取测试集详情失败')
    router.back()
  } finally {
    loading.value = false
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

// 为了保持模板中的数据源一致，我们更新filteredQuestions为分页后的数据
watch(paginatedQuestions, (newVal) => {
  // 这里我们不直接赋值，而是保持filteredQuestions为完整过滤结果
  // 在模板中直接使用paginatedQuestions
}, { immediate: true })

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

const generateQuestions = async () => {
  if (!testset.value) return
  
  try {
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在生成问题...',
      background: 'rgba(255, 255, 255, 0.7)'
    })
    
    const result = await testsetApi.generateQuestions(testset.value.id, {
      num_questions: 10,
      question_types: ['事实召回', '条件推理']
    })
    
    loadingInstance.close()
    ElMessage.success(result.message)
    fetchQuestions()
  } catch (error) {
    ElMessage.error('生成问题失败')
  }
}

const generateQuestionsWithParams = async (num: number) => {
  if (!testset.value) return
  
  try {
    const loadingInstance = ElLoading.service({
      lock: true,
      text: `正在生成${num}个问题...`,
      background: 'rgba(255, 255, 255, 0.7)'
    })
    
    const result = await testsetApi.generateQuestions(testset.value.id, {
      num_questions: num,
      question_types: ['事实召回', '条件推理', '定义解释']
    })
    
    loadingInstance.close()
    ElMessage.success(result.message)
    fetchQuestions()
  } catch (error) {
    ElMessage.error('生成问题失败')
  }
}

const confirmGenerateQuestions = async () => {
  if (!testset.value || !generateFormRef.value) return
  
  try {
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在生成问题...',
      background: 'rgba(255, 255, 255, 0.7)'
    })
    
    const result = await testsetApi.generateQuestions(testset.value.id, {
      num_questions: generateForm.num_questions,
      question_types: generateForm.question_types.join(',')
    })
    
    loadingInstance.close()
    ElMessage.success(result.message)
    showGenerateConfig.value = false
    fetchQuestions()
  } catch (error) {
    ElMessage.error('生成问题失败')
  }
}

const startEvaluation = () => {
  router.push(`/evaluations?testset_id=${testset.value?.id}`)
}

const exportTestset = async () => {
  if (!testset.value) return
  
  try {
    const blob = await testsetApi.exportTestSet(testset.value.id)
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${testset.value.name}.json`
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
.testset-detail {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .filter-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
  }
  
  .action-buttons {
    display: flex;
    flex-direction: column;
    gap: 12px;
    
    .el-button {
      width: 100%;
      justify-content: flex-start;
    }
  }
  
  .stats-container {
    .stat-item {
      display: flex;
      justify-content: space-between;
      margin-bottom: 8px;
      
      .stat-label {
        color: #606266;
      }
      
      .stat-value {
        font-weight: bold;
        color: #303133;
      }
    }
  }
  
  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 16px;
  }
  
  .mb-3 {
    margin-bottom: 1rem;
  }
  
  .mt-3 {
    margin-top: 1rem;
  }
  
  .mt-4 {
    margin-top: 1.5rem;
  }
}
</style>
