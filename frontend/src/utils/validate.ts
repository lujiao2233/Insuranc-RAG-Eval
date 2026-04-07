export const validateEmail = (email: string): boolean => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  return re.test(email)
}

export const validatePassword = (password: string): { valid: boolean; message: string } => {
  if (password.length < 8) {
    return { valid: false, message: '密码长度至少8位' }
  }
  if (!/[A-Z]/.test(password)) {
    return { valid: false, message: '密码需包含大写字母' }
  }
  if (!/[a-z]/.test(password)) {
    return { valid: false, message: '密码需包含小写字母' }
  }
  if (!/[0-9]/.test(password)) {
    return { valid: false, message: '密码需包含数字' }
  }
  return { valid: true, message: '' }
}

export const validateUsername = (username: string): { valid: boolean; message: string } => {
  if (username.length < 3) {
    return { valid: false, message: '用户名长度至少3位' }
  }
  if (username.length > 20) {
    return { valid: false, message: '用户名长度最多20位' }
  }
  if (!/^[a-zA-Z0-9_]+$/.test(username)) {
    return { valid: false, message: '用户名只能包含字母、数字和下划线' }
  }
  return { valid: true, message: '' }
}

export const validateRequired = (value: any): boolean => {
  if (value === null || value === undefined) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (Array.isArray(value)) return value.length > 0
  return true
}

export const validateFileType = (file: File, allowedTypes: string[]): boolean => {
  const ext = file.name.split('.').pop()?.toLowerCase()
  return ext ? allowedTypes.includes(`.${ext}`) : false
}

export const validateFileSize = (file: File, maxSize: number): boolean => {
  return file.size <= maxSize
}

export const formRules = {
  required: (message: string = '此项为必填项') => ({
    required: true,
    message,
    trigger: 'blur'
  }),
  email: (message: string = '请输入有效的邮箱地址') => ({
    type: 'email',
    message,
    trigger: 'blur'
  }),
  minLength: (min: number, message?: string) => ({
    min,
    message: message || `长度至少${min}个字符`,
    trigger: 'blur'
  }),
  maxLength: (max: number, message?: string) => ({
    max,
    message: message || `长度最多${max}个字符`,
    trigger: 'blur'
  })
}
