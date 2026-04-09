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
        <el-form-item label="评估指标">
          <el-checkbox-group v-model="form.evaluation_metrics">
            <el-checkbox value="answer_relevance">答案相关性</el-checkbox>
            <el-checkbox value="context_relevance">上下文相关性</el-checkbox>
            <el-checkbox value="faithfulness">忠实度</el-checkbox>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { testsetApi } from '@/api/testsets'
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
  evaluation_metrics: ['answer_relevance', 'faithfulness']
})

const rules: FormRules = {
  testset_id: [{ required: true, message: '请选择测试集', trigger: 'change' }],
  evaluation_method: [{ required: true, message: '请选择评估方法', trigger: 'change' }]
}

const evaluableTestsets = computed(() => testsets.value.filter(item => item.can_evaluate))

const fetchTestsets = async () => {
  try {
    const response = await testsetApi.getTestSets({ limit: 1000 })
    testsets.value = response.items
  } catch {
    ElMessage.error('获取测试集列表失败')
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
  await fetchTestsets()
  applyRoutePrefill()
})
</script>
