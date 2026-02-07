import { useEffect } from 'react'

/**
 * Hook that registers global keyboard shortcuts for the studio.
 *
 * Shortcuts:
 * - Cmd/Ctrl+Z: undo parameters
 * - Cmd/Ctrl+Shift+Z: redo parameters
 * - Cmd/Ctrl+Enter: trigger render
 * - Escape (while loading): cancel render
 * - Cmd/Ctrl+1..N: switch to mode N
 *
 * @param {object} options
 * @param {function} options.onUndo - callback for undo
 * @param {function} options.onRedo - callback for redo
 * @param {function} options.onRender - callback to trigger render
 * @param {function} options.onCancelRender - callback to cancel render
 * @param {function} options.onSwitchMode - callback receiving mode id string
 * @param {boolean} options.loading - whether a render is in progress
 * @param {Array} options.modes - available modes from manifest
 */
export function useKeyboardShortcuts({
  onUndo,
  onRedo,
  onRender,
  onCancelRender,
  onSwitchMode,
  loading,
  modes,
}) {
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (mod && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        onUndo?.()
        return
      } else if (mod && e.key === 'z' && e.shiftKey) {
        e.preventDefault()
        onRedo?.()
        return
      } else if (mod && e.key === 'Enter') {
        e.preventDefault()
        onRender?.()
      } else if (e.key === 'Escape' && loading) {
        onCancelRender?.()
      } else if (mod && modes?.length > 0) {
        const num = parseInt(e.key, 10)
        if (num >= 1 && num <= modes.length) {
          e.preventDefault()
          onSwitchMode?.(modes[num - 1].id)
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onUndo, onRedo, onRender, onCancelRender, onSwitchMode, loading, modes])
}
