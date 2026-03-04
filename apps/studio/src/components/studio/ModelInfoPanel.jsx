import { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useUnitSystem } from '../../hooks/system/useUnitSystem'

/**
 * ModelInfoPanel — compact collapsible card showing model geometry stats.
 * Displays dimensions (W×D×H), volume, triangle count, and part count.
 */
export default function ModelInfoPanel({ printEstimate, partCount, triangleCount }) {
  const { t } = useLanguage()
  const { format: formatDim, formatVolume } = useUnitSystem()
  const [open, setOpen] = useState(true)

  const bbox = printEstimate?.total?.boundingBox ?? printEstimate?.boundingBox
  const vol = printEstimate?.total?.volumeMm3 ?? printEstimate?.volumeMm3 ?? 0
  const triCount = printEstimate?.total?.triangleCount ?? triangleCount ?? 0

  if (!bbox && vol <= 0) return null

  return (
    <div className="absolute top-2 right-2 z-10 sm:top-auto sm:bottom-2 sm:right-2" style={{ maxWidth: '200px' }}>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 px-2 py-1 text-xs font-medium bg-card/90 border border-border rounded-t-md hover:bg-accent transition-colors backdrop-blur-sm w-full"
        aria-expanded={open}
      >
        {open ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronRight className="h-3 w-3 shrink-0" />}
        {t('info.title')}
      </button>

      {open && (
        <div className="bg-card/90 border border-t-0 border-border rounded-b-md px-2 py-1.5 text-xs space-y-0.5 backdrop-blur-sm">
          {bbox && (
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">{t('info.dimensions')}</span>
              <span className="font-mono text-right">
                {formatDim(bbox.width ?? 0)} × {formatDim(bbox.depth ?? 0)} × {formatDim(bbox.height ?? 0)}
              </span>
            </div>
          )}
          {vol > 0 && (
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">{t('info.volume')}</span>
              <span className="font-mono">{formatVolume(vol)}</span>
            </div>
          )}
          {triCount > 0 && (
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">{t('info.triangles')}</span>
              <span className="font-mono">{triCount.toLocaleString()}</span>
            </div>
          )}
          {partCount > 0 && (
            <div className="flex justify-between gap-2">
              <span className="text-muted-foreground">{t('info.parts')}</span>
              <span className="font-mono">{partCount}</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
