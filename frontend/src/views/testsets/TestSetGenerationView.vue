<template>
  <div class="testset-generation-view">
    <el-page-header @back="$router.push('/testsets')">
      <template #content>
        <span class="text-large font-600">新建测试集</span>
      </template>
    </el-page-header>
    <el-divider />
    <el-row :gutter="20">
      <!-- 上方左侧：参数配置 -->
      <el-col :span="16">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>测试集生成配置</span>
            </div>
          </template>
          
          <div class="config-form-wrapper" :class="{ 'is-locked': generating }">
          <el-form :model="form" :disabled="generating" label-width="140px">
            <el-form-item label="测试集名称" required>
              <el-input
                v-model="form.name"
                maxlength="100"
                show-word-limit
                placeholder="请输入测试集名称"
              />
            </el-form-item>
            <!-- 文档选择 -->
            <el-form-item label="选择文档" required>
              <div class="doc-picker-trigger">
                <el-button :disabled="generating" @click="openDocumentPicker">
                  选择文档
                </el-button>
                <el-text type="info">已选 {{ form.documentIds.length }} 个文档</el-text>
              </div>
              <div v-if="selectedDocumentPreviewText" class="selected-doc-preview">
                {{ selectedDocumentPreviewText }}
              </div>
            </el-form-item>
            <el-form-item label="生成模式">
              <el-radio-group v-model="form.generationMode">
                <el-radio-button label="single_turn">单轮</el-radio-button>
                <el-radio-button label="multi_turn">多轮</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-divider content-position="left">生成参数</el-divider>
            
            <template v-if="!isConversationMode">
              <!-- 生成分布模式 -->
              <el-form-item label="题目分配方式">
                <el-radio-group v-model="form.distributionMode">
                  <el-radio-button label="per_doc">按文档生成</el-radio-button>
                  <el-radio-button label="total">按总量生成</el-radio-button>
                </el-radio-group>
                <div class="form-help" v-if="form.distributionMode === 'per_doc'">每个文档独立生成指定数量的题目，保证文档覆盖</div>
                <div class="form-help" v-else>输入总题目数，系统按题型比例分配</div>
              </el-form-item>

              <!-- 按文档生成：每文档问题数 -->
              <el-form-item v-if="form.distributionMode === 'per_doc'" label="每个文档问题数">
                <el-input-number 
                  v-model="form.questionsPerDoc" 
                  :min="1" 
                  :max="50"
                  style="width: 100%;"
                />
              </el-form-item>

              <!-- 按总量生成：总题目数 -->
              <el-form-item v-if="form.distributionMode === 'total'" label="总题目数">
                <el-input-number 
                  v-model="form.numTotalQuestions" 
                  :min="1" 
                  style="width: 100%;"
                />
              </el-form-item>
              
              <!-- 按总量生成时才显示鲁棒性/安全开关 -->
              <template v-if="form.distributionMode === 'total'">
                <el-form-item label="多文档关联比例">
                  <el-slider
                    v-model="form.multiDocRatio"
                    :min="0"
                    :max="100"
                    :step="5"
                    show-input
                    :format-tooltip="(val: number) => `${val}%`"
                    style="width: 100%;"
                  />
                  <div class="form-help">控制跨文档对比、跨文档信息整合等多文档关联问题的占比</div>
                </el-form-item>
                
                <el-form-item label="鲁棒性/输入质量类">
                  <el-switch 
                    v-model="form.enableRobustnessInputQuality"
                    active-text="启用"
                    inactive-text="禁用"
                  />
                  <div class="form-help">控制错别字、意图模糊、指代消解等问题生成</div>
                </el-form-item>
                
                <el-form-item label="合规与安全类">
                  <el-switch 
                    v-model="form.enableComplianceSafety"
                    active-text="启用"
                    inactive-text="禁用"
                  />
                  <div class="form-help">控制安全合规、隐私等风险问题生成</div>
                </el-form-item>
              </template>
              
              <!-- 人物画像JSON -->
              <el-form-item label="人物画像JSON">
                <el-input
                  v-model="form.personaJson"
                  type="textarea"
                  :rows="6"
                  placeholder="请输入人物画像JSON配置，格式示例：
