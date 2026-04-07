import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

interface UploadOptions {
  maxSize?: number
  allowedTypes?: string[]
  multiple?: boolean
}

export function useUpload(options: UploadOptions = {}) {
  const {
    maxSize = 50 * 1024 * 1024,
    allowedTypes = ['.pdf', '.docx', '.xlsx'],
    multiple = false
  } = options

  const uploading = ref(false)
  const progress = ref(0)
  const files = ref<File[]>([])
  const error = ref<string | null>(null)

  const isUploading = computed(() => uploading.value)
  const hasFiles = computed(() => files.value.length > 0)

  const validateFile = (file: File): { valid: boolean; message?: string } => {
    if (file.size > maxSize) {
      return { valid: false, message: `文件大小超过限制 (${Math.round(maxSize / 1024 / 1024)}MB)` }
    }

    const ext = '.' + file.name.split('.').pop()?.toLowerCase()
    if (!allowedTypes.includes(ext)) {
      return { valid: false, message: `不支持的文件类型: ${ext}` }
    }

    return { valid: true }
  }

  const addFiles = (newFiles: FileList | File[]): { valid: File[]; invalid: { file: File; reason: string }[] } => {
    const valid: File[] = []
    const invalid: { file: File; reason: string }[] = []

    const fileArray = Array.from(newFiles)
    
    for (const file of fileArray) {
      const result = validateFile(file)
      if (result.valid) {
        valid.push(file)
      } else {
        invalid.push({ file, reason: result.message || '未知错误' })
      }
    }

    if (!multiple && valid.length > 0) {
      files.value = [valid[0]]
    } else {
      files.value.push(...valid)
    }

    return { valid, invalid }
  }

  const removeFile = (index: number) => {
    files.value.splice(index, 1)
  }

  const clearFiles = () => {
    files.value = []
    progress.value = 0
    error.value = null
  }

  const upload = async (
    uploadFn: (file: File, onProgress?: (p: number) => void) => Promise<any>
  ): Promise<{ success: any[]; failed: { file: File; error: any }[] }> => {
    if (files.value.length === 0) {
      ElMessage.warning('请选择要上传的文件')
      return { success: [], failed: [] }
    }

    uploading.value = true
    progress.value = 0
    error.value = null

    const success: any[] = []
    const failed: { file: File; error: any }[] = []
    const totalFiles = files.value.length
    let completedFiles = 0

    for (const file of files.value) {
      try {
        const result = await uploadFn(file, (p) => {
          const overallProgress = ((completedFiles + p / 100) / totalFiles) * 100
          progress.value = Math.round(overallProgress)
        })
        success.push(result)
      } catch (e: any) {
        failed.push({ file, error: e })
      }
      completedFiles++
      progress.value = Math.round((completedFiles / totalFiles) * 100)
    }

    uploading.value = false

    if (failed.length > 0) {
      error.value = `${failed.length} 个文件上传失败`
    }

    return { success, failed }
  }

  const formatSize = (bytes: number): string => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  return {
    uploading,
    progress,
    files,
    error,
    isUploading,
    hasFiles,
    addFiles,
    removeFile,
    clearFiles,
    upload,
    validateFile,
    formatSize
  }
}
