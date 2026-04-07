import { ref, onMounted, onUnmounted } from 'vue'

interface LazyLoadOptions {
  rootMargin?: string
  threshold?: number
}

export function useImageLazy(options: LazyLoadOptions = {}) {
  const {
    rootMargin = '50px',
    threshold = 0.1
  } = options

  const observer = ref<IntersectionObserver | null>(null)
  const loadedImages = ref<Set<string>>(new Set())

  const observe = (el: HTMLImageElement) => {
    if (!observer.value) {
      observer.value = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              const img = entry.target as HTMLImageElement
              const src = img.dataset.src
              
              if (src && !loadedImages.value.has(src)) {
                img.src = src
                loadedImages.value.add(src)
                observer.value?.unobserve(img)
              }
            }
          })
        },
        {
          rootMargin,
          threshold
        }
      )
    }
    
    if (el.dataset.src) {
      observer.value.observe(el)
    }
  }

  const unobserve = (el: HTMLImageElement) => {
    if (observer.value) {
      observer.value.unobserve(el)
    }
  }

  const disconnect = () => {
    if (observer.value) {
      observer.value.disconnect()
    }
  }

  const isLoaded = (src: string): boolean => {
    return loadedImages.value.has(src)
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    observe,
    unobserve,
    disconnect,
    isLoaded,
    loadedImages
  }
}

export function useLazyLoadRef() {
  const elementRef = ref<HTMLElement | null>(null)
  const isVisible = ref(false)
  
  let observer: IntersectionObserver | null = null

  const startObserving = () => {
    if (!elementRef.value) return

    observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          isVisible.value = entry.isIntersecting
        })
      },
      { threshold: 0.1 }
    )

    observer.observe(elementRef.value)
  }

  const stopObserving = () => {
    if (observer) {
      observer.disconnect()
      observer = null
    }
  }

  onMounted(() => {
    startObserving()
  })

  onUnmounted(() => {
    stopObserving()
  })

  return {
    elementRef,
    isVisible,
    startObserving,
    stopObserving
  }
}
