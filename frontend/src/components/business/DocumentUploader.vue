<template>
  <div class="document-uploader">
    <el-upload
      ref="uploadRef"
      class="upload-area"
      :action="uploadUrl"
      :headers="headers"
      :multiple="multiple"
      :limit="limit"
      :accept="acceptTypes"
      :auto-upload="autoUpload"
      :show-file-list="showFileList"
      :before-upload="handleBeforeUpload"
      :on-progress="handleProgress"
      :on-success="handleSuccess"
      :on-error="handleError"
      :on-exceed="handleExceed"
      :on-remove="handleRemove"
      :file-list="fileList"
      drag
    >
      <div class="upload-content">
        <el-icon class="upload-icon"><UploadFilled /></el-icon>
        <div class="upload-text">
          <p class="main-text">将文件拖到此处，或<em>点击上传</em></p>
          <p class="sub-text">支持 {{ acceptText }} 格式，单个文件最大 {{ formatSize(maxSize) }}</p>
        </div>
      </div>
    </el-upload>

    <div v-if="uploadingFiles.length > 0" class="upload-list">
      <div v-for="file in uploadingFiles" :key="file.uid" class="upload-item">
        <div class="file-info">
          <el-icon class="file-icon"><Document /></el-icon>
          <span class="file-name">{{ file.name }}</span>
          <span class="file-size">{{ formatSize(file.size || 0) }}</span>
        </div>
        <div class="file-progress">
          <el-progress
            :percentage="file.progress || 0"
            :status="file.status === 'success' ? 'success' : file.status === 'error' ? 'exception' : undefined"
            :stroke-width="6"
          />
        </div>
        <div class="file-actions">
          <el-button
            v-if="file.status === 'uploading'"
            type="danger"
            size="small"
            text
            @click="handleCancelUpload(file)"
          >
            取消
          </el-button>
          <el-icon v-if="file.status === 'success'" class="success-icon"><CircleCheckFilled /></el-icon>
          <el-icon v-if="file.status === 'error'" class="error-icon"><CircleCloseFilled /></el-icon>
        </div>
      </div>
    </div>

    <div v-if="tip" class="upload-tip">
      <el-icon><InfoFilled /></el-icon>
      <span>{{ tip }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, Document, CircleCheckFilled, CircleCloseFilled, InfoFilled } from '@element-plus/icons-vue'
import type { UploadFile, UploadInstance, UploadRawFile } from 'element-plus'
import { useUpload } from '@/composables/useUpload'
import { tokenStorage } from '@/utils/storage'

interface Props {
  uploadUrl?: string
  multiple?: boolean
  limit?: number
  maxSize?: number
  acceptTypes?: string[]
  autoUpload?: boolean
  showFileList?: boolean
  tip?: string
}

interface UploadingFile extends UploadFile {
  progress?: number
  status?: 'ready' | 'uploading' | 'success' | 'error'
}

const props = withDefaults(defineProps<Props>(), {
  uploadUrl: '/api/v1/documents/upload',
  multiple: true,
  limit: 10,
  maxSize: 50 * 1024 * 1024,
  acceptTypes: () => ['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.txt', '.md'],
  autoUpload: true,
  showFileList: false,
  tip: ''
})

const emit = defineEmits<{
  (e: 'success', file: UploadFile, response: any): void
  (e: 'error', file: UploadFile, error: Error): void
  (e: 'progress', file: UploadFile, percent: number): void
  (e: 'remove', file: UploadFile): void
  (e: 'exceed', files: File[]): void
  (e: 'change', fileList: UploadFile[]): void
}>()

const uploadRef = ref<UploadInstance>()
const fileList = ref<UploadFile[]>([])
const uploadingFiles = ref<UploadingFile[]>([])

const headers = computed(() => ({
  Authorization: `Bearer ${tokenStorage.get()}`
}))

const acceptText = computed(() => {
  return props.acceptTypes.map(t => t.toUpperCase().replace('.', '')).join('、')
})

const { validateFile, formatSize } = useUpload({
  maxSize: props.maxSize,
  allowedTypes: props.acceptTypes
})

