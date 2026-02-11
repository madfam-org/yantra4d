import { useState, useCallback, useRef } from 'react'

const MAX_HISTORY = 50

/**
 * Hook providing undo/redo for a state value.
 * Returns [value, setValue, { undo, redo, canUndo, canRedo }].
 *
 * setValue pushes to history. undo/redo navigate history without pushing.
 * Both update the same React state but through separate code paths.
 */
export function useUndoRedo(initialValue) {
  const resolved = typeof initialValue === 'function' ? initialValue() : initialValue
  const [value, setValueRaw] = useState(resolved)
  const [canUndo, setCanUndo] = useState(false)
  const [canRedo, setCanRedo] = useState(false)

  const historyRef = useRef([resolved])
  const indexRef = useRef(0)

  const syncFlags = useCallback(() => {
    setCanUndo(indexRef.current > 0)
    setCanRedo(indexRef.current < historyRef.current.length - 1)
  }, [])

  // setValue: pushes a new entry to history (normal user action)
  // options: { history: boolean } - if false, update state but skip history push
  const setValue = useCallback((updater, options = {}) => {
    const { history = true } = options
    const prev = historyRef.current[indexRef.current]
    const next = typeof updater === 'function' ? updater(prev) : updater

    if (JSON.stringify(prev) === JSON.stringify(next)) return

    if (history) {
      // Truncate redo history and push
      const newHistory = historyRef.current.slice(0, indexRef.current + 1)
      newHistory.push(next)
      if (newHistory.length > MAX_HISTORY) newHistory.shift()
      historyRef.current = newHistory
      indexRef.current = newHistory.length - 1
    }

    setValueRaw(next)
    syncFlags()
  }, [syncFlags])

  // undo: move back in history (no push)
  const undo = useCallback(() => {
    if (indexRef.current <= 0) return
    indexRef.current -= 1
    const val = historyRef.current[indexRef.current]
    setValueRaw(val)
    syncFlags()
  }, [syncFlags])

  // redo: move forward in history (no push)
  const redo = useCallback(() => {
    if (indexRef.current >= historyRef.current.length - 1) return
    indexRef.current += 1
    const val = historyRef.current[indexRef.current]
    setValueRaw(val)
    syncFlags()
  }, [syncFlags])

  return [value, setValue, { undo, redo, canUndo, canRedo }]
}
