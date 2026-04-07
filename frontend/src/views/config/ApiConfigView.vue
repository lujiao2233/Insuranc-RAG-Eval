<template>
  <div class="api-config-view">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>API配置管理</span>
        </div>
      </template>
      
      <el-tabs v-model="activeTab">
        <el-tab-pane label="Qwen API配置" name="qwen">
          <el-form :model="qwenConfig" label-width="150px" style="max-width: 600px;">
            <el-form-item label="API密钥">
              <el-input 
                v-model="qwenConfig['qwen.api_key']" 
                type="password"
                placeholder="请输入Qwen API密钥"
                show-password
              />
            </el-form-item>
            
            <el-form-item label="API端点">
              <el-input 
                v-model="qwenConfig['qwen.api_endpoint']" 
                placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
              />
            </el-form-item>
            
            <el-form-item label="生成模型">
              <el-select 
                v-model="qwenConfig['qwen.generation_model']" 
                placeholder="选择生成模型"
                style="width: 100%;"
              >
                <el-option label="qwen3-max" value="qwen3-max" />
                <el-option label="qwen3-plus" value="qwen3-plus" />
                <el-option label="qwen3-turbo" value="qwen3-turbo" />
                <el-option label="qwen2.5-72b-instruct" value="qwen2.5-72b-instruct" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="评估模型">
              <el-select 
                v-model="qwenConfig['qwen.evaluation_model']" 
                placeholder="选择评估模型"
                style="width: 100%;"
              >
                <el-option label="qwen3-max" value="qwen3-max" />
                <el-option label="qwen3-plus" value="qwen3-plus" />
                <el-option label="qwen3-turbo" value="qwen3-turbo" />
              </el-select>
            </el-form-item>
            
            <el-form-item label="温度参数">
              <el-slider 
                v-model="qwenConfig['qwen.temperature']" 
                :min="0" 
                :max="1" 
                :step="0.01"
                show-input
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveConfig('qwen')" :loading="saving">保存配置</el-button>
              <el-button @click="testConnection('qwen')" :loading="testing">测试连接</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="评估配置" name="evaluation">
          <el-form :model="evaluationConfig" label-width="180px" style="max-width: 600px;">
            <el-form-item label="评估批处理大小">
              <el-input-number 
                v-model="evaluationConfig['evaluation.batch_size']" 
                :min="1" 
                :max="100"
              />
            </el-form-item>
            
            <el-form-item label="评估温度">
              <el-slider 
                v-model="evaluationConfig['evaluation.temperature']" 
                :min="0" 
                :max="1" 
                :step="0.01"
                show-input
              />
            </el-form-item>
            
            <el-form-item label="RAGAS评估指标">
              <el-select 
                v-model="evaluationConfig['evaluation.ragas_metrics']" 
                multiple
                placeholder="选择RAGAS评估指标"
                style="width: 100%;"
              >
                <el-option label="答案相关性" value="answer_relevance" />
                <el-option label="上下文相关性" value="context_relevance" />
                <el-option label="忠实度" value="faithfulness" />
                <el-option label="答案正确性" value="answer_correctness" />
              </el-select>
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveConfig('evaluation')" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="性能阈值" name="thresholds">
          <el-form :model="thresholdConfig" label-width="200px" style="max-width: 600px;">
            <el-sub-menu title="答案相关性阈值">
              <el-form-item label="优秀阈值">
                <el-slider 
                  v-model="thresholdConfig['thresholds.answer_relevance.excellent']" 
                  :min="0" 
                  :max="1" 
                  :step="0.01"
                  show-input
                />
              </el-form-item>
              
              <el-form-item label="良好阈值">
                <el-slider 
                  v-model="thresholdConfig['thresholds.answer_relevance.good']" 
                  :min="0" 
                  :max="1" 
                  :step="0.01"
                  show-input
                />
              </el-form-item>
            </el-sub-menu>
            
            <el-sub-menu title="忠实度阈值">
              <el-form-item label="优秀阈值">
                <el-slider 
                  v-model="thresholdConfig['thresholds.faithfulness.excellent']" 
                  :min="0" 
                  :max="1" 
                  :step="0.01"
                  show-input
                />
              </el-form-item>
              
              <el-form-item label="良好阈值">
                <el-slider 
                  v-model="thresholdConfig['thresholds.faithfulness.good']" 
                  :min="0" 
                  :max="1" 
                  :step="0.01"
                  show-input
                />
              </el-form-item>
            </el-sub-menu>
            
            <el-form-item label="总体优秀阈值">
              <el-slider 
                v-model="thresholdConfig['thresholds.overall.excellent']" 
                :min="0" 
                :max="1" 
                :step="0.01"
                show-input
              />
            </el-form-item>
            
            <el-form-item label="总体良好阈值">
              <el-slider 
                v-model="thresholdConfig['thresholds.overall.good']" 
                :min="0" 
                :max="1" 
                :step="0.01"
                show-input
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveConfig('thresholds')" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
        
        <el-tab-pane label="系统配置" name="system">
          <el-form :model="systemConfig" label-width="150px" style="max-width: 600px;">
            <el-form-item label="默认问题数量">
              <el-input-number 
                v-model="systemConfig['default.num_questions']" 
                :min="1" 
                :max="100"
              />
            </el-form-item>
            
            <el-form-item label="默认批处理大小">
              <el-input-number 
                v-model="systemConfig['default.batch_size']" 
                :min="1" 
                :max="50"
              />
            </el-form-item>
            
            <el-form-item label="默认超时时间(秒)">
              <el-input-number 
                v-model="systemConfig['default.timeout']" 
                :min="10" 
                :max="300"
              />
            </el-form-item>
            
            <el-form-item label="最大文件大小(MB)">
              <el-input-number 
                v-model="systemConfig['files.max_size_mb']" 
                :min="1" 
                :max="100"
              />
            </el-form-item>
            
            <el-form-item label="数据保留天数">
              <el-input-number 
                v-model="systemConfig['storage.retention_days']" 
                :min="1" 
                :max="365"
              />
            </el-form-item>
            
            <el-form-item>
              <el-button type="primary" @click="saveConfig('system')" :loading="saving">保存配置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </el-card>
    
    <!-- 高级功能预览 -->
    <el-card style="margin-top: 20px;">
      <template #header>
        <div class="card-header">
          <span>高级功能预览</span>
        </div>
      </template>
      
      <div class="feature-preview">
        <h3>问题分类体系</h3>
        <el-collapse accordion>
          <el-collapse-item 
            v-for="(category, index) in taxonomy" 
            :key="index" 
            :title="category.major"
          >
            <div v-for="(minor, minorIndex) in category.minors" :key="minorIndex" class="minor-item">
              {{ minor }}
            </div>
          </el-collapse-item>
        </el-collapse>
        
        <h3 style="margin-top: 20px;">多文档关联策略</h3>
        <el-table :data="strategies" style="width: 100%;">
          <el-table-column prop="name" label="策略名称" width="150" />
          <el-table-column prop="description" label="描述" />
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { configApi } from '@/api/config'
import { testsetApi } from '@/api/testsets'