const handleBeforeUpload = (rawFile: UploadRawFile) => {
  const validation = validateFile(rawFile)
  if (!validation.valid) {
    ElMessage.error(validation.error || '文件验证失败')
    return false
  }

  const uploadingFile: UploadingFile = {
    ...rawFile,
    uid: rawFile.uid,
    name: rawFile.name,
    size: rawFile.size,
    progress: 0,
    status: 'uploading'
  }
  uploadingFiles.value.push(uploadingFile)

  return true
}

const handleProgress = (event: { percent: number }, uploadFile: UploadFile) => {
  const file = uploadingFiles.value.find(f => f.uid === uploadFile.uid)
  if (file) {
    file.progress = Math.round(event.percent)
    emit('progress', uploadFile, file.progress)
  }
}

const handleSuccess = (response: any, uploadFile: UploadFile) => {
  const file = uploadingFiles.value.find(f => f.uid === uploadFile.uid)
  if (file) {
    file.status = 'success'
    file.progress = 100
  }
  emit('success', uploadFile, response)
  emit('change', fileList.value)
}

const handleError = (error: Error, uploadFile: UploadFile) => {
  const file = uploadingFiles.value.find(f => f.uid === uploadFile.uid)
  if (file) {
    file.status = 'error'
  }
  emit('error', uploadFile, error)
}

const handleExceed = (files: File[]) => {
  ElMessage.warning(`最多只能上传 ${props.limit} 个文件`)
  emit('exceed', files)
}

const handleRemove = (uploadFile: UploadFile) => {
  uploadingFiles.value = uploadingFiles.value.filter(f => f.uid !== uploadFile.uid)
  emit('remove', uploadFile)
  emit('change', fileList.value)
}

const handleCancelUpload = (file: UploadingFile) => {
  uploadRef.value?.abort(file)
  uploadingFiles.value = uploadingFiles.value.filter(f => f.uid !== file.uid)
}

const clearFiles = () => {
  uploadingFiles.value = []
  fileList.value = []
  uploadRef.value?.clearFiles()
}

const submit = () => {
  uploadRef.value?.submit()
}

defineExpose({
  clearFiles,
  submit,
  fileList: computed(() => fileList.value)
})
</script>

<style lang="scss" scoped>
.document-uploader {
  .upload-area {
    width: 100%;

    :deep(.el-upload-dragger) {
      width: 100%;
      height: 180px;
      border: 2px dashed #dcdfe6;
      border-radius: 8px;
      background-color: #fafafa;
      transition: all 0.3s;

      &:hover {
        border-color: #409eff;
        background-color: #f0f7ff;
      }
    }
  }

  .upload-content {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 20px;

    .upload-icon {
      font-size: 48px;
      color: #c0c4cc;
      margin-bottom: 16px;
    }

    .upload-text {
      text-align: center;

      .main-text {
        font-size: 16px;
        color: #606266;
        margin: 0 0 8px;

        em {
          color: #409eff;
          font-style: normal;
        }
      }

      .sub-text {
        font-size: 12px;
        color: #909399;
        margin: 0;
      }
    }
  }

  .upload-list {
    margin-top: 16px;
    border: 1px solid #ebeef5;
    border-radius: 4px;

    .upload-item {
      display: flex;
      align-items: center;
      padding: 12px 16px;
      border-bottom: 1px solid #ebeef5;

      &:last-child {
        border-bottom: none;
      }

      .file-info {
        flex: 1;
        display: flex;
        align-items: center;
        min-width: 0;

        .file-icon {
          font-size: 20px;
          color: #409eff;
          margin-right: 8px;
          flex-shrink: 0;
        }

        .file-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          font-size: 14px;
          color: #606266;
        }

        .file-size {
          margin-left: 8px;
          font-size: 12px;
          color: #909399;
          flex-shrink: 0;
        }
      }

      .file-progress {
        width: 200px;
        margin: 0 16px;
      }

      .file-actions {
        width: 60px;
        text-align: right;

        .success-icon {
          font-size: 20px;
          color: #67c23a;
        }

        .error-icon {
          font-size: 20px;
          color: #f56c6c;
        }
      }
    }
  }

  .upload-tip {
    display: flex;
    align-items: center;
    margin-top: 12px;
    padding: 8px 12px;
    background-color: #f4f4f5;
    border-radius: 4px;
    font-size: 12px;
    color: #909399;

    .el-icon {
      margin-right: 6px;
    }
  }
}
</style>
