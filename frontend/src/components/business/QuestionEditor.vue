<template>
  <div class="question-editor">
    <div class="editor-header">
      <div class="header-left">
        <span class="title">{{ title }}</span>
        <span v-if="questionCount" class="count">共 {{ questionCount }} 题</span>
      </div>
      <div class="header-right">
        <el-button type="primary" :icon="Plus" @click="handleAdd">
          添加问题
        </el-button>
        <el-button v-if="showImport" :icon="Upload" @click="handleImport">
          导入问题
        </el-button>
        <el-button v-if="showExport" :icon="Download" @click="handleExport">
          导出问题
        </el-button>
      </div>
    </div>

    <div class="editor-toolbar" v-if="questions.length > 0">
      <el-checkbox v-model="selectAll" @change="handleSelectAll">全选</el-checkbox>
      <el-button
        v-if="selectedIds.length > 0"
        type="danger"
        text
        @click="handleBatchDelete"
      >
        删除选中 ({{ selectedIds.length }})
      </el-button>
      <div class="filter-group">
        <el-select v-model="filterType" placeholder="问题类型" clearable size="small" style="width: 120px">
          <el-option label="事实型" value="factual" />
          <el-option label="推理型" value="reasoning" />
          <el-option label="创造型" value="creative" />
        </el-select>
        <el-input
          v-model="searchKeyword"
          placeholder="搜索问题"
          clearable
          size="small"
          style="width: 200px"
          :prefix-icon="Search"
        />
      </div>
    </div>

    <div class="editor-content">
      <div v-if="filteredQuestions.length === 0" class="empty-state">
        <el-empty description="暂无问题，点击上方按钮添加">
          <el-button type="primary" @click="handleAdd">添加第一个问题</el-button>
        </el-empty>
      </div>

      <div v-else class="question-list">
        <div
          v-for="(question, index) in filteredQuestions"
          :key="question.id"
          class="question-item"
          :class="{ 'is-editing': editingId === question.id, 'is-selected': selectedIds.includes(question.id) }"
        >
          <div class="question-header">
            <div class="header-left">
              <el-checkbox
                v-model="selectedIds"
                :value="question.id"
                @change="handleSelectChange"
              />
              <span class="question-index">{{ index + 1 }}</span>
              <el-tag :type="getTypeTagType(question.question_type)" size="small">
                {{ getTypeLabel(question.question_type) }}
              </el-tag>
              <el-tag v-if="question.category_major" type="info" size="small">
                {{ question.category_major }}
              </el-tag>
            </div>
            <div class="header-right">
              <el-button-group size="small">
                <el-button :icon="Edit" @click="handleEdit(question)" />
                <el-button :icon="Delete" type="danger" @click="handleDelete(question)" />
              </el-button-group>
            </div>
          </div>

          <div class="question-body">
            <div v-if="editingId === question.id" class="edit-form">
              <el-form :model="editForm" label-position="top" size="small">
                <el-form-item label="问题内容" required>
                  <el-input
                    v-model="editForm.question"
                    type="textarea"
                    :rows="3"
                    placeholder="请输入问题内容"
                  />
                </el-form-item>
                <el-row :gutter="16">
                  <el-col :span="12">
                    <el-form-item label="问题类型">
                      <el-select v-model="editForm.question_type" style="width: 100%">
                        <el-option label="事实型" value="factual" />
                        <el-option label="推理型" value="reasoning" />
                        <el-option label="创造型" value="creative" />
                      </el-select>
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="主要分类">
                      <el-input v-model="editForm.category_major" placeholder="如：概念理解" />
                    </el-form-item>
                  </el-col>
                </el-row>
                <el-form-item label="期望答案">
                  <el-input
                    v-model="editForm.expected_answer"
                    type="textarea"
                    :rows="2"
                    placeholder="请输入期望答案（可选）"
                  />
                </el-form-item>
                <el-form-item label="上下文">
                  <el-input
                    v-model="editForm.context"
                    type="textarea"
                    :rows="2"
                    placeholder="请输入相关上下文（可选）"
                  />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" @click="handleSaveEdit">保存</el-button>
                  <el-button @click="handleCancelEdit">取消</el-button>
                </el-form-item>
              </el-form>
            </div>
            <div v-else class="view-mode">
              <div class="question-text">{{ question.question }}</div>
              <div v-if="question.expected_answer" class="expected-answer">
                <span class="label">期望答案：</span>
                <span class="content">{{ question.expected_answer }}</span>
              </div>
              <div v-if="question.context" class="context">
                <span class="label">上下文：</span>
                <span class="content">{{ question.context }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="importDialogVisible" title="导入问题" width="500px">
      <el-upload
        drag
        :auto-upload="false"
        accept=".json,.csv"
        :on-change="handleFileChange"
        :limit="1"
      >
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
        <div class="el-upload__text">
          拖拽文件到此处或 <em>点击上传</em>
        </div>
        <template #tip>
          <div class="el-upload__tip">
            支持 JSON 或 CSV 格式文件
          </div>
        </template>
      </el-upload>
      <template #footer>
        <el-button @click="importDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmImport" :loading="importing">
          确认导入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, Upload, Download, Search, UploadFilled } from '@element-plus/icons-vue'
