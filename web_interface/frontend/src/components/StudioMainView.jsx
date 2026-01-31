import Viewer from './Viewer'
import PrintEstimateOverlay from './PrintEstimateOverlay'

export default function StudioMainView({
  viewerRef, consoleRef,
  parts, colors, wireframe, loading, progress, progressPhase,
  animating, setAnimating, mode, params,
  printEstimate, setPrintEstimate,
  logs,
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
        <PrintEstimateOverlay
          volumeMm3={printEstimate?.volumeMm3}
          boundingBox={printEstimate?.boundingBox}
        />
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
