<template>
  <div class="config-form">
    <el-form
      ref="formRef"
      :model="formData"
      :rules="rules"
      :label-width="labelWidth"
      :label-position="labelPosition"
      @submit.prevent="handleSubmit"
    >
      <div v-for="group in groupedConfigs" :key="group.key" class="config-group">
        <div class="group-header">
          <h4 class="group-title">{{ group.title }}</h4>
          <p v-if="group.description" class="group-description">{{ group.description }}</p>
        </div>
        <div class="group-content">
          <template v-for="config in group.items" :key="config.config_key">
            <el-form-item
              :label="getConfigLabel(config.config_key)"
              :prop="config.config_key"
              :rules="getFieldRules(config)"
            >
              <template v-if="getConfigType(config.config_key) === 'api_key'">
                <el-input
                  v-model="formData[config.config_key]"
                  :type="showApiKey[config.config_key] ? 'text' : 'password'"
                  :placeholder="config.config_description || '请输入API密钥'"
                  clearable
                >
                  <template #suffix>
                    <el-icon
                      class="toggle-visibility"
                      @click="toggleApiKeyVisibility(config.config_key)"
                    >
                      <View v-if="!showApiKey[config.config_key]" />
                      <Hide v-else />
                    </el-icon>
                  </template>
                </el-input>
              </template>

              <template v-else-if="getConfigType(config.config_key) === 'select'">
                <el-select
                  v-model="formData[config.config_key]"
                  :placeholder="`请选择${getConfigLabel(config.config_key)}`"
                  style="width: 100%"
                >
                  <el-option
                    v-for="option in getSelectOptions(config.config_key)"
                    :key="option.value"
                    :label="option.label"
                    :value="option.value"
                  />
                </el-select>
              </template>

              <template v-else-if="getConfigType(config.config_key) === 'number'">
                <el-input-number
                  v-model="formData[config.config_key]"
                  :min="getNumberRange(config.config_key).min"
                  :max="getNumberRange(config.config_key).max"
                  :step="getNumberRange(config.config_key).step || 1"
                  :precision="getNumberRange(config.config_key).precision || 0"
                  style="width: 100%"
                />
              </template>

              <template v-else-if="getConfigType(config.config_key) === 'switch'">
                <el-switch
                  v-model="formData[config.config_key]"
                  :active-value="true"
                  :inactive-value="false"
                />
              </template>

              <template v-else-if="getConfigType(config.config_key) === 'textarea'">
                <el-input
                  v-model="formData[config.config_key]"
                  type="textarea"
                  :rows="4"
                  :placeholder="config.config_description || '请输入内容'"
                />
              </template>

              <template v-else-if="getConfigType(config.config_key) === 'json'">
                <el-input
                  v-model="formData[config.config_key]"
                  type="textarea"
                  :rows="6"
                  placeholder="请输入JSON格式配置"
                  @blur="validateJson(config.config_key)"
                />
                <div v-if="jsonErrors[config.config_key]" class="json-error">
                  {{ jsonErrors[config.config_key] }}
                </div>
              </template>

              <template v-else>
                <el-input
                  v-model="formData[config.config_key]"
                  :placeholder="config.config_description || '请输入'"
                  clearable
                />
              </template>

              <div v-if="config.config_description && getConfigType(config.config_key) !== 'api_key'" class="field-tip">
                {{ config.config_description }}
              </div>
            </el-form-item>

            <div v-if="getConfigType(config.config_key) === 'api_key'" class="api-test-row">
              <el-button
                size="small"
                :loading="testingKey === config.config_key"
                @click="testApiConnection(config.config_key)"
              >
                测试连接
              </el-button>
              <span v-if="testResults[config.config_key]" class="test-result" :class="testResults[config.config_key].success ? 'success' : 'error'">
                {{ testResults[config.config_key].message }}
              </span>
            </div>
          </template>
        </div>
      </div>

      <div class="form-actions">
        <el-button @click="handleReset">重置</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSubmit">
          保存配置
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { View, Hide } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { Configuration } from '@/types/models'

interface ConfigGroup {
  key: string
  title: string
  description?: string
  items: Configuration[]
}

