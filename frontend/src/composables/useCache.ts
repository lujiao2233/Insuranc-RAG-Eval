import { ref, onMounted, onUnmounted } from 'vue'

interface CacheItem<T> {
  data: T
  timestamp: number
  ttl: number
}

export function useCache<T>(key: string, ttl: number = 5 * 60 * 1000) {
  const cache = ref<Map<string, CacheItem<T>>>(new Map())
  const loading = ref(false)
  const error = ref<any>(null)

  const getCacheKey = (k: string) => `${key}:${k}`

  const isExpired = (item: CacheItem<T>): boolean => {
    return Date.now() - item.timestamp > item.ttl
  }

  const get = (k: string = 'default'): T | null => {
    const cacheKey = getCacheKey(k)
    const item = cache.value.get(cacheKey)
    
    if (!item) return null
    if (isExpired(item)) {
      cache.value.delete(cacheKey)
      return null
    }
    
    return item.data
  }

  const set = (data: T, k: string = 'default'): void => {
    const cacheKey = getCacheKey(k)
    cache.value.set(cacheKey, {
      data,
      timestamp: Date.now(),
      ttl
    })
  }

  const has = (k: string = 'default'): boolean => {
    const cacheKey = getCacheKey(k)
    const item = cache.value.get(cacheKey)
    return item !== undefined && !isExpired(item)
  }

  const remove = (k: string = 'default'): void => {
    const cacheKey = getCacheKey(k)
    cache.value.delete(cacheKey)
  }

  const clear = (): void => {
    cache.value.clear()
  }

  const fetch = async (
    fetchFn: () => Promise<T>,
    k: string = 'default',
    forceRefresh: boolean = false
  ): Promise<T> => {
    if (!forceRefresh && has(k)) {
      return get(k) as T
    }

    loading.value = true
    error.value = null

    try {
      const data = await fetchFn()
      set(data, k)
      return data
    } catch (e) {
      error.value = e
      throw e
    } finally {
      loading.value = false
    }
  }

  const getOrFetch = async (
    fetchFn: () => Promise<T>,
    k: string = 'default'
  ): Promise<T> => {
    return fetch(fetchFn, k, false)
  }

  const refresh = async (
    fetchFn: () => Promise<T>,
    k: string = 'default'
  ): Promise<T> => {
    return fetch(fetchFn, k, true)
  }

  return {
    cache,
    loading,
    error,
    get,
    set,
    has,
    remove,
    clear,
    fetch,
    getOrFetch,
    refresh
  }
}
