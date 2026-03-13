import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'
import { useLanguage } from '../../contexts/system/LanguageProvider'

const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform)
const mod = isMac ? '⌘' : 'Ctrl'

const SHORTCUT_GROUPS = [
  {
    key: 'shortcuts.viewer',
    shortcuts: [
      { keys: 'O', label: 'shortcuts.ortho' },
      { keys: 'C', label: 'shortcuts.clipping' },
      { keys: 'M', label: 'shortcuts.measure' },
    ],
  },
  {
    key: 'shortcuts.editing',
    shortcuts: [
      { keys: `${mod}+Z`, label: 'shortcuts.undo' },
      { keys: `${mod}+Shift+Z`, label: 'shortcuts.redo' },
    ],
  },
  {
    key: 'shortcuts.rendering',
    shortcuts: [
      { keys: `${mod}+Enter`, label: 'shortcuts.render' },
      { keys: 'Esc', label: 'shortcuts.cancel' },
    ],
  },
  {
    key: 'shortcuts.panels',
    shortcuts: [
      { keys: '[', label: 'shortcuts.toggle_sidebar' },
      { keys: ']', label: 'shortcuts.toggle_console' },
    ],
  },
  {
    key: 'shortcuts.navigation',
    shortcuts: [
      { keys: `${mod}+1..N`, label: 'shortcuts.switch_mode' },
      { keys: '?', label: 'shortcuts.help' },
    ],
  },
]

export default function ShortcutHelpDialog({ open, onClose }) {
  const { t } = useLanguage()
  const dialogRef = useRef(null)

  useEffect(() => {
    if (!open) return
    const handler = (e) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      }
    }
    window.addEventListener('keydown', handler, { capture: true })
    return () => window.removeEventListener('keydown', handler, { capture: true })
  }, [open, onClose])

  // Focus trap: focus the dialog when opened
  useEffect(() => {
    if (open && dialogRef.current) {
      dialogRef.current.focus()
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" role="presentation" onMouseDown={onClose}>
      {/* eslint-disable-next-line jsx-a11y/no-noninteractive-element-interactions */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={t('shortcuts.title')}
        tabIndex={-1}
        className="bg-card border border-border rounded-lg shadow-xl w-full max-w-md mx-4 p-4 sm:p-6 max-h-[90dvh] overflow-y-auto outline-none"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">{t('shortcuts.title')}</h2>
          <button
            onClick={onClose}
            className="min-h-[44px] min-w-[44px] md:min-h-0 md:min-w-0 flex items-center justify-center rounded-md hover:bg-muted transition-colors"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4">
          {SHORTCUT_GROUPS.map((group) => (
            <div key={group.key}>
              <h3 className="text-sm font-medium text-muted-foreground mb-2">{t(group.key)}</h3>
              <div className="space-y-1">
                {group.shortcuts.map((shortcut) => (
                  <div
                    key={shortcut.label}
                    className="flex items-center justify-between py-1.5 min-h-[44px] md:min-h-0"
                  >
                    <span className="text-sm">{t(shortcut.label)}</span>
                    <kbd className="px-2 py-0.5 text-xs font-mono bg-muted rounded border border-border">
                      {shortcut.keys}
                    </kbd>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
