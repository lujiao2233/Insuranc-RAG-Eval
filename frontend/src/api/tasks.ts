import { request } from './index'
import type { TaskStatus } from '@/types'

export const taskApi = {
  cancelTask(taskId: string): Promise<TaskStatus> {
    return request.post(`/testsets/tasks/${taskId}/cancel`)
  },

  retryTask(taskId: string): Promise<TaskStatus> {
    return request.post(`/testsets/tasks/${taskId}/retry`)
  },

  listTasks(): Promise<{ tasks: TaskStatus[] }> {
    return request.get('/testsets/tasks')
  },

  resumeTask(taskId: string): Promise<TaskStatus> {
    return request.post(`/testsets/tasks/${taskId}/resume`)
  }
}
