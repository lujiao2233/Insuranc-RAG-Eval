<template>
  <div class="testsets-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>测试集管理</span>
          <el-button type="primary" @click="showGenerationDialog = true">
            <el-icon><Plus /></el-icon>
            新建测试集
          </el-button>
        </div>
      </template>
      
      <!-- 筛选栏 -->
      <div class="filter-bar mb-4">
        <el-input
          v-model="searchQuery"
          placeholder="搜索测试集名称或描述"
          style="width: 300px; margin-right: 10px;"
          clearable
          @input="filterTestsets"
        />
        
        <el-select 
          v-model="documentFilter" 
          placeholder="关联文档" 
          clearable
          style="width: 200px; margin-right: 10px;"
          @change="filterTestsets"
        >
          <el-option
            v-for="doc in documents"
            :key="doc.id"
            :label="doc.filename"
            :value="doc.id"
          />
        </el-select>
        
        <el-select 
          v-model="methodFilter" 
          placeholder="生成方式" 
          clearable
          style="width: 150px; margin-right: 10px;"
          @change="filterTestsets"
        >
          <el-option label="自动生成" value="auto" />
          <el-option label="手动创建" value="manual" />
        </el-select>
      </div>
      
      <el-table
        v-loading="loading"
        :data="paginatedTestsets"
        style="width: 100%"
      >
        <el-table-column prop="name" label="名称" min-width="200">
          <template #default="{ row }">
            <el-link type="primary" @click="viewTestset(row.id)">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">
            <el-text truncated>{{ row.description || '-' }}</el-text>
          </template>
        </el-table-column>
        <el-table-column prop="question_count" label="问题数" width="100">
          <template #default="{ row }">
            <el-tag :type="getQuestionCountType(row.question_count)">
              {{ row.question_count }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="generation_method" label="生成方式" width="120">
          <template #default="{ row }">
            <el-tag :type="getMethodType(row.generation_method)">
              {{ getMethodText(row.generation_method) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="create_time" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatDateTime(row.create_time) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="170" fixed="right">
          <template #default="{ row }">
            <div class="button-row">
              <el-button type="primary" size="small" class="fixed-width-btn" @click="viewTestset(row.id)">
                查看
              </el-button>
              <el-button type="success" size="small" class="fixed-width-btn" @click="startEvaluation(row)">
                评估
              </el-button>
            </div>
            <div class="button-row">
              <el-button type="warning" size="small" class="fixed-width-btn" @click="handleExportCSV(row)">
                导出
              </el-button>
              <el-button type="danger" size="small" class="fixed-width-btn" @click="handleDelete(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container mt-4">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredTestsets.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </el-card>
    
    <!-- 新建测试集/生成配置对话框 -->
    <el-dialog
      v-model="showGenerationDialog"
      title="新建测试集"
      width="800px"
      :close-on-click-modal="!generating"
      :show-close="!generating"
    >
      <div v-if="!generating && !generationComplete" class="generation-config">
        <el-form
          ref="formRef"
          :model="generationForm"
          label-width="150px"
        >
          <!-- 文档选择 -->
          <el-form-item label="选择文档" prop="documentIds" required>
            <el-select
              v-model="generationForm.documentIds"
              multiple
              placeholder="请选择要生成测试集的文档（支持多选）"
              style="width: 100%"
              filterable
            >
              <el-option
                v-for="doc in analyzedDocuments"
                :key="doc.id"
                :label="`${doc.filename} ${doc.is_analyzed ? '✓' : '(未分析)'}`"
                :value="doc.id"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="按分类选择">
            <el-space wrap style="width: 100%">
              <el-select
                v-model="selectedCategory"
                placeholder="选择文档分类"
                clearable
                style="width: 260px"
              >
                <el-option
                  v-for="category in documentCategories"
                  :key="category"
                  :label="`${category}（${categoryDocCountMap[category] || 0}）`"
                  :value="category"
                />
              </el-select>
              <el-button @click="selectDocumentsByCategory(false)">追加该分类</el-button>
              <el-button type="primary" plain @click="selectDocumentsByCategory(true)">仅选该分类</el-button>
              <el-button text @click="clearSelectedDocuments">清空已选文档</el-button>
            </el-space>
          </el-form-item>
          
          <el-divider content-position="left">生成参数</el-divider>
          
          <!-- 每个文档问题数 -->
          <el-form-item label="每个文档问题数">
            <el-input-number
              v-model="generationForm.questionsPerDoc"
              :min="1"
              :max="50"
              style="width: 100%"
            />
          </el-form-item>
          
          <!-- 安全与鲁棒性 -->
          <el-form-item label="安全与鲁棒性">
            <el-switch
              v-model="generationForm.enableSafetyRobustness"
              active-text="启用"
              inactive-text="禁用"
            />
            <div class="form-help">启用后将生成安全合规与输入质量类问题</div>
          </el-form-item>
          
          <!-- 人物画像配置 -->
          <el-form-item label="人物画像配置">
            <el-switch
              v-model="generationForm.enablePersona"
              active-text="启用"
              inactive-text="禁用"
            />
            <div class="form-help">启用后将根据人物画像生成更贴合角色的问题</div>
          </el-form-item>
          
          <!-- 人物画像JSON -->
          <el-form-item v-if="generationForm.enablePersona" label="人物画像JSON">
            <el-input
              v-model="generationForm.personaJson"
              type="textarea"
              :rows="5"
              placeholder="请输入人物画像JSON配置，格式示例：
[
  {&quot;name&quot;: &quot;新手客户&quot;, &quot;description&quot;: &quot;刚接触保险产品，对基本概念不了解的新用户&quot;},
  {&quot;name&quot;: &quot;资深代理人&quot;, &quot;description&quot;: &quot;有多年代理经验，熟悉各类保险产品和条款&quot;}
]"
            />
            <div class="form-help">定义用户角色，帮助生成更真实的问题</div>
          </el-form-item>
          
          <el-divider content-position="left">问题分类体系</el-divider>
          
          <!-- 分类体系展示 -->
          <div class="taxonomy-preview">
            <el-collapse>
              <el-collapse-item
                v-for="(category, index) in taxonomy"
                :key="index"
                :title="category.major"
              >
                <template #title>
                  <span class="taxonomy-major">{{ category.major }}</span>
                  <el-tag size="small" type="info" class="ml-10">{{ category.minors.length }}个子类</el-tag>
                </template>
                <div class="minor-list">
                  <el-tag
                    v-for="(minor, mi) in category.minors"
                    :key="mi"
                    size="small"
                    class="minor-tag"
                  >
                    {{ minor }}
                  </el-tag>
                </div>
              </el-collapse-item>
            </el-collapse>
          </div>
        </el-form>
      </div>
      
      <!-- 生成进度显示 -->
      <div v-if="generating || generationComplete" class="generation-progress">
        <!-- 进度条 -->
        <div class="progress-section">
          <el-progress
            :percentage="progressPercentage"
            :status="progressStatus"
            :stroke-width="20"
          />
          <div class="progress-info">
            <span>当前阶段: {{ progressInfo.stage }}</span>
            <span>{{ progressInfo.current }}/{{ progressInfo.total }}</span>
          </div>
          <div v-if="progressInfo.logs.length > 0" class="progress-logs">
            <div
              v-for="(log, idx) in progressInfo.logs.slice(-8)"
              :key="idx"
              class="log-item"
            >
              {{ log }}
            </div>
          </div>
        </div>
        
        <!-- 生成结果统计 -->
        <div v-if="generationComplete" class="result-stats">
          <el-row :gutter="10">
            <el-col :span="8">
              <el-statistic title="总问题数" :value="generatedQuestions.length" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="来源文档数" :value="generationForm.documentIds.length" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="状态" :value="generatedQuestions.length > 0 ? '已完成' : '生成失败'" />
            </el-col>
          </el-row>
        </div>
        
        <!-- 生成结果表格 -->
        <div v-if="generationComplete && generatedQuestions.length > 0" class="result-table">
          <el-divider content-position="left">生成结果预览</el-divider>
          <el-table
            :data="generatedQuestions.slice(0, 10)"
            style="width: 100%"
            max-height="300"
            stripe
          >
            <el-table-column type="index" width="50" />
            <el-table-column prop="question" label="问题" min-width="200" show-overflow-tooltip />
            <el-table-column prop="question_type" label="类型" width="120">
              <template #default="{ row }">
                <el-tag size="small">{{ row.question_type || '未分类' }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category_major" label="大类" width="120">
              <template #default="{ row }">
                <el-tag size="small" type="info">{{ row.category_major || '-' }}</el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div v-if="generatedQuestions.length > 10" class="more-hint">
            还有 {{ generatedQuestions.length - 10 }} 个问题...
          </div>
        </div>
      </div>
      
      <template #footer>
        <div v-if="!generating && !generationComplete && !generationFailed">
          <el-button @click="showGenerationDialog = false">取消</el-button>
          <el-button type="primary" @click="startGeneration">
            开始生成
          </el-button>
        </div>
        <div v-if="generating">
          <span>正在生成中，请稍候...</span>
        </div>
        <div v-if="generationComplete && !generationFailed">
          <el-button @click="resetGeneration">新建另一个</el-button>
          <el-button type="primary" @click="viewCreatedTestset">查看测试集</el-button>
        </div>
        <div v-if="generationFailed">
          <el-button type="primary" @click="resetGeneration">关闭</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElLoading } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { testsetApi } from '@/api/testsets'
import { documentApi } from '@/api/documents'
import { formatDateTime } from '@/utils/format'
import type { TestSet, Document } from '@/types'
import type { FormInstance } from 'element-plus'

const router = useRouter()

const loading = ref(false)
const testsets = ref<TestSet[]>([])
const documents = ref<Document[]>([])
const filteredTestsets = ref<TestSet[]>([])
const currentPage = ref(1)
const pageSize = ref(10)

// 筛选相关
const searchQuery = ref('')
const documentFilter = ref('')
const methodFilter = ref('')

// 生成配置相关
const showGenerationDialog = ref(false)
const generating = ref(false)
const generationComplete = ref(false)
const generationFailed = ref(false)
const formRef = ref<FormInstance>()
const createdTestsetId = ref<string | null>(null)

// 分类体系
const taxonomy = ref<Array<{major: string, minors: string[]}>>([])

// 进度相关
const progressInfo = reactive({
  stage: '准备中',
  current: 0,
  total: 0,
  logs: [] as string[]
})

// 生成的问题
const generatedQuestions = ref<any[]>([])

// 生成表单
const generationForm = reactive({
  documentIds: [] as string[],
  questionsPerDoc: 10,
  enableSafetyRobustness: true,
  enablePersona: false,
  personaJson: ''
})

// 计算属性
const analyzedDocuments = computed(() => 
  documents.value.filter(doc => doc.is_analyzed)
)
const selectedCategory = ref('')
const normalizeCategory = (doc: Document) => String(doc.category || '').trim() || '未分类'
const documentCategories = computed(() => {
  const set = new Set<string>()
  for (const doc of analyzedDocuments.value) {
    set.add(normalizeCategory(doc))
  }
  return Array.from(set).sort((a, b) => a.localeCompare(b, 'zh-CN'))
})
const categoryDocCountMap = computed<Record<string, number>>(() => {
  const map: Record<string, number> = {}
  for (const doc of analyzedDocuments.value) {
    const category = normalizeCategory(doc)
    map[category] = (map[category] || 0) + 1
  }
  return map
})

const selectDocumentsByCategory = (replaceSelection: boolean) => {
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择文档分类')
    return
  }
  const targetIds = analyzedDocuments.value
    .filter(doc => normalizeCategory(doc) === selectedCategory.value)
    .map(doc => doc.id)

  if (targetIds.length === 0) {
    ElMessage.warning(`分类“${selectedCategory.value}”下没有已分析文档`)
    return
  }

  if (replaceSelection) {
    generationForm.documentIds = targetIds
  } else {
    generationForm.documentIds = Array.from(new Set([...generationForm.documentIds, ...targetIds]))
  }
  ElMessage.success(`已选中分类“${selectedCategory.value}”下 ${targetIds.length} 个文档`)
}

const clearSelectedDocuments = () => {
  generationForm.documentIds = []
}

const paginatedTestsets = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredTestsets.value.slice(start, end)
})

