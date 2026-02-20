import { useState } from 'react'
import Viewer from '../viewer/Viewer'
import PrintEstimateOverlay from '../export/PrintEstimateOverlay'
import { useProject } from '../../contexts/ProjectProvider'
import { useLanguage } from '../../contexts/LanguageProvider'
import { ChevronLeft, ChevronRight } from 'lucide-react'

function RenderStatusChip({ loading, progress, progressPhase, parts, t }) {
  if (loading) {
    const elapsed = progress > 0 ? `${Math.round(progress)}s` : ''
    const phase = progressPhase || ''
    return (
      <div className="absolute top-2 left-2 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2 pointer-events-none">
        <span className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
        {t('status.rendering')}{elapsed ? ` (${elapsed})` : ''}{phase ? ` — ${phase}` : ''}
      </div>
    )
  }

  if (parts.length > 0) {
    return (
      <div className="absolute top-2 left-2 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2 pointer-events-none">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        {t('status.ready')}
      </div>
    )
  }

  return null
}

export default function StudioMainView() {
  const {
    viewerRef, consoleRef,
    parts, colors, wireframe, boundingBox, loading, progress, progressPhase,
    animating, setAnimating, mode, params,
    printEstimate, setPrintEstimate,
    assemblyActive, highlightedParts, visibleParts,
    logs,
  } = useProject()

  const { t } = useLanguage()
  const [estimateOpen, setEstimateOpen] = useState(true)

  // Only show the estimate toggle when there's something to show
  const hasEstimate = (printEstimate?.total?.volumeMm3 ?? printEstimate?.volumeMm3 ?? 0) > 0

  return (
    <div id="main-content" className="flex-1 relative flex flex-col min-h-0">
      {/* 3D Viewport — φ dominant (≈61.8% of vertical space) */}
      <div className="relative min-h-0" style={{ flex: 1.618 }} aria-busy={loading}>
        <Viewer
          ref={viewerRef}
          parts={parts}
          colors={colors}
          wireframe={wireframe}
          boundingBox={boundingBox}
          loading={loading}
          progress={progress}
          progressPhase={progressPhase}
          animating={animating}
          setAnimating={setAnimating}
          mode={mode}
          params={params}
          onGeometryStats={setPrintEstimate}
          assemblyActive={assemblyActive}
          highlightedParts={highlightedParts}
          visibleParts={visibleParts}
        />
        <RenderStatusChip loading={loading} progress={progress} progressPhase={progressPhase} parts={parts} t={t} />
        {/* Accessible live region for render status */}
        <div aria-live="polite" className="sr-only">
          {loading ? 'Rendering in progress' : parts.length > 0 ? 'Render complete' : ''}
        </div>
      </div>

      {/* Bottom panel — φ subordinate (≈38.2% of vertical space) with min/max height guard */}
      <div className="flex shrink-0 border-t border-border" style={{ flex: 1, minHeight: '120px', maxHeight: '280px' }}>

        {/* Console logs — φ dominant within row (≈61.8% of row width) */}
        <div
          ref={consoleRef}
          className="bg-muted p-4 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap min-w-0"
          style={{ flex: 1.618 }}
          role="log"
          aria-live="polite"
          aria-label="Render console"
        >
          {logs}
        </div>

        {/* Collapse/expand toggle tab */}
        {hasEstimate && (
          <div className="flex items-stretch">
            <button
              onClick={() => setEstimateOpen(o => !o)}
              className="w-6 bg-muted hover:bg-accent border-l border-border flex flex-col items-center justify-center gap-1 text-muted-foreground hover:text-foreground transition-colors py-2"
              title={estimateOpen ? 'Collapse estimate' : 'Expand estimate'}
              aria-expanded={estimateOpen}
              aria-label="Toggle print estimate panel"
            >
              {estimateOpen
                ? <ChevronRight className="h-3 w-3 shrink-0" />
                : (
                  <>
                    <ChevronLeft className="h-3 w-3 shrink-0" />
                    <span
                      className="text-[9px] font-medium leading-none select-none"
                      style={{ writingMode: 'vertical-rl', textOrientation: 'mixed', transform: 'rotate(180deg)' }}
                    >
                      Print Estimate
                    </span>
                  </>
                )
              }
            </button>
          </div>
        )}

        {/* Print Estimate inline panel — φ subordinate (≈38.2% of row width) with guard */}
        {hasEstimate && estimateOpen && (
          <div className="shrink-0 bg-card border-l border-border overflow-y-auto" style={{ flex: 1, minWidth: '160px', maxWidth: '240px' }}>
            <PrintEstimateOverlay
              volumeMm3={printEstimate?.total?.volumeMm3 ?? printEstimate?.volumeMm3}
              boundingBox={printEstimate?.total?.boundingBox ?? printEstimate?.boundingBox}
              perPartData={printEstimate?.parts}
              inline
            />
          </div>
        )}
      </div>
    </div>
  )
}
