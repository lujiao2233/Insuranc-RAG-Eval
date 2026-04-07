const TOKEN_KEY = 'rag_eval_token'

export const tokenStorage = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },

  set(token: string): void {
    try {
      localStorage.setItem(TOKEN_KEY, token)
    } catch (error) {
      console.error('Failed to save token:', error)
    }
  },

  remove(): void {
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch (error) {
      console.error('Failed to remove token:', error)
    }
  }
}

export const setLocalStorage = <T>(key: string, value: T): void => {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch (error) {
    console.error('Failed to save to localStorage:', error)
  }
}

export const getLocalStorage = <T>(key: string): T | null => {
  try {
    const item = localStorage.getItem(key)
    return item ? JSON.parse(item) : null
  } catch {
    return null
  }
}

export const removeLocalStorage = (key: string): void => {
  try {
    localStorage.removeItem(key)
  } catch (error) {
    console.error('Failed to remove from localStorage:', error)
  }
}