const progressPercentage = computed(() => {
  if (progressInfo.total === 0) return 0
  return Math.round((progressInfo.current / progressInfo.total) * 100)
})

const progressStatus = computed(() => {
  if (generating.value) return ''
  if (generationFailed.value) return 'exception'
  if (generationComplete.value && generatedQuestions.value.length === 0) return 'exception'
  if (progressPercentage.value >= 100) return 'success'
  if (progressPercentage.value > 0) return ''
  return 'exception'
})

const getQuestionCountType = (count: number) => {
  if (count === 0) return 'danger'
  if (count < 10) return 'warning'
  if (count < 50) return 'primary'
  return 'success'
}

const getMethodType = (method: string) => {
  return method === 'auto' ? 'success' : 'info'
}

const getMethodText = (method: string) => {
  return method === 'auto' ? '自动生成' : '手动创建'
}

const fetchTestsets = async () => {
  loading.value = true
  try {
    const response = await testsetApi.getTestSets()
    testsets.value = response.items
    filterTestsets()
  } catch (error) {
    ElMessage.error('获取测试集列表失败')
  } finally {
    loading.value = false
  }
}

const fetchDocuments = async () => {
  try {
    const response = await documentApi.getDocuments({ limit: 1000 })
    documents.value = response.items
  } catch (error) {
    console.error('Failed to fetch documents:', error)
  }
}

