import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface AppTask {
  id: string
  name: string
  type: 'testset' | 'evaluation' | 'document'
  progress: number
  status: 'pending' | 'running' | 'completed' | 'failed'
  time: string
  targetId?: string
  error?: string
}

export const useTaskStore = defineStore('task', () => {
  const tasks = ref<AppTask[]>([])

  const activeTaskCount = computed(() => tasks.value.filter(t => t.status === 'running' || t.status === 'pending').length)
  
  const hasActiveTasks = computed(() => activeTaskCount.value > 0)

  function addTask(task: Omit<AppTask, 'time'>) {
    const now = new Date()
    const timeString = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`
    
    // Check if task already exists
    const existingIndex = tasks.value.findIndex(t => t.id === task.id)
    if (existingIndex >= 0) {
      tasks.value[existingIndex] = { ...tasks.value[existingIndex], ...task }
    } else {
      tasks.value.unshift({
        ...task,
        time: timeString
      })
    }
  }

  function updateTask(id: string, updates: Partial<AppTask>) {
    const index = tasks.value.findIndex(t => t.id === id)
    if (index >= 0) {
      tasks.value[index] = { ...tasks.value[index], ...updates }
    }
  }

  function removeTask(id: string) {
    tasks.value = tasks.value.filter(t => t.id !== id)
  }

  function clearCompleted() {
    tasks.value = tasks.value.filter(t => t.status === 'running' || t.status === 'pending')
  }

  function getTask(id: string) {
    return tasks.value.find(t => t.id === id)
  }

  return {
    tasks,
    activeTaskCount,
    hasActiveTasks,
    addTask,
    updateTask,
    removeTask,
    clearCompleted,
    getTask
  }
})
