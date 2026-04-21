<template>
  <div class="page config-page">
    <el-tabs v-model="activeTab" class="section">
      <el-tab-pane label="API配置" name="api">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="page-title">API密钥配置</span>
              <el-button type="primary" @click="testConnection">
                <el-icon><Connection /></el-icon>
                测试连接
              </el-button>
            </div>
          </template>
          
          <el-form label-width="120px">
            <el-form-item label="Qwen API Key">
              <el-input
                v-model="apiConfig.qwen_api_key"
                type="password"
                show-password
                placeholder="请输入Qwen API密钥"
              />
            </el-form-item>
            
            <el-form-item label="API端点">
              <el-input v-model="apiConfig.qwen_endpoint" placeholder="API端点地址" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveApiConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
          
          <el-divider />
          
          <div class="api-status">
            <h4>API状态</h4>
            <el-descriptions :column="2" border>
              <el-descriptions-item
                v-for="(status, service) in apiStatus"
                :key="service"
                :label="service.toUpperCase()"
              >
                <el-tag :type="status === '已配置' ? 'success' : 'info'">
                  {{ status }}
                </el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </div>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="模型配置" name="model">
        <el-card shadow="never">
          <template #header>
            <span class="page-title">模型参数配置</span>
          </template>
          
          <el-form label-width="150px">
            <el-form-item label="生成模型">
              <el-select
                v-model="modelConfig.generation_model"
                filterable
                allow-create
                default-first-option
                placeholder="请选择或输入生成模型"
                style="width: 100%;"
              >
                <el-option
                  v-for="model in modelOptions"
                  :key="model"
                  :label="model"
                  :value="model"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="评估模型">
              <el-select
                v-model="modelConfig.evaluation_model"
                filterable
                allow-create
                default-first-option
                placeholder="请选择或输入评估模型"
                style="width: 100%;"
              >
                <el-option
                  v-for="model in modelOptions"
                  :key="model"
                  :label="model"
                  :value="model"
                />
              </el-select>
            </el-form-item>

            <el-form-item label="分析模型">
              <el-select
                v-model="modelConfig.analysis_model"
                filterable
                allow-create
                default-first-option
                placeholder="请选择或输入分析模型"
                style="width: 100%;"
              >
                <el-option
                  v-for="model in modelOptions"
                  :key="model"
                  :label="model"
                  :value="model"
                />
              </el-select>
            </el-form-item>
            
            <el-form-item label="温度参数">
              <el-slider v-model="modelConfig.temperature" :min="0" :max="1" :step="0.1" show-input />
            </el-form-item>
            
            <el-form-item label="最大Token数">
              <el-input-number v-model="modelConfig.max_tokens" :min="100" :max="4000" :step="100" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveModelConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="评估配置" name="evaluation">
        <el-card shadow="never">
          <template #header>
            <span class="page-title">评估参数配置</span>
          </template>
          
          <el-form label-width="150px">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="RAGAS评估指标" class="vertical-form-item">
                  <el-checkbox-group v-model="evaluationConfig.ragas_metrics" class="metric-categories">
                    <div class="metric-category">
                      <div class="category-title">检索类</div>
                      <el-checkbox value="context_relevance" disabled>检索相关性</el-checkbox>
                      <el-checkbox value="context_precision" disabled>检索精确性</el-checkbox>
                    </div>
                    <div class="metric-category">
                      <div class="category-title">生成类</div>
                      <el-checkbox value="answer_relevance">答案相关性</el-checkbox>
                      <el-checkbox value="answer_correctness">答案正确性</el-checkbox>
                      <el-checkbox value="answer_similarity">答案相似度</el-checkbox>
                      <el-checkbox value="faithfulness" disabled>忠实度</el-checkbox>
                    </div>
                  </el-checkbox-group>
                </el-form-item>
              </el-col>

              <el-col :span="12">
                <el-form-item label="DeepEval评估指标" class="vertical-form-item">
                  <el-checkbox-group v-model="evaluationConfig.deepeval_metrics" class="metric-categories">
                    <div class="metric-category">
                      <div class="category-title">检索类</div>
                      <el-checkbox value="context_relevance" disabled>检索相关性</el-checkbox>
                      <el-checkbox value="context_precision" disabled>检索精确性</el-checkbox>
                    </div>
                    <div class="metric-category">
                      <div class="category-title">生成类</div>
                      <el-checkbox value="answer_relevance">答案相关性</el-checkbox>
                      <el-checkbox value="answer_correctness">答案正确性</el-checkbox>
                      <el-checkbox value="faithfulness" disabled>忠实度</el-checkbox>
                      <el-checkbox value="hallucination" disabled>幻觉检测</el-checkbox>
                    </div>
                    <div class="metric-category">
                      <div class="category-title">安全类</div>
                      <el-checkbox value="toxicity">有害言论检测</el-checkbox>
                      <el-checkbox value="bias">偏见检测</el-checkbox>
                    </div>
                  </el-checkbox-group>
                </el-form-item>
              </el-col>
            </el-row>
            
            <el-form-item label="批处理大小">
              <el-input-number v-model="evaluationConfig.batch_size" :min="1" :max="20" />
            </el-form-item>
            
            <el-form-item label="评估温度">
              <el-slider v-model="evaluationConfig.temperature" :min="0" :max="1" :step="0.1" show-input />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveEvaluationConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="阈值配置" name="thresholds">
        <el-card shadow="never">
          <template #header>
            <span class="page-title">性能阈值配置</span>
          </template>
          
          <el-form label-width="150px">
            <el-form-item label="优秀阈值">
              <el-slider v-model="thresholdsConfig.excellent" :min="0.5" :max="1" :step="0.05" show-input />
            </el-form-item>
            
            <el-form-item label="良好阈值">
              <el-slider v-model="thresholdsConfig.good" :min="0.3" :max="0.8" :step="0.05" show-input />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveThresholdsConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
      
      <el-tab-pane label="系统配置" name="system">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="page-title">系统参数</span>
              <div>
                <el-button @click="exportConfig">
                  <el-icon><Download /></el-icon>
                  导出配置
                </el-button>
                <el-button @click="resetConfig" type="warning">
                  <el-icon><RefreshRight /></el-icon>
                  重置默认
                </el-button>
              </div>
            </div>
          </template>
          
          <el-form label-width="150px">
            <el-form-item label="默认问题数">
              <el-input-number v-model="systemConfig.num_questions" :min="1" :max="100" />
            </el-form-item>
            
            <el-form-item label="默认批处理">
              <el-input-number v-model="systemConfig.batch_size" :min="1" :max="20" />
            </el-form-item>
            
            <el-form-item label="超时时间(秒)">
              <el-input-number v-model="systemConfig.timeout" :min="10" :max="300" />
            </el-form-item>
            
            <el-form-item label="最大文件大小(MB)">
              <el-input-number v-model="systemConfig.max_file_size" :min="1" :max="100" />
            </el-form-item>

            <el-form-item label="短片合并阈值(字)">
              <el-input-number v-model="systemConfig.short_merge_threshold" :min="20" :max="300" />
            </el-form-item>

            <el-form-item label="单切片最大字数">
              <el-input-number v-model="systemConfig.max_chunk_chars" :min="100" :max="2000" />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveSystemConfig">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Download, RefreshRight } from '@element-plus/icons-vue'