const loadTaxonomy = async () => {
  try {
    const config = await testsetApi.getAdvancedConfig()
    taxonomy.value = config.taxonomy
  } catch (error) {
    console.error('加载分类体系失败:', error)
    taxonomy.value = [
      { major: "基础理解类", minors: ["定义解释", "术语对齐", "事实召回", "表格/字段理解", "流程步骤", "对比区分"] },
      { major: "推理与综合类", minors: ["因果推理", "条件推理", "归纳总结", "例外与边界", "决策建议"] },
      { major: "数值与计算类", minors: ["数值提取", "单位换算", "比例与增长率", "区间与阈值判断", "汇总统计", "规则计费/结算"] },
      { major: "鲁棒性/输入质量类", minors: ["错别字与拼写", "意图模糊", "指代消解", "口语省略", "多意图/混合输入", "不完整信息补问"] },
      { major: "合规与安全类", minors: ["暴力与伤害内容", "仇恨歧视与不当言论", "违法犯罪与危险活动", "色情与成人内容", "虚假与误导信息", "个人信息与隐私泄露"] },
      { major: "多文档关联类", minors: ["跨文档对比", "跨文档流程", "跨文档矛盾检查", "跨文档信息整合", "跨文档引用与追踪", "跨文档规则一致性"] }
    ]
  }
}

