import { ref, onUnmounted } from 'vue'

interface PollingOptions {
  interval?: number
  immediate?: boolean
  maxAttempts?: number
  onSuccess?: (data: any) => void
  onError?: (error: any) => void
  shouldStop?: (data: any) => boolean
}

export function usePolling(
  fetchFn: () => Promise<any>,
  options: PollingOptions = {}
) {
  const {
    interval = 3000,
    immediate = false,
    maxAttempts = 0,
    onSuccess,
    onError,
    shouldStop
  } = options

  const isPolling = ref(false)
  const attempts = ref(0)
  const lastResult = ref<any>(null)
  const lastError = ref<any>(null)
  
  let timer: number | null = null

  const poll = async () => {
    if (!isPolling.value) return

    try {
      const result = await fetchFn()
      lastResult.value = result
      lastError.value = null
      attempts.value++
      
      if (onSuccess) {
        onSuccess(result)
      }
      
      if (shouldStop && shouldStop(result)) {
        stop()
        return
      }
      
      if (maxAttempts > 0 && attempts.value >= maxAttempts) {
        stop()
        return
      }
      
      scheduleNext()
    } catch (error) {
      lastError.value = error
      attempts.value++
      
      if (onError) {
        onError(error)
      }
      
      if (maxAttempts > 0 && attempts.value >= maxAttempts) {
        stop()
        return
      }
      
      scheduleNext()
    }
  }

  const scheduleNext = () => {
    if (isPolling.value) {
      timer = window.setTimeout(poll, interval)
    }
  }

  const start = () => {
    if (isPolling.value) return
    
    isPolling.value = true
    attempts.value = 0
    lastResult.value = null
    lastError.value = null
    
    poll()
  }

  const stop = () => {
    isPolling.value = false
    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  const reset = () => {
    stop()
    attempts.value = 0
    lastResult.value = null
    lastError.value = null
  }

  const restart = () => {
    reset()
    start()
  }

  onUnmounted(() => {
    stop()
  })

  if (immediate) {
    start()
  }

  return {
    isPolling,
    attempts,
    lastResult,
    lastError,
    start,
    stop,
    reset,
    restart
  }
}
