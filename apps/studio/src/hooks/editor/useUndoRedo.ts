import { useState, useCallback, useRef } from 'react'

const MAX_HISTORY = 50

interface UndoRedoControls {
  undo: () => void
  redo: () => void
  canUndo: boolean
  canRedo: boolean
}

interface SetValueOptions {
  history?: boolean
}

type SetValueUpdater<T> = T | ((prev: T) => T)

/**
 * Hook providing undo/redo for a state value.
 * Returns [value, setValue, { undo, redo, canUndo, canRedo }].
 *
 * setValue pushes to history. undo/redo navigate history without pushing.
 * canUndo/canRedo are stored as proper React state so they are safe to read
 * during render (no ref access in render path).
 */
export function useUndoRedo<T>(initialValue: T | (() => T)): [T, (updater: SetValueUpdater<T>, options?: SetValueOptions) => void, UndoRedoControls] {
  const resolved = typeof initialValue === 'function' ? (initialValue as () => T)() : initialValue
  const [value, setValueRaw] = useState<T>(resolved)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)

  const historyRef = useRef<T[]>([resolved])
  const indexRef = useRef(0)

  const latestValueRef = useRef<T>(resolved)

  // setValue: pushes a new entry to history (normal user action)
  // options: { history: boolean } - if false, update state but skip history push
  const setValue = useCallback((updater: SetValueUpdater<T>, options: SetValueOptions = {}) => {
    const { history = true } = options

    setValueRaw(prevRaw => {
      const next = typeof updater === 'function' ? (updater as (prev: T) => T)(prevRaw) : updater

      if (JSON.stringify(prevRaw) === JSON.stringify(next)) {
        return prevRaw
      }

      if (history) {
        // Truncate redo history and push
        const newHistory = historyRef.current.slice(0, indexRef.current + 1)
        newHistory.push(next)
        if (newHistory.length > MAX_HISTORY) newHistory.shift()
        historyRef.current = newHistory
        indexRef.current = newHistory.length - 1
        setCanUndo(indexRef.current > 0)
        setCanRedo(false)
      }

      latestValueRef.current = next
      return next
    })
  }, [])

  // undo: move back in history (no push)
  const undo = useCallback(() => {
    if (indexRef.current <= 0) return
    indexRef.current -= 1
    const val = historyRef.current[indexRef.current]
    latestValueRef.current = val
    setValueRaw(val)
    setCanUndo(indexRef.current > 0)
    setCanRedo(true)
  }, [])

  // redo: move forward in history (no push)
  const redo = useCallback(() => {
    if (indexRef.current >= historyRef.current.length - 1) return
    indexRef.current += 1
    const val = historyRef.current[indexRef.current]
    latestValueRef.current = val
    setValueRaw(val)
    setCanUndo(true)
    setCanRedo(indexRef.current < historyRef.current.length - 1)
  }, [])

  return [value, setValue, { undo, redo, canUndo, canRedo }]
}