const filterTestsets = () => {
  let result = [...testsets.value]
  
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(ts => 
      ts.name.toLowerCase().includes(query) || 
      (ts.description && ts.description.toLowerCase().includes(query))
    )
  }
  
  if (documentFilter.value) {
    result = result.filter(ts => ts.document_id === documentFilter.value)
  }
  
  if (methodFilter.value) {
    result = result.filter(ts => ts.generation_method === methodFilter.value)
  }
  
  filteredTestsets.value = result
  currentPage.value = 1
}

const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
}

const handleCurrentChange = (page: number) => {
  currentPage.value = page
}

const viewTestset = (id: string) => {
  router.push(`/testsets/${id}`)
}

const startEvaluation = (testset: TestSet) => {
  router.push(`/evaluations?testset_id=${testset.id}`)
}

const handleDelete = async (testset: TestSet) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除测试集 "${testset.name}" 吗？`,
      '删除确认',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await testsetApi.deleteTestSet(testset.id)
    ElMessage.success('删除成功')
    fetchTestsets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const handleExportCSV = async (testset: TestSet) => {
  try {
    const blob = await testsetApi.exportTestSet(testset.id)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${testset.name}.csv`
    link.click()
    URL.revokeObjectURL(url)
    ElMessage.success('导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

// 轮询任务状态
const pollTaskStatus = async (taskId: string, testsetId: string) => {
  const pollInterval = 2000
  let lastLogIndex = 0
  
  const poll = async () => {
    if (!generating.value) return
    
    try {
      const task = await testsetApi.getTaskStatus(taskId)
      
      progressInfo.stage = task.message || task.status
      if (typeof task.progress === 'number' && progressInfo.total > 0) {
        const currentByProgress = Math.round(task.progress * progressInfo.total)
        if (currentByProgress > progressInfo.current) {
          progressInfo.current = currentByProgress
        }
      }
      
      if (task.logs && task.logs.length > lastLogIndex) {
        const newLogs = task.logs.slice(lastLogIndex)
        for (const log of newLogs) {
          progressInfo.logs.push(log)
        }
        lastLogIndex = task.logs.length
      }
      
      if (task.status === 'finished') {
        generating.value = false
        generationComplete.value = true
        
        if (task.result && task.result.questions) {
          generatedQuestions.value = task.result.questions
          progressInfo.current = task.result.questions.length
        }
        
        progressInfo.stage = '生成完成'
        progressInfo.logs.push(`所有文档处理完成，共生成 ${generatedQuestions.value.length} 个问题`)
        ElMessage.success(`测试集创建成功，共生成 ${generatedQuestions.value.length} 个问题`)
        
      } else if (task.status === 'failed') {
        generating.value = false
        generationFailed.value = true
        progressInfo.stage = '生成失败'
        progressInfo.logs.push(`错误: ${task.error || '未知错误'}`)
        
        if (createdTestsetId.value) {
          try {
            await testsetApi.deleteTestSet(createdTestsetId.value)
            progressInfo.logs.push('已删除创建的空测试集')
          } catch (deleteError) {
            console.error('删除空测试集失败:', deleteError)
          }
          createdTestsetId.value = null
        }
        
        ElMessage.error(task.error || '生成失败')
        
      } else {
        setTimeout(poll, pollInterval)
      }
    } catch (error: any) {
      console.error('轮询任务状态失败:', error)
      setTimeout(poll, pollInterval)
    }
  }
  
  poll()
}

// 开始生成测试集
const startGeneration = async () => {
  if (generationForm.documentIds.length === 0) {
    ElMessage.warning('请至少选择一个文档')
    return
  }
  
  // 解析人物画像
  let personaList: any[] = []
  if (generationForm.enablePersona && generationForm.personaJson) {
    try {
      personaList = JSON.parse(generationForm.personaJson)
    } catch (e) {
      ElMessage.error('人物画像JSON格式不正确')
      return
    }
  }
  
  generating.value = true
  generationComplete.value = false
  generationFailed.value = false
  generatedQuestions.value = []
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = generationForm.documentIds.length * generationForm.questionsPerDoc
  progressInfo.logs = []
  
  try {
    // 创建测试集
    const testset = await testsetApi.createTestSet({
      document_id: generationForm.documentIds[0],
      name: `测试集_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}`,
      description: `自动生成的测试集，包含${generationForm.questionsPerDoc}个问题/文档`
    })
    
    createdTestsetId.value = testset.id
    progressInfo.stage = '开始生成'
    progressInfo.logs.push('创建测试集成功，开始生成问题...')
    
    const { task_id } = await testsetApi.generateQuestionsAsync(testset.id, {
      num_questions: generationForm.questionsPerDoc * generationForm.documentIds.length,
      generation_mode: 'advanced',
      enable_safety_robustness: generationForm.enableSafetyRobustness,
      document_ids: generationForm.documentIds,
      persona_list: personaList
    })
    
    progressInfo.logs.push(`任务已创建: ${task_id}`)
    
    pollTaskStatus(task_id, testset.id)
    
  } catch (error: any) {
    console.error('生成测试集失败:', error)
    generating.value = false
    generationFailed.value = true
    progressInfo.stage = '生成失败'
    progressInfo.logs.push(`错误: ${error?.response?.data?.detail || error?.message || '未知错误'}`)
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成测试集失败')
  }
}

// 重置生成状态
const resetGeneration = () => {
  showGenerationDialog.value = false
  generating.value = false
  generationComplete.value = false
  generationFailed.value = false
  generatedQuestions.value = []
  createdTestsetId.value = null
  generationForm.documentIds = []
  generationForm.questionsPerDoc = 10
  generationForm.enableSafetyRobustness = true
  generationForm.enablePersona = false
  generationForm.personaJson = ''
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = 0
  progressInfo.logs = []
}

// 查看创建的测试集
const viewCreatedTestset = () => {
  if (createdTestsetId.value) {
    router.push(`/testsets/${createdTestsetId.value}`)
  }
  resetGeneration()
}

onMounted(() => {
  fetchTestsets()
  fetchDocuments()
  loadTaxonomy()
})
</script>

<style lang="scss" scoped>
.testsets-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .filter-bar {
    display: flex;
    gap: 10px;
    margin-bottom: 16px;
    align-items: center;
  }
  
  .pagination-container {
    display: flex;
    justify-content: center;
    margin-top: 16px;
  }

  .button-row {
    display: flex;
    gap: 8px;
    margin-bottom: 6px;
  }

  .button-row:last-child {
    margin-bottom: 0;
  }

  .fixed-width-btn {
    width: 64px;
  }
  
  .mb-4 {
    margin-bottom: 1rem;
  }
  
  .mt-4 {
    margin-top: 1rem;
  }
  
  .generation-config {
    .form-help {
      font-size: 12px;
      color: #909399;
      margin-top: 4px;
      line-height: 1.4;
    }
    
    .taxonomy-preview {
      max-height: 250px;
      overflow-y: auto;
      
      .taxonomy-major {
        font-weight: 600;
      }
      
      .ml-10 {
        margin-left: 10px;
      }
      
      .minor-list {
        display: flex;
        flex-wrap: wrap;
        gap: 6px;
        
        .minor-tag {
          margin: 2px;
        }
      }
    }
  }
  
  .generation-progress {
    .progress-section {
      .progress-info {
        display: flex;
        justify-content: space-between;
        margin-top: 10px;
        font-size: 14px;
        color: #606266;
      }
      
      .progress-logs {
        margin-top: 15px;
        max-height: 200px;
        overflow-y: auto;
        background: #f5f7fa;
        padding: 10px;
        border-radius: 4px;
        font-size: 12px;
        
        .log-item {
          padding: 4px 0;
          border-bottom: 1px solid #ebeef5;
          
          &:last-child {
            border-bottom: none;
          }
        }
      }
    }
    
    .result-stats {
      margin-top: 20px;
      padding: 15px;
      background: #f5f7fa;
      border-radius: 4px;
    }
    
    .result-table {
      margin-top: 20px;
      
      .more-hint {
        text-align: center;
        padding: 10px;
        color: #909399;
        font-size: 12px;
      }
    }
  }
}
</style>
