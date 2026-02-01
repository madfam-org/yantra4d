import Viewer from './Viewer'
import PrintEstimateOverlay from './PrintEstimateOverlay'

function RenderStatusChip({ loading, progress, progressPhase, parts, t }) {
  if (loading) {
    const elapsed = progress > 0 ? `${Math.round(progress)}s` : ''
    const phase = progressPhase || ''
    return (
      <div className="absolute top-2 left-2 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-yellow-500 animate-pulse" />
        {t('status.rendering')}{elapsed ? ` (${elapsed})` : ''}{phase ? ` — ${phase}` : ''}
      </div>
    )
  }

  if (parts.length > 0) {
    return (
      <div className="absolute top-2 left-2 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        {t('status.ready')}
      </div>
    )
  }

  return null
}

export default function StudioMainView({
  viewerRef, consoleRef,
  parts, colors, wireframe, loading, progress, progressPhase,
  animating, setAnimating, mode, params,
  printEstimate, setPrintEstimate,
  logs, t,
}) {
  return (
    <div className="flex-1 relative flex flex-col min-h-0">
      <div className="flex-1 relative min-h-0">
        <Viewer
          ref={viewerRef}
          parts={parts}
          colors={colors}
          wireframe={wireframe}
          loading={loading}
          progress={progress}
          progressPhase={progressPhase}
          animating={animating}
          setAnimating={setAnimating}
          mode={mode}
          params={params}
          onGeometryStats={setPrintEstimate}
        />
        <RenderStatusChip loading={loading} progress={progress} progressPhase={progressPhase} parts={parts} t={t} />
        <PrintEstimateOverlay
          volumeMm3={printEstimate?.volumeMm3}
          boundingBox={printEstimate?.boundingBox}
        />
        {/* Accessible live region for render status */}
        <div aria-live="polite" className="sr-only">
          {loading ? 'Rendering in progress' : parts.length > 0 ? 'Render complete' : ''}
        </div>
      </div>

      <div
        ref={consoleRef}
        className="h-32 lg:h-48 bg-muted border-t border-border p-4 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap shrink-0"
        role="log"
        aria-live="polite"
        aria-label="Render console"
      >
        {logs}
      </div>
    </div>
  )
}
