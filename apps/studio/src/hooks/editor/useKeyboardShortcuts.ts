import { useEffect } from 'react'

interface ModeConfig {
  id: string
  [key: string]: unknown
}

interface KeyboardShortcutOptions {
  onUndo?: () => void
  onRedo?: () => void
  onRender?: () => void
  onCancelRender?: () => void
  onSwitchMode?: (modeId: string) => void
  onToggleOrtho?: () => void
  onToggleClipping?: () => void
  onToggleMeasure?: () => void
  onToggleShortcutHelp?: () => void
  loading?: boolean
  modes?: ModeConfig[]
}

/**
 * Hook that registers global keyboard shortcuts for the studio.
 *
 * Shortcuts:
 * - Cmd/Ctrl+Z: undo parameters
 * - Cmd/Ctrl+Shift+Z: redo parameters
 * - Cmd/Ctrl+Enter: trigger render
 * - Escape (while loading): cancel render
 * - Cmd/Ctrl+1..N: switch to mode N
 * - O: toggle orthographic camera
 * - C: toggle clipping plane
 * - M: toggle measure mode
 *
 * Note: [ (toggle sidebar) and ] (toggle console) are handled in App.jsx
 * since usePanelLayout lives outside ProjectProvider context.
 */
export function useKeyboardShortcuts({
  onUndo,
  onRedo,
  onRender,
  onCancelRender,
  onSwitchMode,
  onToggleOrtho,
  onToggleClipping,
  onToggleMeasure,
  onToggleShortcutHelp,
  loading,
  modes,
}: KeyboardShortcutOptions): void {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Ignore text inputs to allow native typing/undo
      const target = e.target as HTMLElement
      if (
        ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName) ||
        target.isContentEditable
      ) {
        return
      }

      const mod = e.metaKey || e.ctrlKey
      const key = e.key.toLowerCase()
      if (mod && key === 'z' && !e.shiftKey) {
        e.preventDefault()
        e.stopPropagation()
        onUndo?.()
        return
      } else if (mod && key === 'z' && e.shiftKey) {
        e.preventDefault()
        e.stopPropagation()
        onRedo?.()
        return
      } else if (mod && e.key === 'Enter') {
        e.preventDefault()
        e.stopPropagation()
        onRender?.()
      } else if (e.key === 'Escape' && loading) {
        // Escape usually doesn't need stopPropagation but good for consistency if we want to own it
        onCancelRender?.()
      } else if (!mod && key === 'o') {
        onToggleOrtho?.()
      } else if (!mod && key === 'c') {
        onToggleClipping?.()
      } else if (!mod && key === 'm') {
        onToggleMeasure?.()
      } else if (e.key === '?' && !mod) {
        onToggleShortcutHelp?.()
      } else if (mod && modes && modes.length > 0) {
        const num = parseInt(e.key, 10)
        if (num >= 1 && num <= modes.length) {
          e.preventDefault()
          e.stopPropagation()
          onSwitchMode?.(modes[num - 1].id)
        }
      }
    }

    // Use capture phase to handle events before Radix UI/other libs stop propagation
    window.addEventListener('keydown', handler, { capture: true })
    return () => window.removeEventListener('keydown', handler, { capture: true })
  }, [onUndo, onRedo, onRender, onCancelRender, onSwitchMode, onToggleOrtho, onToggleClipping, onToggleMeasure, onToggleShortcutHelp, loading, modes])
}