// 活跃标签页
const activeTab = ref('qwen')

// 状态
const saving = ref(false)
const testing = ref(false)

// 配置数据
const qwenConfig = reactive<Record<string, any>>({
  'qwen.api_key': '',
  'qwen.api_endpoint': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  'qwen.generation_model': 'qwen3-max',
  'qwen.evaluation_model': 'qwen3-max',
  'qwen.temperature': 0.1,
  'qwen.max_tokens': 2000
})

const evaluationConfig = reactive<Record<string, any>>({
  'evaluation.batch_size': 5,
  'evaluation.temperature': 0.1,
  'evaluation.ragas_metrics': ['answer_relevance', 'context_relevance', 'faithfulness']
})

const thresholdConfig = reactive<Record<string, any>>({
  'thresholds.answer_relevance.excellent': 0.8,
  'thresholds.answer_relevance.good': 0.6,
  'thresholds.faithfulness.excellent': 0.8,
  'thresholds.faithfulness.good': 0.6,
  'thresholds.overall.excellent': 0.8,
  'thresholds.overall.good': 0.6
})

const systemConfig = reactive<Record<string, any>>({
  'default.num_questions': 10,
  'default.batch_size': 5,
  'default.timeout': 60,
  'files.max_size_mb': 50,
  'storage.retention_days': 30,
  'logging.level': 'INFO'
})