interface Props {
  configs: Configuration[]
  labelWidth?: string
  labelPosition?: 'left' | 'right' | 'top'
}

const props = withDefaults(defineProps<Props>(), {
  labelWidth: '180px',
  labelPosition: 'right'
})

const emit = defineEmits<{
  (e: 'submit', data: Record<string, any>): void
  (e: 'reset'): void
  (e: 'test-api', key: string): Promise<{ success: boolean; message: string }>
}>()

const formRef = ref<FormInstance>()
const formData = reactive<Record<string, any>>({})
const originalData = reactive<Record<string, any>>({})
const showApiKey = reactive<Record<string, boolean>>({})
const jsonErrors = reactive<Record<string, string>>({})
const testResults = reactive<Record<string, { success: boolean; message: string }>>({})
const submitting = ref(false)
const testingKey = ref<string | null>(null)

const configGroups: Record<string, { title: string; description?: string }> = {
  llm: {
    title: 'LLM 配置',
    description: '配置大语言模型相关参数'
  },
  evaluation: {
    title: '评估参数',
    description: '配置评估相关参数'
  },
  rag: {
    title: 'RAG 参数',
    description: '配置检索增强生成相关参数'
  },
  system: {
    title: '系统设置',
    description: '配置系统运行参数'
  },
  other: {
    title: '其他配置'
  }
}

const configMetadata: Record<string, {
  label: string
  type: 'text' | 'api_key' | 'select' | 'number' | 'switch' | 'textarea' | 'json'
  group?: string
  options?: { label: string; value: any }[]
  min?: number
  max?: number
  step?: number
  precision?: number
  required?: boolean
}> = {
  qwen_api_key: {
    label: 'Qwen API Key',
    type: 'api_key',
    group: 'llm',
    required: true
  },
  qwen_model: {
    label: 'Qwen 模型',
    type: 'select',
    group: 'llm',
    options: [
      { label: 'Qwen-Turbo', value: 'qwen-turbo' },
      { label: 'Qwen-Plus', value: 'qwen-plus' },
      { label: 'Qwen-Max', value: 'qwen-max' }
    ]
  },
  qwen_temperature: {
    label: 'Temperature',
    type: 'number',
    group: 'llm',
    min: 0,
    max: 2,
    step: 0.1,
    precision: 1
  },
  qwen_max_tokens: {
    label: '最大Token数',
    type: 'number',
    group: 'llm',
    min: 100,
    max: 32000,
    step: 100
  },
  evaluation_method: {
    label: '评估方法',
    type: 'select',
    group: 'evaluation',
    options: [
      { label: 'RAGAS官方', value: 'ragas_official' },
      { label: 'DeepEval', value: 'deepeval' }
    ]
  },
  evaluation_metrics: {
    label: '评估指标',
    type: 'json',
    group: 'evaluation'
  },
  chunk_size: {
    label: '分块大小',
    type: 'number',
    group: 'rag',
    min: 100,
    max: 2000,
    step: 100
  },
  chunk_overlap: {
    label: '分块重叠',
    type: 'number',
    group: 'rag',
    min: 0,
    max: 500,
    step: 50
  },
  retrieval_top_k: {
    label: '检索Top-K',
    type: 'number',
    group: 'rag',
    min: 1,
    max: 20,
    step: 1
  },
  enable_cache: {
    label: '启用缓存',
    type: 'switch',
    group: 'system'
  },
  cache_ttl: {
    label: '缓存时间(秒)',
    type: 'number',
    group: 'system',
    min: 60,
    max: 86400,
    step: 60
  }
}

const rules = computed<FormRules>(() => {
  const r: FormRules = {}
  Object.keys(formData).forEach(key => {
    const meta = configMetadata[key]
    if (meta?.required) {
      r[key] = [{ required: true, message: `请输入${meta.label}`, trigger: 'blur' }]
    }
  })
  return r
})

const groupedConfigs = computed((): ConfigGroup[] => {
  const groups: Record<string, Configuration[]> = {}

  props.configs.forEach(config => {
    const meta = configMetadata[config.config_key]
    const groupKey = meta?.group || 'other'
    if (!groups[groupKey]) {
      groups[groupKey] = []
    }
    groups[groupKey].push(config)
  })

  return Object.entries(groups).map(([key, items]) => ({
    key,
    title: configGroups[key]?.title || key,
    description: configGroups[key]?.description,
    items
  }))
})