[
  {&quot;name&quot;: &quot;新手客户&quot;, &quot;description&quot;: &quot;刚接触保险产品，对基本概念不了解的新用户&quot;},
  {&quot;name&quot;: &quot;资深代理人&quot;, &quot;description&quot;: &quot;有多年代理经验，熟悉各类保险产品和条款&quot;}
]"
                />
                <div class="form-help">定义用户角色，帮助生成更真实的问题</div>
              </el-form-item>
            </template>

            <template v-else>
              <el-form-item label="Case 数量">
                <el-input-number
                  v-model="form.numCases"
                  :min="1"
                  :max="50"
                  style="width: 100%;"
                />
              </el-form-item>
              <el-form-item label="每 Case 轮数范围">
                <div class="conversation-slider-wrapper">
                  <el-slider
                    v-model="form.turnRange"
                    range
                    :min="3"
                    :max="5"
                    :step="1"
                    show-stops
                    style="width: 100%;"
                  />
                  <div class="form-help">当前范围：{{ form.turnRange[0] }} - {{ form.turnRange[1] }} 轮</div>
                </div>
              </el-form-item>
              <el-form-item label="Case 类型比例">
                <div class="conversation-ratio-grid">
                  <div class="ratio-item">
                    <div class="ratio-label">单切片深挖</div>
                    <el-input-number
                      v-model="form.caseTypeRatioPercent.single_chunk_deep"
                      :min="0"
                      :max="100"
                      :precision="1"
                      :step="1"
                      style="width: 100%;"
                      @change="normalizeCaseTypeRatioInputs('single_chunk_deep')"
                    />
                  </div>
                  <div class="ratio-item">
                    <div class="ratio-label">同文档切片链</div>
                    <el-input-number
                      v-model="form.caseTypeRatioPercent.same_doc_chain"
                      :min="0"
                      :max="100"
                      :precision="1"
                      :step="1"
                      style="width: 100%;"
                      @change="normalizeCaseTypeRatioInputs('same_doc_chain')"
                    />
                  </div>
                  <div class="ratio-item">
                    <div class="ratio-label">跨文档关联</div>
                    <el-input-number
                      v-model="form.caseTypeRatioPercent.cross_doc_assoc"
                      :min="0"
                      :max="100"
                      :precision="1"
                      :step="1"
                      style="width: 100%;"
                      @change="normalizeCaseTypeRatioInputs('cross_doc_assoc')"
                    />
                  </div>
                </div>
                <div class="form-help">输入后会自动归一化，当前总和：{{ normalizedRatioTotal }}%</div>
              </el-form-item>
            </template>

            <!-- 操作按钮 -->
            <el-form-item class="mt-20">
              <el-button 
                type="primary" 
                size="large"
                @click="handleGenerate"
                :loading="generating"
                :disabled="form.documentIds.length === 0"
                style="width: 100%;"
              >
                {{ generateButtonText }}
              </el-button>
            </el-form-item>
            <el-form-item v-if="generationFailed" class="mt-10">
              <el-button type="success" plain style="width: 100%;" @click="resumeGeneration">
                继续生成（断点续传）
              </el-button>
            </el-form-item>
            <el-form-item v-if="generationFailed" class="mt-10">
              <el-button type="warning" plain style="width: 100%;" @click="retryLastSubmit">
                使用上次参数重试
              </el-button>
            </el-form-item>
            <el-alert
              v-if="generationFailed"
              type="error"
              :closable="false"
              title="生成失败，请检查参数或模型配置后重试。"
              class="mt-10"
            />
            <el-alert
              v-if="generationSucceeded"
              type="success"
              :closable="false"
              title="生成成功，请点击“查看测试集详情”进入详情页。"
              class="mt-10"
            />
            <el-form-item v-if="generationSucceeded" class="mt-10">
              <el-button type="primary" plain style="width: 100%;" @click="goToCreatedTestset">
                查看测试集详情
              </el-button>
            </el-form-item>
          </el-form>
          </div>
        </el-card>
      </el-col>

      <!-- 上方右侧：分类体系预览（独立框） -->
      <el-col :span="8">
        <el-card class="taxonomy-card">
          <template #header>
            <div class="card-header">
              <span>问题分类体系预览</span>
            </div>
          </template>
          <div class="config-form-wrapper" :class="{ 'is-locked': generating }">
            <div class="taxonomy-preview">
              <div class="taxonomy-actions">
                <el-button size="small" @click="selectAllMinors">全选</el-button>
                <el-button size="small" @click="deselectAllMinors">清空</el-button>
                <span class="selected-count">已选 {{ selectedMinors.size }} / {{ totalMinorCount }} 个分类</span>
              </div>
              <el-collapse>
                <el-collapse-item 
                  v-for="(category, index) in taxonomy" 
                  :key="index" 
                  :title="category.major"
                >
                  <template #title>
                    <span class="taxonomy-major">{{ category.major }}</span>
                    <el-tag size="small" type="info" class="ml-10">{{ getSelectedCountInMajor(category) }}/{{ category.minors.length }}</el-tag>
                  </template>
                  <div class="minor-list">
                    <el-tag 
                      v-for="(minor, mi) in category.minors" 
                      :key="mi" 
                      size="small" 
                      class="minor-tag"
                      :class="{ 'minor-tag-selected': selectedMinors.has(minor) }"
                      :effect="selectedMinors.has(minor) ? 'dark' : 'plain'"
                      @click="toggleMinor(minor)"
                    >
                      {{ minor }}
                    </el-tag>
                  </div>
                </el-collapse-item>
              </el-collapse>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <!-- 下方：生成进度和结果 -->
      <el-col :span="24" class="mt-20">
        <!-- 生成进度 -->
        <el-card v-if="generating || generatedItemCount > 0" class="progress-card">
          <template #header>
            <div class="card-header">
              <span>生成进度</span>
              <el-button v-if="!isConversationResultMode && generatedQuestions.length > 0" text @click="exportCSV">
                导出CSV
              </el-button>
            </div>
          </template>
          
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
                v-for="(log, idx) in progressInfo.logs.slice(-5)" 
                :key="idx"
                class="log-item"
              >
                {{ log }}
              </div>
            </div>
          </div>
          
          <!-- 生成结果统计 -->
          <div v-if="!generating && progressInfo.logs.length > 0" class="result-stats">
            <el-row :gutter="10">
              <el-col :span="8">
                <el-statistic :title="generatedItemStatTitle" :value="generatedItemCount" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="来源文档数" :value="form.documentIds.length" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="状态" :value="generatedItemCount > 0 ? '已完成' : '生成失败'" />
              </el-col>
            </el-row>
          </div>
        </el-card>
        
        <!-- 生成结果表格 -->
        <el-card v-if="!isConversationResultMode && generatedQuestions.length > 0" class="result-card mt-20">
          <template #header>
            <div class="card-header">
              <span>生成结果</span>
              <el-space>
                <el-input 
                  v-model="filterText" 
                  placeholder="搜索问题" 
                  clearable
                  style="width: 200px;"
                />
              </el-space>
            </div>
          </template>
          
          <el-table 
            :data="filteredQuestions" 
            style="width: 100%"
            max-height="500"
            stripe
          >
            <el-table-column type="index" width="50" />
            <el-table-column prop="question" label="问题" min-width="250" show-overflow-tooltip />
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
            <el-table-column label="操作" width="80" fixed="right">
              <template #default="{ row, $index }">
                <el-button size="small" link type="primary" @click="viewDetail(row)">
                  详情
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
        
        <!-- 空状态 -->
        <el-card v-if="!generating && generatedItemCount === 0 && progressInfo.logs.length === 0" class="empty-card">
          <el-empty description="请选择文档并配置参数，然后点击生成测试集">
            <template #image>
              <el-icon :size="60"><DocumentAdd /></el-icon>
            </template>
          </el-empty>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 问题详情对话框 -->
    <el-dialog v-model="detailDialogVisible" title="问题详情" width="700px">
      <div v-if="currentQuestion" class="question-detail">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="问题">
            {{ currentQuestion.question }}
          </el-descriptions-item>
          <el-descriptions-item label="预期答案">
            {{ currentQuestion.expected_answer || currentQuestion.ground_truth || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="上下文">
            <el-input
              v-model="currentQuestion.context"
              type="textarea"
              :rows="4"
              readonly
            />
          </el-descriptions-item>
          <el-descriptions-item label="问题类型">
            {{ currentQuestion.question_type || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="主要分类">
            {{ currentQuestion.category_major || '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="次要分类">
            {{ currentQuestion.category_minor || '-' }}
          </el-descriptions-item>
          <el-descriptions-item v-if="currentQuestion.metadata" label="元数据">
            <pre>{{ JSON.stringify(currentQuestion.metadata, null, 2) }}</pre>
          </el-descriptions-item>
        </el-descriptions>
      </div>
    </el-dialog>

    <!-- 文档选择穿梭框 -->
    <el-dialog
      v-model="documentPickerVisible"
      title="选择文档"
      width="1000px"
      class="document-picker-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="document-picker-content">
        <div class="picker-toolbar">
          <el-cascader
            v-model="pickerSelectedCategories"
            :options="categoryTree"
            placeholder="按分类选择（可多选）"
            clearable
            filterable
            collapse-tags
            collapse-tags-tooltip
            style="width: 300px;"
            :props="{ expandTrigger: 'hover', checkStrictly: true, multiple: true }"
          />
          <el-button @click="selectPickerDocumentsByCategory(false)">追加该分类</el-button>
          <el-button type="primary" plain @click="selectPickerDocumentsByCategory(true)">仅选该分类</el-button>
          <el-button text @click="clearPickerDocumentSelection">清空已选</el-button>
        </div>
        <el-transfer
          v-model="tempDocumentIds"
          :data="transferData"
          filterable
          :filter-method="transferFilterMethod"
          filter-placeholder="搜索文档名称/分类"
          :titles="['可选文档', '已选文档']"
          :props="{ key: 'key', label: 'label' }"
          :button-texts="['移除', '添加']"
        />
      </div>
      <template #footer>
        <el-button @click="cancelDocumentPicker">取消</el-button>
        <el-button type="primary" @click="confirmDocumentPicker">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, onActivated } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElNotification } from 'element-plus'
import { testsetApi } from '@/api/testsets'
import { taskApi } from '@/api/tasks'
import { documentApi } from '@/api/documents'
import { useTaskStore } from '@/stores/task'
import { getLocalStorage, removeLocalStorage, setLocalStorage } from '@/utils/storage'
import { useCategoryHierarchy } from '@/composables/useCategoryHierarchy'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()
const { categoryTree } = useCategoryHierarchy()
const GENERATION_SESSION_STORAGE_KEY = 'testset_generation_session'
const GENERATION_SESSION_MAX_AGE_MS = 12 * 60 * 60 * 1000

const buildLocalNameStamp = () => {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`
}

type GenerationPayload = {
  name: string
  documentIds: string[]
  generationMode: 'single_turn' | 'multi_turn'
  distributionMode: 'per_doc' | 'total'
  questionsPerDoc: number
  numTotalQuestions: number
  numCases: number
  turnRange: [number, number]
  caseTypeRatio: {
    single_chunk_deep: number
    same_doc_chain: number
    cross_doc_assoc: number
  }
  enableSafetyRobustness: boolean
  personaJson: string
  questionTypes: string[]
  multiDocRatio: number
}

type SavedGenerationSession = {
  taskId: string
  createdTestsetId: string
  payload: GenerationPayload
  savedAt: number
}

// 表单数据
const form = reactive({
  name: `测试集_${buildLocalNameStamp()}`,
  documentIds: [] as string[],
  generationMode: 'single_turn' as 'single_turn' | 'multi_turn',
  distributionMode: 'per_doc' as 'per_doc' | 'total',
  questionsPerDoc: 5,
  numTotalQuestions: 10,
  numCases: 5,
  turnRange: [3, 5] as [number, number],
  caseTypeRatioPercent: {
    single_chunk_deep: 20,
    same_doc_chain: 60,
    cross_doc_assoc: 20
  },
  enableRobustnessInputQuality: false,
  enableComplianceSafety: false,
  multiDocRatio: 10,
  personaJson: ''
})

// 分类体系
const taxonomy = ref<Array<{major: string, minors: string[]}>>([])
const selectedMinors = ref<Set<string>>(new Set())

const totalMinorCount = computed(() => 
  taxonomy.value.reduce((sum, cat) => sum + cat.minors.length, 0)
)

const getSelectedCountInMajor = (category: { major: string; minors: string[] }) => 
  category.minors.filter(m => selectedMinors.value.has(m)).length

const toggleMinor = (minor: string) => {
  const newSet = new Set(selectedMinors.value)
  if (newSet.has(minor)) {
    newSet.delete(minor)
  } else {
    newSet.add(minor)
  }
  selectedMinors.value = newSet
}

const selectAllMinors = () => {
  const allMinors = new Set<string>()
  taxonomy.value.forEach(cat => cat.minors.forEach(m => allMinors.add(m)))
  selectedMinors.value = allMinors
}

const deselectAllMinors = () => {
  selectedMinors.value = new Set()
}

// 状态
const generating = ref(false)
const generationFailed = ref(false)
const createdTestsetId = ref<string | null>(null)
const generatedQuestions = ref<any[]>([])
const generatedConversationCaseCount = ref(0)
const resultMode = ref<'single_turn' | 'multi_turn'>('single_turn')
const filterText = ref('')
const initialLoading = ref(false)
const documents = ref<any[]>([])
const lastSubmitPayload = ref<null | {
  name: string
  documentIds: string[]
  generationMode: 'single_turn' | 'multi_turn'
  distributionMode: 'per_doc' | 'total'
  questionsPerDoc: number
  numTotalQuestions: number
  numCases: number
  turnRange: [number, number]
  caseTypeRatio: {
    single_chunk_deep: number
    same_doc_chain: number
    cross_doc_assoc: number
  }
  enableSafetyRobustness: boolean
  personaJson: string
  questionTypes: string[]
  multiDocRatio: number
}>(null)
let pollingTimer: number | null = null
let hasShownCompletionNotification = false

// 进度信息
const progressInfo = reactive({
  stage: '准备中',
  current: 0,
  total: 0,
  logs: [] as string[]
})

const isConversationMode = computed(() => form.generationMode === 'multi_turn')
const isConversationResultMode = computed(() => resultMode.value === 'multi_turn')

const generatedItemCount = computed(() =>
  isConversationResultMode.value ? generatedConversationCaseCount.value : generatedQuestions.value.length
)

const generatedItemStatTitle = computed(() =>
  isConversationResultMode.value ? '总 Case 数' : '总问题数'
)

const generateButtonText = computed(() => {
  if (!generating.value) return '开始生成测试集'
  if (isConversationMode.value) {
    return `生成中... (${progressInfo.current}/${progressInfo.total} Case)`
  }
  return `生成中... (${progressInfo.current}/${progressInfo.total})`
})

// 进度百分比
const progressPercentage = computed(() => {
  if (progressInfo.total === 0) return 0
  return Math.round((progressInfo.current / progressInfo.total) * 100)
})

// 进度状态
const progressStatus = computed(() => {
  if (generationFailed.value) return 'exception'
  if (!generating.value && generatedItemCount.value === 0 && progressInfo.logs.length > 0) return 'exception'
  if (progressPercentage.value >= 100 && generatedItemCount.value > 0) return 'success'
  if (progressPercentage.value > 0) return ''
  return 'exception'
})

const generationSucceeded = computed(() =>
  !generating.value &&
  !generationFailed.value &&
  !!createdTestsetId.value &&
  generatedItemCount.value > 0
)

const hasInMemoryGenerationState = computed(() =>
  generating.value ||
  !!createdTestsetId.value ||
  generatedItemCount.value > 0 ||
  progressInfo.logs.length > 0
)

// 过滤后的问题
const filteredQuestions = computed(() => {
  if (!filterText.value) return generatedQuestions.value
  const searchText = filterText.value.toLowerCase()
  return generatedQuestions.value.filter(q => 
    q.question?.toLowerCase().includes(searchText) ||
    q.question_type?.toLowerCase().includes(searchText) ||
    q.category_major?.toLowerCase().includes(searchText)
  )
})

// 已分析的文档
const analyzedDocuments = computed(() =>
  documents.value.filter((doc: any) => doc.is_analyzed && doc.status === 'active')
)
const transferData = computed(() =>
  analyzedDocuments.value.map((doc: any) => {
    const category = String(doc?.category || '').trim() || '未分类'
    return {
      key: doc.id,
      label: `${doc.filename}（${category}）`
    }
  })
)
const transferFilterMethod = (query: string, item: { label: string }) => {
  if (!query) return true
  return item.label.toLowerCase().includes(query.toLowerCase())
}
const documentPickerVisible = ref(false)
const tempDocumentIds = ref<string[]>([])
const pickerSelectedCategories = ref<string[][]>([])
const documentNameMap = computed<Record<string, string>>(() => {
  const map: Record<string, string> = {}
  for (const doc of analyzedDocuments.value) {
    map[doc.id] = doc.filename
  }
  return map
})
const selectedDocumentPreviewText = computed(() => {
  if (form.documentIds.length === 0) return ''
  const names = form.documentIds
    .slice(0, 3)
    .map(id => documentNameMap.value[id] || id)
  const more = form.documentIds.length > 3 ? ` 等${form.documentIds.length}个` : ''
  return `已选: ${names.join('，')}${more}`
})
const openDocumentPicker = () => {
  tempDocumentIds.value = [...form.documentIds]
  pickerSelectedCategories.value = []
  documentPickerVisible.value = true
}
const confirmDocumentPicker = () => {
  form.documentIds = [...tempDocumentIds.value]
  documentPickerVisible.value = false
}
const cancelDocumentPicker = () => {
  pickerSelectedCategories.value = []
  documentPickerVisible.value = false
}
const normalizeCategory = (doc: any) => String(doc?.category || '').trim() || '未分类'

const selectPickerDocumentsByCategory = (replaceSelection: boolean) => {
  if (!pickerSelectedCategories.value || pickerSelectedCategories.value.length === 0) {
    ElMessage.warning('请先选择文档分类')
    return
  }
  
  const categoryPaths = pickerSelectedCategories.value.map(path => path.join('/'))
  
  const targetIds = analyzedDocuments.value
    .filter(doc => {
      const docCategory = normalizeCategory(doc)
      return categoryPaths.some(catPath => 
        docCategory === catPath || docCategory.startsWith(catPath + '/')
      )
    })
    .map(doc => doc.id)
  
  if (targetIds.length === 0) {
    ElMessage.warning('所选分类下没有可用文档')
    return
  }

  if (replaceSelection) {
    tempDocumentIds.value = targetIds
  } else {
    tempDocumentIds.value = Array.from(new Set([...tempDocumentIds.value, ...targetIds]))
  }
  ElMessage.success(`已选中 ${categoryPaths.length} 个分类下共 ${targetIds.length} 个文档`)
}

const clearPickerDocumentSelection = () => {
  tempDocumentIds.value = []
}

const normalizeCaseTypeRatioInputs = (
  preferredKey?: 'single_chunk_deep' | 'same_doc_chain' | 'cross_doc_assoc'
) => {
  const source = form.caseTypeRatioPercent
  const entries = [
    ['single_chunk_deep', Number(source.single_chunk_deep || 0)],
    ['same_doc_chain', Number(source.same_doc_chain || 0)],
    ['cross_doc_assoc', Number(source.cross_doc_assoc || 0)]
  ] as Array<['single_chunk_deep' | 'same_doc_chain' | 'cross_doc_assoc', number]>
  const total = entries.reduce((sum, [, value]) => sum + Math.max(value, 0), 0)

  if (total <= 0) {
    source.single_chunk_deep = 20
    source.same_doc_chain = 60
    source.cross_doc_assoc = 20
    return
  }

  const normalized = Object.fromEntries(
    entries.map(([key, value]) => [key, Number(((Math.max(value, 0) / total) * 100).toFixed(1))])
  ) as Record<'single_chunk_deep' | 'same_doc_chain' | 'cross_doc_assoc', number>

  const keys = ['single_chunk_deep', 'same_doc_chain', 'cross_doc_assoc'] as const
  const normalizedTotal = keys.reduce((sum, key) => sum + normalized[key], 0)
  const diff = Number((100 - normalizedTotal).toFixed(1))
  const targetKey = preferredKey || 'same_doc_chain'
  normalized[targetKey] = Number((normalized[targetKey] + diff).toFixed(1))

  source.single_chunk_deep = normalized.single_chunk_deep
  source.same_doc_chain = normalized.same_doc_chain
  source.cross_doc_assoc = normalized.cross_doc_assoc
}

const normalizedRatioTotal = computed(() =>
  Number(
    (
      form.caseTypeRatioPercent.single_chunk_deep
      + form.caseTypeRatioPercent.same_doc_chain
      + form.caseTypeRatioPercent.cross_doc_assoc
    ).toFixed(1)
  )
)

// 详情对话框
const detailDialogVisible = ref(false)
const currentQuestion = ref<any>(null)

// 加载分类体系
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
  selectAllMinors()
}

// 生成测试集
const saveGenerationSession = (taskId: string, payload: GenerationPayload, testsetId: string) => {
  setLocalStorage<SavedGenerationSession>(GENERATION_SESSION_STORAGE_KEY, {
    taskId,
    createdTestsetId: testsetId,
    payload,
    savedAt: Date.now()
  })
}

const clearGenerationSession = () => {
  removeLocalStorage(GENERATION_SESSION_STORAGE_KEY)
}

const getSavedGenerationSession = (): SavedGenerationSession | null => {
  const session = getLocalStorage<SavedGenerationSession>(GENERATION_SESSION_STORAGE_KEY)
  if (!session) return null
  if (!session.taskId || !session.createdTestsetId || !session.payload || !session.savedAt) {
    clearGenerationSession()
    return null
  }
  if (Date.now() - Number(session.savedAt) > GENERATION_SESSION_MAX_AGE_MS) {
    clearGenerationSession()
    return null
  }
  return session
}

const applySavedPayloadToForm = (payload: GenerationPayload) => {
  form.name = payload.name
  form.documentIds = [...payload.documentIds]
  form.generationMode = payload.generationMode
  form.questionsPerDoc = payload.questionsPerDoc
  form.numCases = payload.numCases
  form.turnRange = [...payload.turnRange] as [number, number]
  form.caseTypeRatioPercent.single_chunk_deep = Number((payload.caseTypeRatio.single_chunk_deep * 100).toFixed(1))
  form.caseTypeRatioPercent.same_doc_chain = Number((payload.caseTypeRatio.same_doc_chain * 100).toFixed(1))
  form.caseTypeRatioPercent.cross_doc_assoc = Number((payload.caseTypeRatio.cross_doc_assoc * 100).toFixed(1))
  form.enableRobustnessInputQuality = payload.enableSafetyRobustness
  form.enableComplianceSafety = false
  form.personaJson = payload.personaJson
  resultMode.value = payload.generationMode
  lastSubmitPayload.value = payload
}

const getExpectedTotalFromPayload = (payload: GenerationPayload) => (
  payload.generationMode === 'multi_turn'
    ? payload.numCases
    : payload.distributionMode === 'per_doc'
      ? payload.documentIds.length * payload.questionsPerDoc
      : payload.numTotalQuestions
)

const stopPolling = () => {
  if (pollingTimer) {
    window.clearInterval(pollingTimer)
    pollingTimer = null
  }
}

const cleanupCreatedTestset = async (message?: string) => {
  if (!createdTestsetId.value) return
  const testsetId = createdTestsetId.value
  try {
    await testsetApi.deleteTestSet(testsetId)
    if (message) {
      progressInfo.logs.push(message)
    }
  } catch (error) {
    console.error('删除失败任务对应测试集失败:', error)
  } finally {
    createdTestsetId.value = null
  }
}

const syncTaskStoreStatus = (taskId: string, task: any, taskName: string, targetId: string) => {
  const statusMap: Record<string, 'pending' | 'running' | 'cancelling' | 'cancelled' | 'completed' | 'failed'> = {
    pending: 'pending',
    running: 'running',
    cancelling: 'cancelling',
    cancelled: 'cancelled',
    finished: 'completed',
    failed: 'failed'
  }
  taskStore.addTask({
    id: taskId,
    name: taskName,
    type: 'testset',
    progress: Math.round(Number(task.progress || 0) * 100),
    status: statusMap[task.status] || 'running',
    targetId
  })
}

const pollTaskStatus = (taskId: string, initialLogIndex = 0) => {
  let lastLogIndex = initialLogIndex
  const poll = async () => {
    try {
      const task = await testsetApi.getTaskStatus(taskId)
      const taskName = `${resultMode.value === 'multi_turn' ? '生成多轮测试集' : '生成测试集'}: ${form.name}`
      const contextInfo = (task.contextInfo || task.context_info || {}) as Record<string, any>
      const totalCases = Number(contextInfo.totalCases ?? contextInfo.total_cases ?? 0)
      const currentCase = Number(contextInfo.currentCase ?? contextInfo.current_case ?? 0)
      const currentTurn = Number(contextInfo.currentTurn ?? contextInfo.current_turn ?? 0)

      if (isConversationMode.value && totalCases > 0) {
        progressInfo.stage = currentCase > 0
          ? `正在生成 Case ${currentCase}/${totalCases}${currentTurn > 0 ? `，Turn ${currentTurn}...` : '...'}`
          : (task.message || task.status)
        progressInfo.total = totalCases
        if (currentCase > 0) {
          progressInfo.current = Math.max(progressInfo.current, currentCase)
        }
      } else {
        progressInfo.stage = task.message || task.status
      }

      if (!isConversationMode.value && typeof task.total_steps === 'number' && task.total_steps > 0) {
        progressInfo.total = task.total_steps
      }
      if (!isConversationMode.value && typeof task.current_step === 'number') {
        progressInfo.current = Math.max(progressInfo.current, task.current_step)
      }

      if (!isConversationMode.value && typeof task.progress === 'number' && progressInfo.total > 0) {
        const currentByProgress = Math.round(task.progress * progressInfo.total)
        if (currentByProgress > progressInfo.current) {
          progressInfo.current = currentByProgress
        }
      }

      // 更新全局任务状态
      syncTaskStoreStatus(taskId, task, taskName, createdTestsetId.value || '')
      taskStore.updateTask(taskId, {
        progress: progressPercentage.value,
        status: 'running',
        message: task.message,
        currentStep: task.current_step ?? undefined,
        totalSteps: task.total_steps ?? undefined,
      })

      if (task.logs && task.logs.length > lastLogIndex) {
        const newLogs = task.logs.slice(lastLogIndex)
        for (const log of newLogs) {
          progressInfo.logs.push(log)
        }
        lastLogIndex = task.logs.length
      }

      if (task.status === 'finished') {
        stopPolling()
        generating.value = false
        generatedQuestions.value = task.result?.questions || []
        generatedConversationCaseCount.value = Number(
          task.result?.generated_case_count
          || (Array.isArray(task.result?.generated_case_ids) ? task.result.generated_case_ids.length : 0)
          || 0
        )
        progressInfo.current = progressInfo.total || generatedItemCount.value
        progressInfo.stage = '生成完成'
        syncTaskStoreStatus(taskId, task, taskName, createdTestsetId.value || '')
        taskStore.updateTask(taskId, { progress: 100, status: 'completed' })

        if (!hasShownCompletionNotification) {
          hasShownCompletionNotification = true
          ElNotification({
            title: '生成成功',
            message: isConversationResultMode.value
              ? `已生成 ${generatedConversationCaseCount.value} 个多轮 Case，请点击"查看测试集详情"继续`
              : `已生成 ${generatedQuestions.value.length} 个问题，请点击"查看测试集详情"继续`,
            type: 'success'
          })
        }
        return
      }

      if (task.status === 'cancelled') {
        stopPolling()
        generating.value = false
        generationFailed.value = true
        progressInfo.stage = '生成已取消'
        syncTaskStoreStatus(taskId, task, taskName, createdTestsetId.value || '')
        progressInfo.logs.push(task.message || '任务已取消')
        // 断点续传场景：如果已有部分问题生成，保留测试集以便后续续传
        const contextInfo = (task.contextInfo || task.context_info || {}) as Record<string, any>
        const hasGenerated = Number(contextInfo.generated_count ?? 0) > 0
        if (!hasGenerated) {
          await cleanupCreatedTestset('已删除已取消任务创建的测试集')
        } else {
          progressInfo.logs.push(`已生成 ${contextInfo.generated_count} 个问题，可点击"继续生成（断点续传）"恢复`)
        }
        ElNotification({
          title: '任务已取消',
          message: hasGenerated
            ? `已部分生成 ${contextInfo.generated_count} 个问题，可点击"继续生成（断点续传）"恢复`
            : (task.message || '测试集生成已取消'),
          type: 'warning'
        })
        return
      }

      if (task.status === 'failed') {
        stopPolling()
        generating.value = false
        generationFailed.value = true
        progressInfo.stage = '生成失败'
        syncTaskStoreStatus(taskId, task, taskName, createdTestsetId.value || '')

        const err = task.error || '未知错误'
        progressInfo.logs.push(`错误: ${err}`)
        // 断点续传场景：如果已有部分问题生成，保留测试集以便后续续传
        const contextInfo = (task.contextInfo || task.context_info || {}) as Record<string, any>
        const hasGenerated = Number(contextInfo.generated_count ?? 0) > 0
        if (!hasGenerated) {
          await cleanupCreatedTestset('已删除失败任务创建的测试集')
        } else {
          progressInfo.logs.push(`已生成 ${contextInfo.generated_count} 个问题，可点击"继续生成（断点续传）"恢复`)
        }
        ElNotification({
          title: '生成失败',
          message: hasGenerated
            ? `任务失败，但已保存 ${contextInfo.generated_count} 个问题，可点击"继续生成（断点续传）"恢复`
            : `任务执行失败：${err}，可直接点击"使用上次参数重试"`,
          type: 'error'
        })
      }
    } catch (error: any) {
      stopPolling()
      generating.value = false
      generationFailed.value = true
      progressInfo.stage = '轮询中断'

      const err = error?.response?.data?.detail || error?.message || '网络异常'
      progressInfo.logs.push(`轮询失败: ${err}`)
      progressInfo.logs.push('后端任务可能仍在运行，请刷新页面查看进度')
      ElNotification({
        title: '轮询中断',
        message: `状态轮询失败：${err}。后端任务可能仍在运行，请刷新页面恢复进度。`,
        type: 'warning',
        duration: 10000
      })
    }
  }

  poll()
  pollingTimer = window.setInterval(poll, 2000)
}

const restoreGenerationSession = async () => {
  const session = getSavedGenerationSession()
  if (!session) return false

  try {
    const { taskId, createdTestsetId: savedTestsetId, payload } = session
    const task = await testsetApi.getTaskStatus(taskId)

    applySavedPayloadToForm(payload)
    createdTestsetId.value = savedTestsetId
    generatedQuestions.value = []
    generatedConversationCaseCount.value = 0
    generationFailed.value = false
    hasShownCompletionNotification = false
    progressInfo.total = getExpectedTotalFromPayload(payload)
    progressInfo.current = 0
    progressInfo.logs = task.logs ? [...task.logs] : []

    if (payload.generationMode === 'multi_turn') {
      const contextInfo = (task.contextInfo || task.context_info || {}) as Record<string, any>
      const totalCases = Number(contextInfo.totalCases ?? contextInfo.total_cases ?? 0)
      const currentCase = Number(contextInfo.currentCase ?? contextInfo.current_case ?? 0)
      const currentTurn = Number(contextInfo.currentTurn ?? contextInfo.current_turn ?? 0)
      progressInfo.total = totalCases > 0 ? totalCases : progressInfo.total
      progressInfo.current = currentCase > 0 ? currentCase : progressInfo.current
      progressInfo.stage = currentCase > 0
        ? `正在生成 Case ${currentCase}/${progressInfo.total}${currentTurn > 0 ? `，Turn ${currentTurn}...` : '...'}`
        : (task.message || '准备中')
    } else {
      if (typeof task.total_steps === 'number' && task.total_steps > 0) {
        progressInfo.total = task.total_steps
      }
      if (typeof task.current_step === 'number') {
        progressInfo.current = task.current_step
      } else if (typeof task.progress === 'number' && progressInfo.total > 0) {
        progressInfo.current = Math.round(task.progress * progressInfo.total)
      }
      progressInfo.stage = task.message || '准备中'
    }

    syncTaskStoreStatus(taskId, task, `${payload.generationMode === 'multi_turn' ? '生成多轮测试集' : '生成测试集'}: ${payload.name}`, savedTestsetId)

    if (task.status === 'finished') {
      generating.value = false
      generatedQuestions.value = task.result?.questions || []
      generatedConversationCaseCount.value = Number(
        task.result?.generated_case_count
        || (Array.isArray(task.result?.generated_case_ids) ? task.result.generated_case_ids.length : 0)
        || 0
      )
      progressInfo.current = progressInfo.total || generatedItemCount.value
      progressInfo.stage = '生成完成'
      return true
    }

    if (task.status === 'failed' || task.status === 'cancelled') {
      generating.value = false
      generationFailed.value = true
      progressInfo.stage = task.status === 'cancelled' ? '生成已取消' : '生成失败'
      return true
    }

    generating.value = true
    pollTaskStatus(taskId, task.logs?.length || 0)
    ElMessage.success('已恢复测试集生成进度')
    return true
  } catch (error: any) {
    clearGenerationSession()
    console.error('恢复测试集生成会话失败:', error)
    return false
  }
}

const submitGeneration = async (payload: GenerationPayload) => {
  clearGenerationSession()
  hasShownCompletionNotification = false
  generating.value = true
  resultMode.value = payload.generationMode
  generationFailed.value = false
  generatedQuestions.value = []
  generatedConversationCaseCount.value = 0
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = payload.generationMode === 'multi_turn'
    ? payload.numCases
    : payload.distributionMode === 'per_doc'
      ? payload.documentIds.length * payload.questionsPerDoc
      : payload.numTotalQuestions
  progressInfo.logs = []

  try {
    let personaList: any[] = []
    if (payload.generationMode !== 'multi_turn' && payload.personaJson) {
      personaList = JSON.parse(payload.personaJson)
    }

    const testSet = await testsetApi.createTestSet({
      document_id: payload.documentIds[0],
      name: payload.name,
      description: payload.generationMode === 'multi_turn'
        ? `自动生成的多轮测试集，预计 ${payload.numCases} 个 Case`
        : payload.distributionMode === 'per_doc'
          ? `自动生成的测试集，每文档${payload.questionsPerDoc}题`
          : `自动生成的测试集，共${payload.numTotalQuestions}题`,
      metadata: {
        document_ids: payload.documentIds
      }
    })
    createdTestsetId.value = testSet.id
    progressInfo.stage = '开始生成'
    progressInfo.logs.push(
      payload.generationMode === 'multi_turn'
        ? '创建测试集成功，开始异步生成多轮 Case...'
        : '创建测试集成功，开始异步生成问题...'
    )

    const taskResponse = payload.generationMode === 'multi_turn'
      ? await testsetApi.generateConversationQuestions(testSet.id, {
          num_cases: payload.numCases,
          turn_range: payload.turnRange,
          case_type_ratio: payload.caseTypeRatio,
          document_ids: payload.documentIds
        })
      : await testsetApi.generateQuestionsAsync(testSet.id, {
          num_questions: payload.distributionMode === 'per_doc'
            ? payload.questionsPerDoc * payload.documentIds.length
            : payload.numTotalQuestions,
          generation_mode: 'advanced',
          enable_safety_robustness: payload.enableSafetyRobustness,
          document_ids: payload.documentIds,
          persona_list: personaList,
          distribution_mode: payload.distributionMode,
          questions_per_doc: payload.distributionMode === 'per_doc' ? payload.questionsPerDoc : undefined,
          question_types: payload.questionTypes.length > 0 ? payload.questionTypes.join(',') : undefined,
          multi_doc_ratio: payload.multiDocRatio,
        })
    const { task_id } = taskResponse
    saveGenerationSession(task_id, payload, testSet.id)
    
    taskStore.addTask({
      id: task_id,
      name: `${payload.generationMode === 'multi_turn' ? '生成多轮测试集' : '生成测试集'}: ${payload.name}`,
      type: 'testset',
      progress: 0,
      status: 'running',
      targetId: testSet.id
    })

    progressInfo.logs.push(`任务已创建: ${task_id}`)
    pollTaskStatus(task_id)
  } catch (error) {
    await cleanupCreatedTestset('已删除提交失败时创建的测试集')
    throw error
  }
}

const handleGenerate = async () => {
  const name = form.name.trim()
  if (!name) {
    ElMessage.warning('请输入测试集名称')
    return
  }
  if (form.documentIds.length === 0) {
    ElMessage.warning('请至少选择一个文档')
    return
  }
  if (!isConversationMode.value && form.personaJson.trim()) {
    try {
      JSON.parse(form.personaJson)
    } catch {
      ElMessage.error('人物画像JSON格式不正确')
      return
    }
  }

  const payload = {
    name,
    documentIds: [...form.documentIds],
    generationMode: form.generationMode,
    distributionMode: form.distributionMode,
    questionsPerDoc: form.questionsPerDoc,
    numTotalQuestions: form.numTotalQuestions,
    numCases: form.numCases,
    turnRange: [...form.turnRange] as [number, number],
    caseTypeRatio: {
      single_chunk_deep: Number((form.caseTypeRatioPercent.single_chunk_deep / 100).toFixed(4)),
      same_doc_chain: Number((form.caseTypeRatioPercent.same_doc_chain / 100).toFixed(4)),
      cross_doc_assoc: Number((form.caseTypeRatioPercent.cross_doc_assoc / 100).toFixed(4))
    },
    enableSafetyRobustness: form.enableRobustnessInputQuality || form.enableComplianceSafety,
    personaJson: isConversationMode.value ? '' : form.personaJson.trim(),
    questionTypes: Array.from(selectedMinors.value),
    multiDocRatio: form.multiDocRatio / 100
  }
  lastSubmitPayload.value = payload

  try {
    await submitGeneration(payload)
  } catch (error: any) {
    generating.value = false
    generationFailed.value = true
    const err = error?.response?.data?.detail || error?.message || '未知错误'
    progressInfo.stage = '生成失败'
    progressInfo.logs.push(`错误: ${err}`)
    ElNotification({
      title: '提交失败',
      message: `创建任务失败：${err}`,
      type: 'error'
    })
  }
}

const retryLastSubmit = async () => {
  if (!lastSubmitPayload.value) {
    ElMessage.warning('暂无可重试的参数，请先提交一次')
    return
  }
  try {
    await submitGeneration(lastSubmitPayload.value)
  } catch (error: any) {
    generating.value = false
    generationFailed.value = true
    const err = error?.response?.data?.detail || error?.message || '未知错误'
    progressInfo.stage = '生成失败'
    progressInfo.logs.push(`重试失败: ${err}`)
    ElMessage.error(`重试失败：${err}`)
  }
}

const resumeGeneration = async () => {
  const session = getSavedGenerationSession()
  if (!session) {
    ElMessage.warning('未找到可续传的任务会话，请使用"使用上次参数重试"重新生成')
    return
  }

  const { taskId, createdTestsetId: savedTestsetId, payload } = session

  try {
    // 调用后端断点续传接口
    const result = await taskApi.resumeTask(taskId)

    // 恢复前端状态
    applySavedPayloadToForm(payload)
    createdTestsetId.value = savedTestsetId
    resultMode.value = payload.generationMode
    generating.value = true
    generationFailed.value = false
    generatedQuestions.value = []
    generatedConversationCaseCount.value = 0
    progressInfo.total = getExpectedTotalFromPayload(payload)
    progressInfo.stage = result.message || '断点续传中...'
    progressInfo.logs.push(`断点续传: 任务 ${taskId} 已恢复`)

    // 更新全局任务栏
    taskStore.updateTask(taskId, {
      status: 'pending',
      progress: Math.round((result.progress || 0) * 100),
      message: result.message,
      error: undefined
    })

    // 开始轮询
    pollTaskStatus(taskId)

    ElMessage.success('已从断点继续生成')
  } catch (error: any) {
    const err = error?.response?.data?.detail || error?.message || '未知错误'
    ElNotification({
      title: '续传失败',
      message: `无法从断点续传：${err}，可使用"使用上次参数重试"重新生成`,
      type: 'error'
    })
  }
}

const resetGenerationPage = (options?: { preserveSession?: boolean }) => {
  stopPolling()
  generating.value = false
  generationFailed.value = false
  createdTestsetId.value = null
  generatedQuestions.value = []
  generatedConversationCaseCount.value = 0
  resultMode.value = 'single_turn'
  lastSubmitPayload.value = null
  form.name = `测试集_${buildLocalNameStamp()}`
  form.documentIds = []
  form.generationMode = 'single_turn'
  form.questionsPerDoc = 10
  form.numCases = 5
  form.turnRange = [3, 5]
  form.caseTypeRatioPercent.single_chunk_deep = 20
  form.caseTypeRatioPercent.same_doc_chain = 60
  form.caseTypeRatioPercent.cross_doc_assoc = 20
  form.enableRobustnessInputQuality = false
  form.enableComplianceSafety = false
  form.personaJson = ''
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = 0
  progressInfo.logs = []
  filterText.value = ''
  pickerSelectedCategories.value = []
  tempDocumentIds.value = []
  if (!options?.preserveSession) {
    clearGenerationSession()
  }
}

const applyRouteQuery = () => {
  const queryDocumentId = typeof route.query.document_id === 'string' ? route.query.document_id : ''
  const queryTestsetName = typeof route.query.testset_name === 'string' ? route.query.testset_name : ''
  if (queryDocumentId) {
    form.documentIds = [queryDocumentId]
  }
  if (queryTestsetName.trim()) {
    form.name = queryTestsetName.trim()
  }
}

const goToCreatedTestset = () => {
  if (!createdTestsetId.value) return
  const id = createdTestsetId.value
  resetGenerationPage()
  // replace 避免返回栈停留在旧的新建页状态
  router.replace(`/testsets/${id}`)
}

// 查看详情
const viewDetail = (row: any) => {
  currentQuestion.value = row
  detailDialogVisible.value = true
}

// 导出CSV
const exportCSV = () => {
  if (generatedQuestions.value.length === 0) {
    ElMessage.warning('没有可导出的数据')
    return
  }
  
  const docCategoryMap: Record<string, string> = {}
  for (const doc of documents.value) {
    docCategoryMap[doc.id] = doc.category || '未分类'
  }
  
  const parseCategoryLevels = (category: string): [string, string, string] => {
    if (!category || category === '未分类') return ['', '', '']
    const parts = category.split('/')
    if (parts.length >= 3) return [parts[0], parts[1], parts[2]]
    if (parts.length === 2) return [parts[0], parts[1], '']
    if (parts.length === 1) return [parts[0], '', '']
    return ['', '', '']
  }
  
  const getSourceDocument = (q: any): string => {
    const meta = q.metadata || {}
    const docIds = meta.doc_ids || meta.document_ids || []
    if (Array.isArray(docIds)) {
      for (const did of docIds) {
        const doc = documents.value.find(d => d.id === did)
        if (doc) return doc.filename || ''
      }
    }
    if (meta.doc_id) {
      const doc = documents.value.find(d => d.id === meta.doc_id)
      if (doc) return doc.filename || ''
    }
    if (meta.filename) return meta.filename
    if (meta.filenames && Array.isArray(meta.filenames)) return meta.filenames.join(' | ')
    return ''
  }
  
  const getCategoryForQuestion = (q: any): [string, string, string] => {
    const meta = q.metadata || {}
    const docIds = meta.doc_ids || meta.document_ids || []
    const ids = Array.isArray(docIds) ? docIds : []
    if (meta.doc_id) ids.push(meta.doc_id)
    for (const did of ids) {
      if (docCategoryMap[did]) return parseCategoryLevels(docCategoryMap[did])
    }
    if (form.documentIds.length > 0) {
      for (const did of form.documentIds) {
        if (docCategoryMap[did]) return parseCategoryLevels(docCategoryMap[did])
      }
    }
    return ['', '', '']
  }
  
  const headers = ['问题ID', '一级分类', '二级分类', '三级分类', '来源文档', '问题', '预期答案', '问题类型', '主要分类', '次要分类', '上下文']
  const rows = generatedQuestions.value.map(q => {
    const [level1, level2, level3] = getCategoryForQuestion(q)
    const sourceDoc = getSourceDocument(q)
    return [
      `"${(q.id || '').replace(/"/g, '""')}"`,
      `"${level1.replace(/"/g, '""')}"`,
      `"${level2.replace(/"/g, '""')}"`,
      `"${level3.replace(/"/g, '""')}"`,
      `"${sourceDoc.replace(/"/g, '""')}"`,
      `"${(q.question || '').replace(/"/g, '""')}"`,
      `"${((q.expected_answer || q.ground_truth) || '').replace(/"/g, '""')}"`,
      `"${(q.question_type || '').replace(/"/g, '""')}"`,
      `"${(q.category_major || '').replace(/"/g, '""')}"`,
      `"${(q.category_minor || '').replace(/"/g, '""')}"`,
      `"${(q.context || '').replace(/"/g, '""')}"`
    ]
  })
  
  const csvContent = [headers.join(','), ...rows].join('\n')
  
  const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  link.download = `测试集_${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}.csv`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('导出成功')
}

