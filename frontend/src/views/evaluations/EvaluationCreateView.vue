<template>
  <div class="evaluation-create-view">
    <el-page-header @back="$router.push('/evaluations')">
      <template #content>
        <span class="text-large font-600">新建评估</span>
      </template>
    </el-page-header>
    <el-divider />

    <el-card>
      <template #header>
        <span>评估配置</span>
      </template>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" style="max-width: 720px;">
        <el-form-item label="测试集" prop="testset_id">
          <el-select v-model="form.testset_id" filterable placeholder="请选择测试集" style="width: 100%">
            <el-option
              v-for="item in evaluableTestsets"
              :key="item.id"
              :label="`${item.name}（${item.answered_questions || 0}/${item.question_count || 0}）`"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="评估方法" prop="evaluation_method">
          <el-select v-model="form.evaluation_method" style="width: 100%">
            <el-option label="RAGAS官方" value="ragas_official" />
            <el-option label="DeepEval" value="deepeval" />
          </el-select>
        </el-form-item>
        <el-form-item label="评估指标" class="vertical-form-item">
          <el-checkbox-group v-model="form.evaluation_metrics" class="metric-categories">
            <div v-for="group in metricOptions" :key="group.category" class="metric-category">
              <div class="category-title">{{ group.category }}</div>
              <el-checkbox
                v-for="metric in group.items"
                :key="metric.value"
                :value="metric.value"
                :disabled="['context_relevance', 'context_precision', 'faithfulness', 'hallucination'].includes(metric.value)"
              >
                {{ metric.label }}
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item>
          <el-button @click="$router.push('/evaluations')">取消</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">开始评估</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { testsetApi } from '@/api/testsets'
import { configApi } from '@/api/config'
import { useEvaluationStore } from '@/stores/evaluation'
import { useTaskStore } from '@/stores/task'
import type { TestSet } from '@/types'
import type { FormInstance, FormRules } from 'element-plus'

const route = useRoute()
const router = useRouter()
const evaluationStore = useEvaluationStore()
const taskStore = useTaskStore()

const creating = ref(false)
const formRef = ref<FormInstance>()
const testsets = ref<TestSet[]>([])

const form = reactive({
  testset_id: '',
  evaluation_method: 'ragas_official',
  evaluation_metrics: ['answer_relevance', 'context_relevance', 'context_precision', 'faithfulness', 'answer_correctness']
})

const rules: FormRules = {
  testset_id: [{ required: true, message: '请选择测试集', trigger: 'change' }],
  evaluation_method: [{ required: true, message: '请选择评估方法', trigger: 'change' }]
}

const evaluableTestsets = computed(() => testsets.value.filter(item => item.can_evaluate))

const ragasMetricCatalog = [
  {
    category: '检索类',
    items: [
      { value: 'context_relevance', label: '检索相关性' },
      { value: 'context_precision', label: '检索精确性' }
    ]
  },
  {
    category: '生成类',
    items: [
      { value: 'answer_relevance', label: '答案相关性' },
      { value: 'answer_correctness', label: '答案正确性' },
      { value: 'answer_similarity', label: '答案相似度' },
      { value: 'faithfulness', label: '忠实度' }
    ]
  }
]

const deepevalMetricCatalog = [
  {
    category: '检索类',
    items: [
      { value: 'context_relevance', label: '检索相关性' },
      { value: 'context_precision', label: '检索精确性' }
    ]
  },
  {
    category: '生成类',
    items: [
      { value: 'answer_relevance', label: '答案相关性' },
      { value: 'answer_correctness', label: '答案正确性' },
      { value: 'faithfulness', label: '忠实度' },
      { value: 'hallucination', label: '幻觉检测' }
    ]
  },
  {
    category: '安全类',
    items: [
      { value: 'toxicity', label: '有害言论检测' },
      { value: 'bias', label: '偏见检测' }
    ]
  }
]

const enabledRagasMetrics = ref<string[]>(['answer_relevance', 'context_relevance', 'context_precision', 'faithfulness', 'answer_correctness'])
const enabledDeepevalMetrics = ref<string[]>(['answer_relevance', 'context_relevance', 'context_precision', 'faithfulness', 'answer_correctness', 'toxicity', 'bias'])

