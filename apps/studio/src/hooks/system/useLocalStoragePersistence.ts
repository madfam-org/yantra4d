import { useEffect } from 'react'

interface PersistenceOptions {
  debounce?: number
  serialize?: boolean
}

/**
 * Debounced localStorage persistence for a value.
 * Serializes with JSON.stringify for objects, or stores raw strings.
 */
export function useLocalStoragePersistence(
  key: string,
  value: unknown,
  { debounce = 300, serialize = true }: PersistenceOptions = {}
): void {
  useEffect(() => {
    const stored = serialize ? JSON.stringify(value) : (value as string)
    if (debounce > 0) {
      const id = setTimeout(() => {
        try { localStorage.setItem(key, stored) } catch (e) { console.warn('localStorage write failed:', (e as Error).message) }
      }, debounce)
      return () => clearTimeout(id)
    }
    try { localStorage.setItem(key, stored) } catch (e) { console.warn('localStorage write failed:', (e as Error).message) }
  }, [key, value, debounce, serialize])
}
