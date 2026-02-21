import { useEffect } from 'react'

/**
 * Debounced localStorage persistence for a value.
 * Serializes with JSON.stringify for objects, or stores raw strings.
 */
export function useLocalStoragePersistence(key, value, { debounce = 300, serialize = true } = {}) {
  useEffect(() => {
    const stored = serialize ? JSON.stringify(value) : value
    if (debounce > 0) {
      const id = setTimeout(() => {
        try { localStorage.setItem(key, stored) } catch (e) { console.warn('localStorage write failed:', e.message) }
      }, debounce)
      return () => clearTimeout(id)
    }
    try { localStorage.setItem(key, stored) } catch (e) { console.warn('localStorage write failed:', e.message) }
  }, [key, value, debounce, serialize])
}
