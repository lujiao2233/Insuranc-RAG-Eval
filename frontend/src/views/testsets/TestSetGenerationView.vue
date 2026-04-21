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
            <el-divider content-position="left">生成参数</el-divider>
            
            <!-- 问题数量 -->
            <el-form-item label="每个文档问题数">
              <el-input-number 
                v-model="form.questionsPerDoc" 
                :min="1" 
                :max="50"
                style="width: 100%;"
              />
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
                {{ generating ? `生成中... (${progressInfo.current}/${progressInfo.total})` : '开始生成测试集' }}
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
          </div>
        </el-card>
      </el-col>
      
      <!-- 下方：生成进度和结果 -->
      <el-col :span="24" class="mt-20">
        <!-- 生成进度 -->
        <el-card v-if="generating || generatedQuestions.length > 0" class="progress-card">
          <template #header>
            <div class="card-header">
              <span>生成进度</span>
              <el-button v-if="generatedQuestions.length > 0" text @click="exportCSV">
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
                <el-statistic title="总问题数" :value="generatedQuestions.length" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="来源文档数" :value="form.documentIds.length" />
              </el-col>
              <el-col :span="8">
                <el-statistic title="状态" :value="generatedQuestions.length > 0 ? '已完成' : '生成失败'" />
              </el-col>
            </el-row>
          </div>
        </el-card>
        
        <!-- 生成结果表格 -->
        <el-card v-if="generatedQuestions.length > 0" class="result-card mt-20">
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
        <el-card v-if="!generating && generatedQuestions.length === 0 && progressInfo.logs.length === 0" class="empty-card">
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
          <el-select
            v-model="pickerSelectedCategory"
            placeholder="按分类选择"
            clearable
            style="width: 240px;"
          >
            <el-option
              v-for="category in documentCategories"
              :key="category"
              :label="`${category}（${categoryDocCountMap[category] || 0}）`"
              :value="category"
            />
          </el-select>
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
import { documentApi } from '@/api/documents'
import { useTaskStore } from '@/stores/task'

const router = useRouter()
const route = useRoute()
const taskStore = useTaskStore()

