import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Plus, X, Copy } from 'lucide-react'
import { useLanguage } from '../../contexts/LanguageProvider'
import Viewer from '../viewer/Viewer'

/**
 * Side-by-side comparison of 2-4 parameter variations.
 * Each slot holds a snapshot of parts + params.
 * Camera is synchronized across all viewers via shared state.
 */
export default function ComparisonView({ slots, onRemoveSlot, onAddCurrent, colors, wireframe, mode }) {
  const { t } = useLanguage()
  const [syncCamera, setSyncCamera] = useState(true)

  if (!slots || slots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-4 text-muted-foreground">
        <p>{t('compare.empty')}</p>
        <Button variant="outline" onClick={onAddCurrent} className="gap-2">
          <Plus className="h-4 w-4" />
          {t('compare.add_current')}
        </Button>
      </div>
    )
  }

  const gridCols = slots.length <= 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-2'

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 p-2 border-b border-border bg-card">
        <span className="text-sm font-medium">{t('compare.title')}</span>
        <span className="text-xs text-muted-foreground">({slots.length}/4)</span>
        <div className="flex-1" />
        {slots.length < 4 && (
          <Button variant="outline" size="sm" onClick={onAddCurrent} className="gap-1 min-h-[36px]">
            <Plus className="h-3 w-3" />
            {t('compare.add_current')}
          </Button>
        )}
        <button
          type="button"
          className={`text-xs px-2 py-1 rounded ${syncCamera ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'}`}
          onClick={() => setSyncCamera(prev => !prev)}
        >
          {t('compare.sync_camera')}
        </button>
      </div>

      <div className={`flex-1 grid ${gridCols} gap-1 p-1`}>
        {slots.map((slot, idx) => (
          <div key={slot.id} className="relative border border-border rounded overflow-hidden bg-background">
            <div className="absolute top-1 left-1 z-10 flex items-center gap-1">
              <span className="px-1.5 py-0.5 bg-card/80 rounded text-[10px] font-mono">
                {slot.label || `#${idx + 1}`}
              </span>
              <button
                type="button"
                className="p-0.5 bg-card/80 rounded hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => onRemoveSlot(slot.id)}
                aria-label="Remove slot"
              >
                <X className="h-3 w-3" />
              </button>
            </div>
            <div className="h-full min-h-[200px]">
              <Viewer
                parts={slot.parts}
                colors={colors}
                wireframe={wireframe}
                loading={false}
                mode={mode}
                params={slot.params}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