import type { Question } from '@/types/models'

interface Props {
  questions?: Question[]
  title?: string
  showImport?: boolean
  showExport?: boolean
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  questions: () => [],
  title: '问题列表',
  showImport: true,
  showExport: true,
  readonly: false
})

const emit = defineEmits<{
  (e: 'add'): void
  (e: 'edit', question: Question): void
  (e: 'delete', question: Question): void
  (e: 'batch-delete', ids: string[]): void
  (e: 'save', question: Question): void
  (e: 'import', questions: Partial<Question>[]): void
  (e: 'export', questions: Question[]): void
}>()

const editingId = ref<string | null>(null)
const selectedIds = ref<string[]>([])
const selectAll = ref(false)
const filterType = ref<string>('')
const searchKeyword = ref('')
const importDialogVisible = ref(false)
const importing = ref(false)
const importFile = ref<File | null>(null)

const editForm = reactive({
  question: '',
  question_type: 'factual' as Question['question_type'],
  category_major: '',
  category_minor: '',
  expected_answer: '',
  context: ''
})

const questionCount = computed(() => props.questions.length)

const filteredQuestions = computed(() => {
  let result = [...props.questions]

  if (filterType.value) {
    result = result.filter(q => q.question_type === filterType.value)
  }

  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(q =>
      q.question.toLowerCase().includes(keyword) ||
      q.expected_answer?.toLowerCase().includes(keyword)
    )
  }

  return result
})

const getTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    factual: '事实型',
    reasoning: '推理型',
    creative: '创造型'
  }
  return labels[type] || type
}

const getTypeTagType = (type: string) => {
  const types: Record<string, string> = {
    factual: 'primary',
    reasoning: 'warning',
    creative: 'success'
  }
  return types[type] || 'info'
}

const handleAdd = () => {
  emit('add')
}

const handleEdit = (question: Question) => {
  editingId.value = question.id
  editForm.question = question.question
  editForm.question_type = question.question_type
  editForm.category_major = question.category_major || ''
  editForm.category_minor = question.category_minor || ''
  editForm.expected_answer = question.expected_answer || ''
  editForm.context = question.context || ''
}

const handleSaveEdit = () => {
  if (!editForm.question.trim()) {
    ElMessage.warning('请输入问题内容')
    return
  }

  const question = props.questions.find(q => q.id === editingId.value)
  if (question) {
    const updatedQuestion: Question = {
      ...question,
      question: editForm.question,
      question_type: editForm.question_type,
      category_major: editForm.category_major,
      category_minor: editForm.category_minor,
      expected_answer: editForm.expected_answer,
      context: editForm.context
    }
    emit('save', updatedQuestion)
  }
  editingId.value = null
}

const handleCancelEdit = () => {
  editingId.value = null
}

const handleDelete = async (question: Question) => {
  try {
    await ElMessageBox.confirm('确定要删除这个问题吗？', '提示', {
      type: 'warning'
    })
    emit('delete', question)
  } catch {
    // 用户取消
  }
}

const handleSelectAll = (val: boolean) => {
  selectedIds.value = val ? filteredQuestions.value.map(q => q.id) : []
}

const handleSelectChange = () => {
  selectAll.value = selectedIds.value.length === filteredQuestions.value.length
}

