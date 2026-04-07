import { format, formatDistanceToNow, parseISO } from 'date-fns'
import { zhCN } from 'date-fns/locale'

export const formatDate = (date: string | Date, formatStr: string = 'yyyy-MM-dd'): string => {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    return format(d, formatStr, { locale: zhCN })
  } catch {
    return '-'
  }
}

export const formatDateTime = (date: string | Date): string => {
  return formatDate(date, 'yyyy-MM-dd HH:mm:ss')
}

export const formatRelativeTime = (date: string | Date): string => {
  try {
    const d = typeof date === 'string' ? parseISO(date) : date
    return formatDistanceToNow(d, { addSuffix: true, locale: zhCN })
  } catch {
    return '-'
  }
}

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

export const formatDuration = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const secs = seconds % 60

  if (hours > 0) {
    return `${hours}小时${minutes}分${secs}秒`
  }
  if (minutes > 0) {
    return `${minutes}分${secs}秒`
  }
  return `${secs}秒`
}

export const formatNumber = (num: number, decimals: number = 2): string => {
  return num.toFixed(decimals)
}

export const formatPercent = (num: number, decimals: number = 2): string => {
  return (num * 100).toFixed(decimals) + '%'
}

export const formatScore = (score: number): string => {
  if (score >= 0.8) return '优秀'
  if (score >= 0.6) return '良好'
  if (score >= 0.4) return '一般'
  return '较差'
}

export const getScoreColor = (score: number): string => {
  if (score >= 0.8) return '#67C23A'
  if (score >= 0.6) return '#E6A23C'
  return '#F56C6C'
}