import { configApi } from '@/api/config'

const activeTab = ref('api')

const apiConfig = reactive({
  qwen_api_key: '',
  qwen_endpoint: ''
})

const modelConfig = reactive({
  generation_model: 'qwen3-max',
  evaluation_model: 'qwen3-max',
  analysis_model: 'qwen3-max',
  temperature: 0.1,
  max_tokens: 2000
})

const modelOptions = [
  'qwen3.6-flash',
  'qwen3.6-plus',
  'qwen3.5-plus',
  'qwen3.5-flash',
  'qwen3-max',
  'deepseek-v3.2',
  'glm-5'
]

const evaluationConfig = reactive({
  ragas_metrics: ['answer_relevance', 'context_relevance', 'context_precision', 'faithfulness', 'answer_correctness'],
  deepeval_metrics: ['answer_relevance', 'context_relevance', 'context_precision', 'faithfulness', 'answer_correctness', 'toxicity', 'bias'],
  batch_size: 5,
  temperature: 0.1
})

const thresholdsConfig = reactive({
  excellent: 0.8,
  good: 0.6
})

const systemConfig = reactive({
  num_questions: 10,
  batch_size: 5,
  timeout: 60,
  max_file_size: 50,
  short_merge_threshold: 60,
  max_chunk_chars: 500
})

const apiStatus = ref<Record<string, string>>({})

