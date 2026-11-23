import { Button } from '@/components/ui/button'
import { Plus, X, Copy } from 'lucide-react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import Viewer from '../viewer/Viewer'

interface ComparisonSlot {
  id: string
  label?: string
  /** The slot's number, fixed when it is added; the position is the fallback. */
  n?: number
  parts: unknown[]
  params: Record<string, unknown>
}

interface ComparisonViewProps {
  slots: ComparisonSlot[]
  onRemoveSlot: (id: string) => void
  onAddCurrent: () => void
  /** False while there is no rendered model to snapshot (nothing rendered yet, or a render in flight). */
  canAddCurrent?: boolean
  colors: Record<string, string>
  wireframe: boolean
  mode: string
}

/** The most variations shown side by side. */
export const MAX_COMPARISON_SLOTS = 4

/**
 * Side-by-side comparison of up to four parameter variations.
 * Each slot holds a snapshot of parts + params and its own viewer; the
 * cameras are independent (owner ruling 2026-11-22: compare ships without a
 * one-camera promise, so there is no "sync camera" control).
 */
export default function ComparisonView({ slots, onRemoveSlot, onAddCurrent, canAddCurrent = true, colors, wireframe, mode }: ComparisonViewProps) {
  const { t } = useLanguage()

  if (!slots || slots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 p-6 text-center">
        <Copy className="h-8 w-8 text-muted-foreground" aria-hidden="true" />
        <p className="text-sm font-medium text-foreground">{t('compare.empty')}</p>
        <p className="max-w-sm text-sm text-muted-foreground">{t('compare.empty_hint')}</p>
        <Button
          variant="outline"
          onClick={onAddCurrent}
          disabled={!canAddCurrent}
          aria-describedby={canAddCurrent ? undefined : 'compare-add-needs-render'}
          className="gap-2 min-h-[44px]"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t('compare.add_current')}
        </Button>
        {!canAddCurrent && (
          <p id="compare-add-needs-render" className="text-xs text-muted-foreground">
            {t('compare.add_needs_render')}
          </p>
        )}
      </div>
    )
  }

  const gridCols = slots.length <= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-2'

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-2 border-b border-border bg-card">
        <span className="text-sm font-medium">{t('compare.title')}</span>
        <span className="font-mono text-xs text-muted-foreground">({slots.length}/{MAX_COMPARISON_SLOTS})</span>
        <div className="flex-1" />
        {slots.length < MAX_COMPARISON_SLOTS && (
          <Button
            variant="outline"
            size="sm"
            onClick={onAddCurrent}
            disabled={!canAddCurrent}
            title={canAddCurrent ? undefined : t('compare.add_needs_render')}
            className="h-auto min-h-[44px] gap-1 text-xs md:h-8 md:min-h-0"
          >
            <Plus className="h-3 w-3" aria-hidden="true" />
            {t('compare.add_current')}
          </Button>
        )}
      </div>

      <div className={`flex-1 min-h-0 grid ${gridCols} gap-1 p-1`}>
        {slots.map((slot, idx) => {
          const label = slot.label || t('compare.variation', { n: slot.n ?? idx + 1 })
          return (
            // The slot's name and its remove control sit in a bar of their
            // own above the viewer. They used to float over the viewer's
            // corner, where the viewer's own controls (the ortho toggle at
            // top-2 left-14, z-10) covered the remove button and took its
            // clicks in every browser.
            <section
              key={slot.id}
              aria-label={label}
              data-testid="comparison-slot"
              className="flex min-h-0 flex-col overflow-hidden rounded border border-border bg-background"
            >
              <div className="flex shrink-0 items-center gap-1 border-b border-border bg-card pl-2">
                <span className="min-w-0 flex-1 truncate font-mono text-xs">{label}</span>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="h-11 w-11 shrink-0 md:h-7 md:w-7"
                  onClick={() => onRemoveSlot(slot.id)}
                  aria-label={t('compare.remove', { label })}
                  title={t('compare.remove', { label })}
                >
                  <X className="h-3.5 w-3.5" aria-hidden="true" />
                </Button>
              </div>
              <div className="relative min-h-[200px] flex-1">
                <Viewer
                  parts={slot.parts}
                  colors={colors}
                  wireframe={wireframe}
                  loading={false}
                  mode={mode}
                  params={slot.params}
                />
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