const handleBatchDelete = async () => {
  try {
    await ElMessageBox.confirm(`确定要删除选中的 ${selectedIds.value.length} 个问题吗？`, '提示', {
      type: 'warning'
    })
    emit('batch-delete', [...selectedIds.value])
    selectedIds.value = []
    selectAll.value = false
  } catch {
    // 用户取消
  }
}

const handleImport = () => {
  importDialogVisible.value = true
}

const handleFileChange = (file: any) => {
  importFile.value = file.raw
}

const confirmImport = async () => {
  if (!importFile.value) {
    ElMessage.warning('请选择要导入的文件')
    return
  }

  importing.value = true
  try {
    const text = await importFile.value.text()
    let questions: Partial<Question>[] = []

    if (importFile.value.name.endsWith('.json')) {
      questions = JSON.parse(text)
    } else if (importFile.value.name.endsWith('.csv')) {
      const lines = text.split('\n')
      const headers = lines[0].split(',')
      for (let i = 1; i < lines.length; i++) {
        if (!lines[i].trim()) continue
        const values = lines[i].split(',')
        const obj: Record<string, string> = {}
        headers.forEach((h, idx) => {
          obj[h.trim()] = values[idx]?.trim() || ''
        })
        questions.push({
          question: obj.question || obj.question_text,
          question_type: (obj.question_type || 'factual') as Question['question_type'],
          expected_answer: obj.expected_answer || obj.answer,
          category_major: obj.category_major,
          context: obj.context
        })
      }
    }

    emit('import', questions)
    importDialogVisible.value = false
    ElMessage.success(`成功导入 ${questions.length} 个问题`)
  } catch (error) {
    ElMessage.error('文件解析失败，请检查文件格式')
  } finally {
    importing.value = false
  }
}

const handleExport = () => {
  const questionsToExport = selectedIds.value.length > 0
    ? props.questions.filter(q => selectedIds.value.includes(q.id))
    : props.questions

  emit('export', questionsToExport)

  const dataStr = JSON.stringify(questionsToExport, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `questions_${Date.now()}.json`
  link.click()
  URL.revokeObjectURL(url)
}

watch(() => props.questions, () => {
  selectedIds.value = selectedIds.value.filter(id =>
    props.questions.some(q => q.id === id)
  )
}, { deep: true })
</script>

<style lang="scss" scoped>
.question-editor {
  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 12px;

      .title {
        font-size: 16px;
        font-weight: 600;
        color: #303133;
      }

      .count {
        font-size: 14px;
        color: #909399;
      }
    }

    .header-right {
      display: flex;
      gap: 8px;
    }
  }

  .editor-toolbar {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px 16px;
    background-color: #f5f7fa;
    border-radius: 4px;
    margin-bottom: 16px;

    .filter-group {
      margin-left: auto;
      display: flex;
      gap: 8px;
    }
  }

  .editor-content {
    min-height: 200px;

    .empty-state {
      padding: 40px 0;
    }

    .question-list {
      .question-item {
        border: 1px solid #ebeef5;
        border-radius: 8px;
        margin-bottom: 12px;
        transition: all 0.3s;

        &:hover {
          box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        }

        &.is-selected {
          border-color: #409eff;
          background-color: #f0f7ff;
        }

        &.is-editing {
          border-color: #409eff;
        }

        .question-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 12px 16px;
          border-bottom: 1px solid #ebeef5;
          background-color: #fafafa;
          border-radius: 8px 8px 0 0;

          .header-left {
            display: flex;
            align-items: center;
            gap: 12px;

            .question-index {
              font-weight: 600;
              color: #409eff;
            }
          }
        }

        .question-body {
          padding: 16px;

          .view-mode {
            .question-text {
              font-size: 15px;
              line-height: 1.6;
              color: #303133;
              margin-bottom: 12px;
            }

            .expected-answer,
            .context {
              font-size: 14px;
              color: #606266;
              margin-bottom: 8px;

              .label {
                color: #909399;
                margin-right: 8px;
              }

              .content {
                color: #606266;
              }
            }
          }

          .edit-form {
            .el-form-item {
              margin-bottom: 16px;
            }
          }
        }
      }
    }
  }
}
</style>