const fetchConfigs = async () => {
  try {
    const [apiStatusRes, qwenRes, evalRes, thresholdsRes, systemRes] = await Promise.all([
      configApi.getApiStatus(),
      configApi.getQwenConfig(),
      configApi.getEvaluationConfig(),
      configApi.getThresholds(),
      configApi.getSystemConfig()
    ])
    
    apiStatus.value = apiStatusRes.api_status
    
    if (qwenRes.configs) {
      modelConfig.generation_model = qwenRes.configs['qwen.generation_model'] || modelConfig.generation_model
      modelConfig.evaluation_model = qwenRes.configs['qwen.evaluation_model'] || modelConfig.evaluation_model
      modelConfig.analysis_model = qwenRes.configs['qwen.analysis_model'] || modelConfig.analysis_model
      modelConfig.temperature = parseFloat(qwenRes.configs['qwen.temperature']) || modelConfig.temperature
      modelConfig.max_tokens = parseInt(qwenRes.configs['qwen.max_tokens']) || modelConfig.max_tokens
    }
    
    if (evalRes.configs) {
      const ragasMetrics = evalRes.configs['evaluation.ragas_metrics']
      if (ragasMetrics && Array.isArray(ragasMetrics)) {
        evaluationConfig.ragas_metrics = ragasMetrics
      }
      const deepevalMetrics = evalRes.configs['evaluation.deepeval_metrics']
      if (deepevalMetrics && Array.isArray(deepevalMetrics)) {
        evaluationConfig.deepeval_metrics = deepevalMetrics
      }
      evaluationConfig.batch_size = parseInt(evalRes.configs['evaluation.batch_size']) || evaluationConfig.batch_size
      evaluationConfig.temperature = parseFloat(evalRes.configs['evaluation.temperature']) || evaluationConfig.temperature
    }
    
    if (thresholdsRes.configs) {
      thresholdsConfig.excellent = parseFloat(thresholdsRes.configs['thresholds.overall.excellent']) || thresholdsConfig.excellent
      thresholdsConfig.good = parseFloat(thresholdsRes.configs['thresholds.overall.good']) || thresholdsConfig.good
    }

    const systemChunking = systemRes.configs?.chunking || {}
    if (systemChunking['chunking.short_merge_threshold']) {
      systemConfig.short_merge_threshold = parseInt(systemChunking['chunking.short_merge_threshold']) || systemConfig.short_merge_threshold
    }
    if (systemChunking['chunking.max_chunk_chars']) {
      systemConfig.max_chunk_chars = parseInt(systemChunking['chunking.max_chunk_chars']) || systemConfig.max_chunk_chars
    }
  } catch (error) {
    console.error('Failed to fetch configs:', error)
  }
}

const saveApiConfig = async () => {
  try {
    if (apiConfig.qwen_api_key) {
      await configApi.setApiKey('qwen', apiConfig.qwen_api_key)
    }
    
    await configApi.batchUpdateConfigs({
      'qwen.api_endpoint': apiConfig.qwen_endpoint
    })
    
    ElMessage.success('API配置保存成功')
    fetchConfigs()
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveModelConfig = async () => {
  try {
    await configApi.batchUpdateConfigs({
      'qwen.generation_model': modelConfig.generation_model,
      'qwen.evaluation_model': modelConfig.evaluation_model,
      'qwen.analysis_model': modelConfig.analysis_model,
      'qwen.temperature': modelConfig.temperature.toString(),
      'qwen.max_tokens': modelConfig.max_tokens.toString()
    })
    
    ElMessage.success('模型配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveEvaluationConfig = async () => {
  try {
    await configApi.batchUpdateConfigs({
      'evaluation.ragas_metrics': evaluationConfig.ragas_metrics,
      'evaluation.deepeval_metrics': evaluationConfig.deepeval_metrics,
      'evaluation.batch_size': evaluationConfig.batch_size.toString(),
      'evaluation.temperature': evaluationConfig.temperature.toString()
    })
    
    ElMessage.success('评估配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveThresholdsConfig = async () => {
  try {
    await configApi.batchUpdateConfigs({
      'thresholds.overall.excellent': thresholdsConfig.excellent.toString(),
      'thresholds.overall.good': thresholdsConfig.good.toString()
    })
    
    ElMessage.success('阈值配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const saveSystemConfig = async () => {
  try {
    await configApi.batchUpdateConfigs({
      'default.num_questions': systemConfig.num_questions.toString(),
      'default.batch_size': systemConfig.batch_size.toString(),
      'default.timeout': systemConfig.timeout.toString(),
      'files.max_size_mb': systemConfig.max_file_size.toString(),
      'chunking.short_merge_threshold': systemConfig.short_merge_threshold.toString(),
      'chunking.max_chunk_chars': systemConfig.max_chunk_chars.toString()
    })
    
    ElMessage.success('系统配置保存成功')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

const testConnection = async () => {
  try {
    const result = await configApi.testApiConnection('qwen')
    if (result.status === 'success') {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error) {
    ElMessage.error('连接测试失败')
  }
}

const exportConfig = async () => {
  try {
    const result = await configApi.exportConfigs()
    const blob = new Blob([JSON.stringify(result.configs, null, 2)], { type: 'application/json' })
    const url = window.URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'config_export.json'
    a.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('配置导出成功')
  } catch (error) {
    ElMessage.error('导出失败')
  }
}

const resetConfig = async () => {
  try {
    await configApi.resetToDefaults()
    ElMessage.success('配置已重置为默认值')
    fetchConfigs()
  } catch (error) {
    ElMessage.error('重置失败')
  }
}

onMounted(() => {
  fetchConfigs()
})
</script>

<style lang="scss" scoped>
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

.config-page {
  .page-title {
    font-size: var(--font-16, 16px);
    font-weight: var(--fw-600, 600);
    color: var(--text-1, #303133);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .api-status {
    h4 {
      margin-bottom: 16px;
      color: var(--text-1, #303133);
      font-weight: var(--fw-600, 600);
    }
  }
}

:deep(.el-card__header) {
  padding: 16px;
  border-bottom: 1px solid var(--border-1, #ebeef5);
}

:deep(.el-card) {
  border-radius: var(--radius-8, 8px);
}
</style>