const buildLocalNameStamp = () => {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`
}

// 表单数据
const form = reactive({
  name: `测试集_${buildLocalNameStamp()}`,
  documentIds: [] as string[],
  questionsPerDoc: 10,
  enableRobustnessInputQuality: false,
  enableComplianceSafety: false,
  personaJson: ''
})

// 分类体系
const taxonomy = ref<Array<{major: string, minors: string[]}>>([])

// 状态
const generating = ref(false)
const generationFailed = ref(false)
const createdTestsetId = ref<string | null>(null)
const generatedQuestions = ref<any[]>([])
const filterText = ref('')
const initialLoading = ref(false)
const documents = ref<any[]>([])
const lastSubmitPayload = ref<null | {
  name: string
  documentIds: string[]
  questionsPerDoc: number
  enableSafetyRobustness: boolean
  personaJson: string
}>(null)
let pollingTimer: number | null = null

// 进度信息
const progressInfo = reactive({
  stage: '准备中',
  current: 0,
  total: 0,
  logs: [] as string[]
})

// 进度百分比
const progressPercentage = computed(() => {
  if (progressInfo.total === 0) return 0
  return Math.round((progressInfo.current / progressInfo.total) * 100)
})

// 进度状态
const progressStatus = computed(() => {
  if (generationFailed.value) return 'exception'
  if (!generating.value && generatedQuestions.value.length === 0 && progressInfo.logs.length > 0) return 'exception'
  if (progressPercentage.value >= 100 && generatedQuestions.value.length > 0) return 'success'
  if (progressPercentage.value > 0) return ''
  return 'exception'
})

const generationSucceeded = computed(() =>
  !generating.value &&
  !generationFailed.value &&
  !!createdTestsetId.value &&
  generatedQuestions.value.length > 0
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
  documents.value.filter((doc: any) => doc.is_analyzed)
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
const pickerSelectedCategory = ref('')
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
  pickerSelectedCategory.value = ''
  documentPickerVisible.value = true
}
const confirmDocumentPicker = () => {
  form.documentIds = [...tempDocumentIds.value]
  documentPickerVisible.value = false
}
const cancelDocumentPicker = () => {
  pickerSelectedCategory.value = ''
  documentPickerVisible.value = false
}
const normalizeCategory = (doc: any) => String(doc?.category || '').trim() || '未分类'
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

const selectPickerDocumentsByCategory = (replaceSelection: boolean) => {
  if (!pickerSelectedCategory.value) {
    ElMessage.warning('请先选择文档分类')
    return
  }
  const targetIds = analyzedDocuments.value
    .filter(doc => normalizeCategory(doc) === pickerSelectedCategory.value)
    .map(doc => doc.id)
  if (targetIds.length === 0) {
    ElMessage.warning(`分类“${pickerSelectedCategory.value}”下没有可用文档`)
    return
  }

  if (replaceSelection) {
    tempDocumentIds.value = targetIds
  } else {
    tempDocumentIds.value = Array.from(new Set([...tempDocumentIds.value, ...targetIds]))
  }
  ElMessage.success(`已选中分类“${pickerSelectedCategory.value}”下 ${targetIds.length} 个文档`)
}

const clearPickerDocumentSelection = () => {
  tempDocumentIds.value = []
}

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
}

// 生成测试集
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

const pollTaskStatus = (taskId: string) => {
  let lastLogIndex = 0
  const poll = async () => {
    try {
      const task = await testsetApi.getTaskStatus(taskId)
      progressInfo.stage = task.message || task.status

      if (typeof task.total_steps === 'number' && task.total_steps > 0) {
        progressInfo.total = task.total_steps
      }
      if (typeof task.current_step === 'number') {
        progressInfo.current = Math.max(progressInfo.current, task.current_step)
      }

      if (typeof task.progress === 'number' && progressInfo.total > 0) {
        const currentByProgress = Math.round(task.progress * progressInfo.total)
        if (currentByProgress > progressInfo.current) {
          progressInfo.current = currentByProgress
        }
      }

      // 更新全局任务状态
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
        progressInfo.current = progressInfo.total
        progressInfo.stage = '生成完成'
        
        // 更新全局任务为完成
        taskStore.updateTask(taskId, {
          progress: 100,
          status: 'completed'
        })

        ElNotification({
          title: '生成成功',
          message: `已生成 ${generatedQuestions.value.length} 个问题，请点击“查看测试集详情”继续`,
          type: 'success'
        })
        return
      }

      if (task.status === 'cancelled') {
        stopPolling()
        generating.value = false
        generationFailed.value = true
        progressInfo.stage = '生成已取消'
        taskStore.removeTask(taskId)
        progressInfo.logs.push(task.message || '任务已取消')
        await cleanupCreatedTestset('已删除已取消任务创建的测试集')
        ElNotification({
          title: '任务已取消',
          message: task.message || '测试集生成已取消',
          type: 'warning'
        })
        return
      }

      if (task.status === 'failed') {
        stopPolling()
        generating.value = false
        generationFailed.value = true
        progressInfo.stage = '生成失败'
        
        taskStore.removeTask(taskId)

        const err = task.error || '未知错误'
        progressInfo.logs.push(`错误: ${err}`)
        await cleanupCreatedTestset('已删除失败任务创建的测试集')
        ElNotification({
          title: '生成失败',
          message: `任务执行失败：${err}，可直接点击“使用上次参数重试”`,
          type: 'error'
        })
      }
    } catch (error: any) {
      stopPolling()
      generating.value = false
      generationFailed.value = true
      progressInfo.stage = '生成失败'
      
      taskStore.removeTask(taskId)

      const err = error?.response?.data?.detail || error?.message || '网络异常'
      progressInfo.logs.push(`轮询失败: ${err}`)
      await cleanupCreatedTestset('已删除轮询失败任务创建的测试集')
      ElNotification({
        title: '网络异常',
        message: `状态轮询失败：${err}，请重试`,
        type: 'error'
      })
    }
  }

  poll()
  pollingTimer = window.setInterval(poll, 2000)
}

const submitGeneration = async (payload: {
  name: string
  documentIds: string[]
  questionsPerDoc: number
  enableSafetyRobustness: boolean
  personaJson: string
}) => {
  generating.value = true
  generationFailed.value = false
  generatedQuestions.value = []
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = payload.documentIds.length * payload.questionsPerDoc
  progressInfo.logs = []

  try {
    let personaList: any[] = []
    if (payload.personaJson) {
      personaList = JSON.parse(payload.personaJson)
    }

    const testSet = await testsetApi.createTestSet({
      document_id: payload.documentIds[0],
      name: payload.name,
      description: `自动生成的测试集，包含${payload.questionsPerDoc}个问题/文档`
    })
    createdTestsetId.value = testSet.id
    progressInfo.stage = '开始生成'
    progressInfo.logs.push('创建测试集成功，开始异步生成问题...')

    const { task_id } = await testsetApi.generateQuestionsAsync(testSet.id, {
      num_questions: payload.questionsPerDoc * payload.documentIds.length,
      generation_mode: 'advanced',
      enable_safety_robustness: payload.enableSafetyRobustness,
      document_ids: payload.documentIds,
      persona_list: personaList
    })
    
    taskStore.addTask({
      id: task_id,
      name: `生成测试集: ${payload.name}`,
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
  if (form.personaJson.trim()) {
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
    questionsPerDoc: form.questionsPerDoc,
    enableSafetyRobustness: form.enableRobustnessInputQuality || form.enableComplianceSafety,
    personaJson: form.personaJson.trim()
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

const resetGenerationPage = () => {
  stopPolling()
  generating.value = false
  generationFailed.value = false
  createdTestsetId.value = null
  generatedQuestions.value = []
  lastSubmitPayload.value = null
  form.name = `测试集_${buildLocalNameStamp()}`
  form.documentIds = []
  form.questionsPerDoc = 10
  form.enableRobustnessInputQuality = false
  form.enableComplianceSafety = false
  form.personaJson = ''
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = 0
  progressInfo.logs = []
  filterText.value = ''
  pickerSelectedCategory.value = ''
  tempDocumentIds.value = []
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
  
  // 构建CSV内容
  const headers = ['问题', '预期答案', '问题类型', '主要分类', '次要分类', '上下文']
  const rows = generatedQuestions.value.map(q => [
    `"${(q.question || '').replace(/"/g, '""')}"`,
    `"${((q.expected_answer || q.ground_truth) || '').replace(/"/g, '""')}"`,
    `"${(q.question_type || '').replace(/"/g, '""')}"`,
    `"${(q.category_major || '').replace(/"/g, '""')}"`,
    `"${(q.category_minor || '').replace(/"/g, '""')}"`,
    `"${(q.context || '').replace(/"/g, '""')}"`
  ])
  
  const csvContent = [headers.join(','), ...rows].join('\n')
  
  // 下载
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

  resetGenerationPage()
  applyRouteQuery()
  await loadTaxonomy()
})

onActivated(() => {
  // keepAlive 场景：每次进入新建页默认重置，再按路由参数预填
  resetGenerationPage()
  applyRouteQuery()
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
    
    .taxonomy-major {
      font-weight: 600;
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