// 高级功能数据
const taxonomy = ref<Array<{major: string, minors: string[]}>>([])
const strategies = ref<Array<{id: string, name: string, description: string}>>([])

// 保存配置
const saveConfig = async (tab: string) => {
  saving.value = true
  try {
    let configToSave: Record<string, any> = {}
    
    switch(tab) {
      case 'qwen':
        configToSave = qwenConfig
        break
      case 'evaluation':
        configToSave = evaluationConfig
        break
      case 'thresholds':
        configToSave = thresholdConfig
        break
      case 'system':
        configToSave = systemConfig
        break
    }
    
    await configApi.batchUpdateConfig(configToSave)
    ElMessage.success('配置保存成功')
  } catch (error: any) {
    console.error('保存配置失败:', error)
    ElMessage.error(error?.response?.data?.detail || '保存配置失败')
  } finally {
    saving.value = false
  }
}

// 测试连接
const testConnection = async (provider: string) => {
  testing.value = true
  try {
    const result = await configApi.testConnection(provider)
    if (result.success) {
      ElMessage.success(result.message)
    } else {
      ElMessage.error(result.message)
    }
  } catch (error: any) {
    console.error('测试连接失败:', error)
    ElMessage.error(error?.response?.data?.detail || '测试连接失败')
  } finally {
    testing.value = false
  }
}

// 加载高级功能配置
const loadAdvancedConfig = async () => {
  try {
    const config = await testsetApi.getAdvancedConfig()
    taxonomy.value = config.taxonomy
    strategies.value = config.strategies
  } catch (error: any) {
    console.error('加载高级配置失败:', error)
    // 使用默认值
    taxonomy.value = [
      {
        major: "基础理解类",
        minors: ["定义解释", "术语对齐", "事实召回", "表格/字段理解", "流程步骤", "对比区分"]
      },
      {
        major: "推理与综合类", 
        minors: ["因果推理", "条件推理", "归纳总结", "例外与边界", "决策建议"]
      }
    ]
    strategies.value = [
      { id: "deep_dive", name: "深度挖掘", description: "基于同一文档的多个切片生成关联问题" },
      { id: "cross_product", name: "跨产品比较", description: "基于不同文档的相似内容生成对比问题" },
      { id: "theme_chain", name: "主题链", description: "基于文档间的主题关联生成问题" }
    ]
  }
}

// 加载现有配置
const loadConfig = async () => {
  try {
    const config = await configApi.getAllConfig()
    
    // 更新各个配置对象
    Object.assign(qwenConfig, config.qwen || {})
    Object.assign(evaluationConfig, config.evaluation || {})
    Object.assign(thresholdConfig, config.thresholds || {})
    Object.assign(systemConfig, config.system || {})
  } catch (error: any) {
    console.error('加载配置失败:', error)
    ElMessage.error(error?.response?.data?.detail || '加载配置失败')
  }
}

onMounted(() => {
  loadConfig()
  loadAdvancedConfig()
})
</script>

<style lang="scss" scoped>
.api-config-view {
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .feature-preview {
    h3 {
      margin-bottom: 10px;
    }
    
    .minor-item {
      padding: 4px 0;
      color: #606266;
    }
  }
}
</style>
