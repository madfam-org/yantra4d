import { useEffect } from 'react'

/**
 * Debounced localStorage persistence for a value.
 * Serializes with JSON.stringify for objects, or stores raw strings.
 */
export function useLocalStoragePersistence(key, value, { debounce = 300, serialize = true } = {}) {
  useEffect(() => {
    const stored = serialize ? JSON.stringify(value) : value
    if (debounce > 0) {
      const id = setTimeout(() => localStorage.setItem(key, stored), debounce)
      return () => clearTimeout(id)
    }
    localStorage.setItem(key, stored)
  }, [key, value, debounce, serialize])
}