const getConfigLabel = (key: string) => {
  return configMetadata[key]?.label || key
}

const getConfigType = (key: string) => {
  return configMetadata[key]?.type || 'text'
}

const getSelectOptions = (key: string) => {
  return configMetadata[key]?.options || []
}

const getNumberRange = (key: string) => {
  return {
    min: configMetadata[key]?.min ?? 0,
    max: configMetadata[key]?.max ?? 100,
    step: configMetadata[key]?.step,
    precision: configMetadata[key]?.precision
  }
}

const getFieldRules = (config: Configuration) => {
  const meta = configMetadata[config.config_key]
  if (meta?.required) {
    return [{ required: true, message: `请输入${meta.label}`, trigger: 'blur' }]
  }
  return []
}

const toggleApiKeyVisibility = (key: string) => {
  showApiKey[key] = !showApiKey[key]
}

const validateJson = (key: string) => {
  const value = formData[key]
  if (!value) {
    delete jsonErrors[key]
    return
  }

  try {
    JSON.parse(value)
    delete jsonErrors[key]
  } catch (e) {
    jsonErrors[key] = 'JSON格式无效'
  }
}

const testApiConnection = async (key: string) => {
  testingKey.value = key
  try {
    const result = await emit('test-api', key)
    testResults[key] = result || { success: false, message: '测试失败' }
  } catch (error: any) {
    testResults[key] = { success: false, message: error.message || '测试失败' }
  } finally {
    testingKey.value = null
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  const hasJsonErrors = Object.keys(jsonErrors).length > 0
  if (hasJsonErrors) {
    ElMessage.error('请修正JSON格式错误')
    return
  }

  try {
    await formRef.value.validate()
    submitting.value = true
    emit('submit', { ...formData })
  } catch {
    ElMessage.warning('请完善必填项')
  } finally {
    submitting.value = false
  }
}

const handleReset = () => {
  Object.assign(formData, { ...originalData })
  Object.keys(jsonErrors).forEach(key => delete jsonErrors[key])
  Object.keys(testResults).forEach(key => delete testResults[key])
  formRef.value?.clearValidate()
  emit('reset')
}

watch(() => props.configs, (configs) => {
  configs.forEach(config => {
    let value: any = config.config_value

    if (getConfigType(config.config_key) === 'number') {
      value = parseFloat(value) || 0
    } else if (getConfigType(config.config_key) === 'switch') {
      value = value === 'true' || value === true
    }

    formData[config.config_key] = value
    originalData[config.config_key] = value
  })
}, { immediate: true, deep: true })

defineExpose({
  validate: () => formRef.value?.validate(),
  resetFields: () => formRef.value?.resetFields(),
  getFormData: () => ({ ...formData })
})
</script>

<style lang="scss" scoped>
.config-form {
  .config-group {
    margin-bottom: 32px;

    .group-header {
      margin-bottom: 20px;

      .group-title {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
        margin: 0 0 8px;
      }

      .group-description {
        font-size: 13px;
        color: #909399;
        margin: 0;
      }
    }

    .group-content {
      padding: 20px;
      background-color: #fafafa;
      border-radius: 8px;

      :deep(.el-form-item) {
        margin-bottom: 20px;

        &:last-child {
          margin-bottom: 0;
        }
      }
    }
  }

  .toggle-visibility {
    cursor: pointer;
    color: #909399;

    &:hover {
      color: #409eff;
    }
  }

  .field-tip {
    margin-top: 4px;
    font-size: 12px;
    color: #909399;
    line-height: 1.5;
  }

  .api-test-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: -12px;
    margin-bottom: 16px;
    padding-left: calc(v-bind(labelWidth) + 12px);

    .test-result {
      font-size: 13px;

      &.success {
        color: #67c23a;
      }

      &.error {
        color: #f56c6c;
      }
    }
  }

  .json-error {
    margin-top: 4px;
    font-size: 12px;
    color: #f56c6c;
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
