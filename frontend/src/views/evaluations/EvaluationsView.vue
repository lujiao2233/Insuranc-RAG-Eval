<template>
  <div class="evaluations-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>评估管理</span>
          <el-button type="primary" @click="showUploadDialog = true">
            <el-icon><Plus /></el-icon>
            上传测试集
          </el-button>
        </div>
      </template>

      <div class="filter-bar">
        <el-input
          v-model="keyword"
          placeholder="搜索测试集名称"
          clearable
          style="width: 260px;"
        />
        <el-select v-model="availabilityFilter" placeholder="评估状态" clearable style="width: 160px;">
          <el-option label="全部" value="" />
          <el-option label="已评估" value="evaluated" />
          <el-option label="可评估" value="evaluable" />
          <el-option label="不可评估" value="not_evaluable" />
        </el-select>
      </div>

      <el-table v-loading="loading" :data="filteredTestsets" style="width: 100%">
        <el-table-column prop="name" label="测试集名称" min-width="220" />
        <el-table-column prop="question_count" label="问题数" width="90" />
        <el-table-column label="模型答案" width="140">
          <template #default="{ row }">
            {{ row.answered_questions || 0 }} / {{ row.question_count || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="评估状态" width="120">
          <template #default="{ row }">
            <el-tag v-if="row.eval_status === 'evaluated'" type="info">
              已评估
            </el-tag>
            <el-tag v-else-if="row.eval_status === 'evaluable'" type="success">
              可评估
            </el-tag>
            <el-tag v-else type="warning">
              不可评估
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
              <el-button
                type="success"
                size="small"
                class="fixed-width-btn"
                :disabled="!row.can_evaluate"
                @click="openEvaluateDialog(row)"
              >
                评估
              </el-button>
            </div>
            <div class="button-row">
              <el-button type="warning" size="small" class="fixed-width-btn" @click="handleExport(row)">
                导出
              </el-button>
              <el-button type="danger" size="small" class="fixed-width-btn" @click="handleDelete(row)">
                删除
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showUploadDialog" title="上传测试集" width="560px">
      <el-form :model="uploadForm" label-width="100px">
        <el-form-item label="CSV文件" required>
          <el-upload
            :auto-upload="false"
            :limit="1"
            accept=".csv"
            :on-change="handleUploadFileChange"
            :on-remove="handleUploadFileRemove"
          >
            <el-button type="primary">选择CSV文件</el-button>
            <template #tip>
              <div class="el-upload__tip">
                兼容中英文字段：`问题/ question`；推荐包含 `模型答案/ model_answer` 以支持直接评估
              </div>
            </template>
          </el-upload>
        </el-form-item>
        <el-form-item label="测试集名称">
          <el-input v-model="uploadForm.name" placeholder="不填则自动命名" />
        </el-form-item>
        <el-form-item label="测试集描述">
          <el-input v-model="uploadForm.description" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showUploadDialog = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleImportTestset">上传</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEvaluateDialog" title="评估配置" width="520px">
      <el-form ref="evaluateFormRef" :model="evaluateForm" :rules="evaluateRules" label-width="100px">
        <el-form-item label="测试集">
          <el-input :model-value="currentTestsetName" disabled />
        </el-form-item>
        <el-form-item label="评估方法" prop="evaluation_method">
          <el-select v-model="evaluateForm.evaluation_method" style="width: 100%">
            <el-option label="RAGAS官方" value="ragas_official" />
            <el-option label="DeepEval" value="deepeval" />
          </el-select>
        </el-form-item>
        <el-form-item label="评估指标">
          <el-checkbox-group v-model="evaluateForm.evaluation_metrics">
            <el-checkbox value="answer_relevance">答案相关性</el-checkbox>
            <el-checkbox value="context_relevance">上下文相关性</el-checkbox>
            <el-checkbox value="faithfulness">忠实度</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEvaluateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creatingEvaluation" @click="handleCreateEvaluation">
          开始评估
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { testsetApi } from '@/api/testsets'
import { useEvaluationStore } from '@/stores/evaluation'
import { formatDateTime } from '@/utils/format'
import type { TestSet } from '@/types'
import type { FormInstance, FormRules, UploadFile } from 'element-plus'

const router = useRouter()
const evaluationStore = useEvaluationStore()

const loading = ref(false)
const testsets = ref<TestSet[]>([])
const keyword = ref('')
const availabilityFilter = ref('')

const showUploadDialog = ref(false)
const uploading = ref(false)
const uploadForm = reactive({
  file: null as File | null,
  name: '',
  description: ''
})

const showEvaluateDialog = ref(false)
const creatingEvaluation = ref(false)
const currentTestsetId = ref('')
const currentTestsetName = ref('')
const evaluateFormRef = ref<FormInstance>()
const evaluateForm = reactive({
  evaluation_method: 'ragas_official',
  evaluation_metrics: ['answer_relevance', 'faithfulness']
})
const evaluateRules: FormRules = {
  evaluation_method: [{ required: true, message: '请选择评估方法', trigger: 'change' }]
}

const isUploadedTestset = (testset: TestSet) => {
  return testset.generation_method === 'csv_import' || Boolean(testset.metadata?.imported)
}

const filteredTestsets = computed(() => {
  let result = [...testsets.value]
  const query = keyword.value.trim().toLowerCase()

  if (query) {
    result = result.filter(item => item.name.toLowerCase().includes(query))
  }
  if (availabilityFilter.value) {
    result = result.filter(item => item.eval_status === availabilityFilter.value)
  }
  return result
})

const fetchTestsets = async () => {
  loading.value = true
  try {
    const response = await testsetApi.getTestSets({ limit: 1000 })
    testsets.value = response.items.filter(item => isUploadedTestset(item))
  } catch (error) {
    ElMessage.error('获取测试集列表失败')
  } finally {
    loading.value = false
  }
}

const handleUploadFileChange = (file: UploadFile) => {
  uploadForm.file = (file.raw as File) || null
}

const handleUploadFileRemove = () => {
  uploadForm.file = null
}

const handleImportTestset = async () => {
  if (!uploadForm.file) {
    ElMessage.warning('请先选择CSV文件')
    return
  }
  uploading.value = true
  try {
    await testsetApi.importTestSetCsv({
      file: uploadForm.file,
      name: uploadForm.name || undefined,
      description: uploadForm.description || undefined
    })
    ElMessage.success('测试集上传成功')
    showUploadDialog.value = false
    uploadForm.file = null
    uploadForm.name = ''
    uploadForm.description = ''
    await fetchTestsets()
  } catch (error) {
    ElMessage.error('测试集上传失败')
  } finally {
    uploading.value = false
  }
}

const viewTestset = (id: string) => {
  router.push(`/testsets/${id}`)
}

const openEvaluateDialog = (testset: TestSet) => {
  if (!testset.can_evaluate) {
    ElMessage.warning('该测试集缺少模型答案，暂不可评估')
    return
  }
  currentTestsetId.value = testset.id
  currentTestsetName.value = testset.name
  showEvaluateDialog.value = true
}

const handleCreateEvaluation = async () => {
  if (!evaluateFormRef.value || !currentTestsetId.value) return
  await evaluateFormRef.value.validate(async (valid) => {
    if (!valid) return
    creatingEvaluation.value = true
    try {
      const result = await evaluationStore.createEvaluation({
        testset_id: currentTestsetId.value,
        evaluation_method: evaluateForm.evaluation_method,
        evaluation_metrics: evaluateForm.evaluation_metrics
      })
      ElMessage.success('评估任务已创建')
      showEvaluateDialog.value = false
      router.push(`/evaluations/${result.id}`)
    } catch (error) {
      ElMessage.error('创建评估失败')
    } finally {
      creatingEvaluation.value = false
    }
  })
}

const handleExport = async (testset: TestSet) => {
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

const handleDelete = async (testset: TestSet) => {
  try {
    await ElMessageBox.confirm(`确定要删除测试集 "${testset.name}" 吗？`, '删除确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    await testsetApi.deleteTestSet(testset.id)
    ElMessage.success('删除成功')
    await fetchTestsets()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

onMounted(() => {
  fetchTestsets()
})
</script>

<style lang="scss" scoped>
.evaluations-view {
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
}
</style>