// 初始化
onMounted(async () => {
  initialLoading.value = true
  try {
    const response = await documentApi.getDocuments({ is_analyzed: true, limit: 1000 })
    documents.value = response.items || []
  } finally {
    initialLoading.value = false
  }

  await loadTaxonomy()
  const restored = await restoreGenerationSession()
  if (!restored) {
    resetGenerationPage()
    applyRouteQuery()
  }
})

onActivated(async () => {
  if (hasInMemoryGenerationState.value) return
  const restored = await restoreGenerationSession()
  if (!restored) {
    resetGenerationPage()
    applyRouteQuery()
  }
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style lang="scss" scoped>
.testset-generation-view {
  padding: 20px;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .config-card, .taxonomy-card, .progress-card, .result-card, .empty-card {
    height: 100%;
  }

  .config-form-wrapper {
    &.is-locked {
      pointer-events: none;
      opacity: 0.75;
      user-select: none;
    }

  }

  .document-picker-content {
    height: 68vh;
    display: flex;
    flex-direction: column;

    .picker-toolbar {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    :deep(.el-transfer) {
      display: flex;
      align-items: stretch;
      gap: 12px;
      width: 100%;
      flex: 1;
      min-height: 0;
    }

    :deep(.el-transfer-panel) {
      flex: 0 0 calc((100% - 120px) / 2);
      width: calc((100% - 120px) / 2);
      min-width: 0;
      height: 100%;
    }

    :deep(.el-transfer-panel__body) {
      height: calc(100% - 40px);
      display: flex;
      flex-direction: column;
    }

    :deep(.el-transfer-panel__list) {
      flex: 1;
    }

    :deep(.el-transfer__buttons) {
      flex: 0 0 96px;
      width: 96px;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      gap: 12px;
      background: #f8fafc;
      border-radius: 8px;
    }
  }

  .doc-picker-trigger {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .selected-doc-preview {
    margin-top: 6px;
    font-size: 12px;
    color: #909399;
    line-height: 1.4;
  }

  .form-help {
    font-size: 12px;
    color: #909399;
    margin-top: 4px;
    line-height: 1.4;
  }

  .conversation-slider-wrapper {
    width: 100%;
  }

  .conversation-ratio-grid {
    width: 100%;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }

  .ratio-item {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .ratio-label {
    font-size: 13px;
    color: #606266;
  }
  
  .mt-10 {
    margin-top: 10px;
  }
  
  .mt-20 {
    margin-top: 20px;
  }
  
  .ml-10 {
    margin-left: 10px;
  }
  
  .taxonomy-preview {
    max-height: 520px;
    overflow-y: auto;
    
    .taxonomy-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 10px;
      
      .selected-count {
        font-size: 12px;
        color: #909399;
      }
    }
    
    .taxonomy-major {
      font-weight: 600;
    }
    
    .minor-list {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      
      .minor-tag {
        margin: 2px;
        cursor: pointer;
        transition: all 0.2s;
        user-select: none;
        
        &:hover {
          opacity: 0.8;
        }
      }
      
      .minor-tag-selected {
        box-shadow: 0 0 0 1px var(--el-color-primary);
      }
    }
  }
  
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
      max-height: 150px;
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
  
  .question-detail {
    pre {
      background: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
      font-size: 12px;
    }
  }
}
</style>
