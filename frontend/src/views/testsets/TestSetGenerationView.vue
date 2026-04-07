<template>
  <div class="testset-generation-view">
    <el-row :gutter="20">
      <!-- 左侧：参数配置 -->
      <el-col :span="12">
        <el-card class="config-card">
          <template #header>
            <div class="card-header">
              <span>测试集生成配置</span>
            </div>
          </template>
          
          <el-form :model="form" label-width="140px" style="max-width: 600px;">
            <!-- 文档选择 -->
            <el-form-item label="选择文档" required>
              <el-select 
                v-model="form.documentIds" 
                multiple
                placeholder="请选择要生成测试集的文档"
                style="width: 100%;"
                filterable
              >
                <el-option
                  v-for="doc in analyzedDocuments"
                  :key="doc.id"
                  :label="doc.filename"
                  :value="doc.id"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="按分类选择">
              <el-space wrap style="width: 100%;">
                <el-select
                  v-model="selectedCategory"
                  placeholder="选择文档分类"
                  clearable
                  style="width: 260px;"
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
                <el-button text @click="clearDocumentSelection">清空已选文档</el-button>
              </el-space>
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
            
            <!-- 是否启用安全/鲁棒性问题 -->
            <el-form-item label="安全与鲁棒性">
              <el-switch 
                v-model="form.enableSafetyRobustness"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-help">启用后将生成安全合规与输入质量类问题</div>
            </el-form-item>
            
            <!-- 人物画像配置 -->
            <el-form-item label="人物画像配置">
              <el-switch 
                v-model="form.enablePersona"
                active-text="启用"
                inactive-text="禁用"
              />
              <div class="form-help">启用后将根据人物画像生成更贴合角色的问题</div>
            </el-form-item>
            
            <!-- 人物画像JSON -->
            <el-form-item v-if="form.enablePersona" label="人物画像JSON">
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
            
            <el-divider content-position="left">问题分类体系预览</el-divider>
            
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
          </el-form>
        </el-card>
      </el-col>
      
      <!-- 右侧：生成进度和结果 -->
      <el-col :span="12">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElNotification } from 'element-plus'
import { useDocumentStore } from '@/stores/document'
import { useTestSetStore } from '@/stores/testset'
import { testsetApi } from '@/api/testsets'

// 文档存储
const documentStore = useDocumentStore()
const testSetStore = useTestSetStore()

// 表单数据
const form = reactive({
  documentIds: [] as string[],
  questionsPerDoc: 10,
  enableSafetyRobustness: true,
  enablePersona: false,
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
  documentStore.documents.filter(doc => doc.is_analyzed)
)
const selectedCategory = ref('')
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

const selectDocumentsByCategory = (replaceSelection: boolean) => {
  if (!selectedCategory.value) {
    ElMessage.warning('请先选择文档分类')
    return
  }
  const targetIds = analyzedDocuments.value
    .filter(doc => normalizeCategory(doc) === selectedCategory.value)
    .map(doc => doc.id)
  if (targetIds.length === 0) {
    ElMessage.warning(`分类“${selectedCategory.value}”下没有可用文档`)
    return
  }

  if (replaceSelection) {
    form.documentIds = targetIds
  } else {
    form.documentIds = Array.from(new Set([...form.documentIds, ...targetIds]))
  }
  ElMessage.success(`已选中分类“${selectedCategory.value}”下 ${targetIds.length} 个文档`)
}

const clearDocumentSelection = () => {
  form.documentIds = []
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
const handleGenerate = async () => {
  if (form.documentIds.length === 0) {
    ElMessage.warning('请至少选择一个文档')
    return
  }
  
  // 解析人物画像
  let personaList: any[] = []
  if (form.enablePersona && form.personaJson) {
    try {
      personaList = JSON.parse(form.personaJson)
    } catch (e) {
      ElMessage.error('人物画像JSON格式不正确')
      return
    }
  }
  
  generating.value = true
  generationFailed.value = false
  generatedQuestions.value = []
  progressInfo.stage = '准备中'
  progressInfo.current = 0
  progressInfo.total = form.documentIds.length * form.questionsPerDoc
  progressInfo.logs = []
  
  try {
    // 创建测试集
    const testSet = await testSetStore.createTestSet({
      document_id: form.documentIds[0],
      name: `测试集_${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}`,
      description: `自动生成的测试集，包含${form.questionsPerDoc}个问题/文档`
    })
    
    createdTestsetId.value = testSet.id
    progressInfo.stage = '开始生成'
    progressInfo.logs.push('创建测试集成功，开始生成问题...')
    
    // 逐个文档生成问题
    for (let i = 0; i < form.documentIds.length; i++) {
      const docId = form.documentIds[i]
      progressInfo.stage = `处理文档 ${i + 1}/${form.documentIds.length}`
      progressInfo.logs.push(`开始处理文档 ${i + 1}...`)
      
      try {
        // 调用生成API
        const result = await testsetApi.generateQuestions(testSet.id, {
          num_questions: form.questionsPerDoc,
          generation_mode: 'advanced',
          enable_safety_robustness: form.enableSafetyRobustness
        })
        
        if (result.questions && result.questions.length > 0) {
          // 添加到结果中
          for (const q of result.questions) {
            generatedQuestions.value.push({
              ...q,
              passed: true
            })
            progressInfo.current++
          }
          progressInfo.logs.push(`文档 ${i + 1} 生成完成，获得 ${result.questions.length} 个问题`)
        }
      } catch (error: any) {
        console.error(`文档 ${i + 1} 生成失败:`, error)
        progressInfo.logs.push(`文档 ${i + 1} 生成失败: ${error?.response?.data?.detail || error?.message || '未知错误'}`)
      }
    }
    
    progressInfo.stage = '生成完成'
    progressInfo.logs.push(`所有文档处理完成，共生成 ${generatedQuestions.value.length} 个问题`)
    
    // 判断是否生成成功
    if (generatedQuestions.value.length === 0) {
      generationFailed.value = true
      progressInfo.stage = '生成失败'
      progressInfo.logs.push('未能生成任何问题，测试集创建失败')
      
      // 删除已创建的空测试集
      if (createdTestsetId.value) {
        try {
          await testsetApi.deleteTestSet(createdTestsetId.value)
          progressInfo.logs.push('已删除创建的空测试集')
        } catch (deleteError) {
          console.error('删除空测试集失败:', deleteError)
        }
        createdTestsetId.value = null
      }
      
      ElNotification({
        title: '生成失败',
        message: '未能生成任何问题，请检查LLM配置是否正确（DASHSCOPE_API_KEY或QWEN_API_KEY）',
        type: 'error'
      })
    } else {
      ElNotification({
        title: '生成完成',
        message: `成功生成 ${generatedQuestions.value.length} 个测试问题`,
        type: 'success'
      })
    }
    
  } catch (error: any) {
    console.error('生成测试集失败:', error)
    generationFailed.value = true
    ElMessage.error(error?.response?.data?.detail || error?.message || '生成测试集失败')
    progressInfo.stage = '生成失败'
    progressInfo.logs.push(`错误: ${error?.response?.data?.detail || error?.message || '未知错误'}`)
  } finally {
    generating.value = false
  }
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
  link.download = `测试集_${new Date().toISOString().slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
  
  ElMessage.success('导出成功')
}

// 初始化
onMounted(async () => {
  documentStore.pagination.page = 1
  documentStore.pagination.size = 1000
  await documentStore.fetchDocuments({ is_analyzed: true })
  await loadTaxonomy()
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
  
  .config-card, .progress-card, .result-card, .empty-card {
    height: 100%;
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
    max-height: 300px;
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