const filterCatalogByEnabled = (
  catalog: Array<{ category: string; items: Array<{ value: string; label: string }> }>,
  enabled: string[]
) => {
  const enabledSet = new Set(enabled)
  return catalog.map(group => ({
    category: group.category,
    items: group.items.filter(item => enabledSet.has(item.value))
  })).filter(group => group.items.length > 0)
}

const metricOptions = computed(() => {
  return form.evaluation_method === 'deepeval'
    ? filterCatalogByEnabled(deepevalMetricCatalog, enabledDeepevalMetrics.value)
    : filterCatalogByEnabled(ragasMetricCatalog, enabledRagasMetrics.value)
})

const getEnabledMetricsByMethod = (method: string) => {
  return method === 'deepeval' ? enabledDeepevalMetrics.value : enabledRagasMetrics.value
}

watch(
  () => form.evaluation_method,
  (method) => {
    form.evaluation_metrics = [...getEnabledMetricsByMethod(method)]
  }
)

const fetchTestsets = async () => {
  try {
    const response = await testsetApi.getTestSets({ limit: 1000 })
    testsets.value = response.items
  } catch {
    ElMessage.error('获取测试集列表失败')
  }
}

const fetchEvaluationMetricConfig = async () => {
  try {
    const { configs } = await configApi.getEvaluationConfig()
    if (Array.isArray(configs['evaluation.ragas_metrics'])) {
      enabledRagasMetrics.value = configs['evaluation.ragas_metrics'].map((x: any) => String(x))
    }
    if (Array.isArray(configs['evaluation.deepeval_metrics'])) {
      enabledDeepevalMetrics.value = configs['evaluation.deepeval_metrics'].map((x: any) => String(x))
    }
    form.evaluation_metrics = [...getEnabledMetricsByMethod(form.evaluation_method)]
  } catch {
    ElMessage.warning('读取评估指标配置失败，使用默认指标')
  }
}

const applyRoutePrefill = () => {
  const testsetId = typeof route.query.testset_id === 'string' ? route.query.testset_id : ''
  if (testsetId) {
    form.testset_id = testsetId
  }
}

const handleCreate = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    if (!form.evaluation_metrics.length) {
      ElMessage.warning('当前评估方法未启用任何指标，请先到系统配置中勾选并保存')
      return
    }

    creating.value = true
    try {
      const result = await evaluationStore.createEvaluation({
        testset_id: form.testset_id,
        evaluation_method: form.evaluation_method,
        evaluation_metrics: form.evaluation_metrics
      })

      const testsetName = testsets.value.find(t => t.id === form.testset_id)?.name || form.testset_id
      taskStore.addTask({
        id: result.task_id || result.id,
        name: `评估: ${testsetName}`,
        type: 'evaluation',
        progress: 0,
        status: 'running',
        targetId: result.id
      })

      ElMessage.success('评估任务已创建')
      router.push(`/evaluations/${result.id}`)
    } catch {
      ElMessage.error('创建评估失败')
    } finally {
      creating.value = false
    }
  })
}

onMounted(async () => {
  await fetchEvaluationMetricConfig()
  await fetchTestsets()
  applyRoutePrefill()
})
</script>

<style scoped>
.metric-categories {
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%;
}

.metric-category {
  display: flex;
  flex-direction: column;
  background-color: var(--bg-2, #f8f9fa);
  padding: 12px 16px;
  border-radius: 4px;
}

.category-title {
  font-size: 13px;
  color: var(--text-2, #606266);
  font-weight: 600;
  margin-bottom: 8px;
}

.metric-category .el-checkbox {
  margin-right: 24px;
  margin-bottom: 4px;
}

.vertical-form-item {
  flex-direction: column;
  align-items: flex-start;
}

.vertical-form-item :deep(.el-form-item__label) {
  width: 100% !important;
  text-align: left;
  justify-content: flex-start;
  margin-bottom: 8px;
}

.vertical-form-item :deep(.el-form-item__content) {
  margin-left: 0 !important;
  width: 100%;
}
</style>
