import React, { useState, useMemo } from 'react'
import Viewer from '../viewer/Viewer'
import ComparisonView from '../project/ComparisonView'
import PrintEstimateOverlay from '../export/PrintEstimateOverlay'
import WelcomeOverlay from '../feedback/WelcomeOverlay'
import ShortcutHelpDialog from './ShortcutHelpDialog'
import ModelInfoPanel from './ModelInfoPanel'
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"
import { useProject } from '../../contexts/project/ProjectProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useUnitSystem } from '../../hooks/system/useUnitSystem'
import { ChevronLeft, ChevronRight, ChevronUp, ChevronDown } from 'lucide-react'
import { evaluateSafeFormula } from '../../lib/safeFormula'

interface RenderStatusChipProps {
  loading: boolean
  progress: number
  progressPhase: string
  parts: unknown[]
  t: (key: string) => string
}

function RenderStatusChip({ loading, progress, progressPhase, parts, t }: RenderStatusChipProps) {
  if (loading) {
    const elapsed = progress > 0 ? `${Math.round(progress)}s` : ''
    const phase = progressPhase || ''
    return (
      <div className="absolute top-2 left-28 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2 pointer-events-none">
        <span className="h-2 w-2 rounded-full bg-yellow-500 motion-safe:animate-pulse" />
        {t('status.rendering')}{elapsed ? ` (${elapsed})` : ''}{phase ? ` — ${phase}` : ''}
      </div>
    )
  }

  if (parts.length > 0) {
    return (
      <div className="absolute top-2 left-28 z-10 px-3 py-1.5 bg-card border border-border rounded-lg text-xs font-medium flex items-center gap-2 pointer-events-none">
        <span className="h-2 w-2 rounded-full bg-green-500" />
        {t('status.ready')}
      </div>
    )
  }

  return null
}

interface ComparisonSlot {
  id: string
  [key: string]: unknown
}

interface StudioMainViewProps {
  compareMode?: boolean
  comparisonSlots?: ComparisonSlot[]
  onAddComparisonSlot?: () => void
  onRemoveComparisonSlot?: (slotId: string) => void
  consoleSize?: number
  consoleCollapsed?: boolean
  onConsoleResize?: (size: number) => void
  onToggleConsole?: () => void
}

export default function StudioMainView({ compareMode, comparisonSlots, onAddComparisonSlot, onRemoveComparisonSlot, consoleSize, consoleCollapsed, onConsoleResize, onToggleConsole }: StudioMainViewProps) {
  const {
    viewerRef, consoleRef,
    parts, colors, wireframe, boundingBox, loading, progress, progressPhase,
    animating, setAnimating, mode, params,
    printEstimate, setPrintEstimate,
    assemblyActive, highlightedParts, visibleParts,
    headDiffMode, headParts,
    hoveredParam,
    cachedVariants,
    logs,
    orthoCamera, setOrthoCamera,
    clippingEnabled, clippingAxis, clippingPosition,
    measureMode, measurements, setMeasurements,
    explodeFactor,
    lightIntensity, environmentPreset,
    thicknessData,
    overhangData,
    shortcutHelpOpen, setShortcutHelpOpen,
    manifest, projectSlug,
    stressData, stressSimulationActive, handleRunFEA,
    physicsJobId, physicsProgress, physicsFrames, handleRunPhysics,
    optimizationJobId, optimizationProgress, optimizationLogs, handleOptimizeTopology
  } = useProject()

  const { t } = useLanguage()
  const { unit, format: formatDim, formatVolume } = useUnitSystem()
  const [estimateOpen, setEstimateOpen] = useState(true)
  const [consoleExpanded, setConsoleExpanded] = useState(false)

  // Compute total individual piece count from part_quantities formulas
  const totalPieceCount = useMemo(() => {
    try {
      const modes = (manifest as Record<string, unknown>)?.modes as Array<Record<string, unknown>> | undefined
      if (!modes) return undefined
      const activeMode = modes.find(m => m.id === mode)
      if (!activeMode) return undefined
      const pqMap = activeMode.part_quantities as Record<string, string | number> | undefined
      if (!pqMap) return undefined
      const modeParts = activeMode.parts as string[] | undefined
      if (!modeParts) return undefined
      let total = 0
      for (const partId of modeParts) {
        const formula = pqMap[partId]
        if (formula == null) { total += 1; continue }
        if (typeof formula === 'number') { total += formula; continue }
        try {
          const result = evaluateSafeFormula(String(formula), params)
          total += typeof result === 'number' ? result : Number(result)
        } catch { total += 1 }
      }
      return total > 0 ? Math.round(total) : undefined
    } catch { return undefined }
  }, [manifest, mode, params])

  // Only show the estimate toggle when there's something to show and manifest allows it
  const pe = printEstimate as Record<string, unknown>
  const estimateDisabled = (manifest?.print_estimation as Record<string, unknown> | undefined)?.enabled === false
  // Welcome overlay: show once per project if manifest declares welcome.enabled
  const welcomeData = React.useMemo(() => {
    try {
      const proj = (manifest as Record<string, unknown>)?.project
      if (!proj || typeof proj !== 'object') return null
      const w = (proj as Record<string, unknown>).welcome
      if (!w || typeof w !== 'object' || !(w as Record<string, unknown>).enabled) return null
      return w as Record<string, unknown>
    } catch { return null }
  }, [manifest])
  const [welcomeDismissed] = useState(() => {
    try { return !!localStorage.getItem(`yantra4d-welcome-${projectSlug}`) } catch { return true }
  })
  const showWelcome = welcomeData !== null && !welcomeDismissed

  const hasEstimate = !estimateDisabled
    && ((pe?.total?.volumeMm3 ?? pe?.volumeMm3 ?? 0) > 0)

  // Last log line for collapsed console preview
  const lastLogLine = typeof logs === 'string'
    ? logs.trim().split('\n').pop() || ''
    : ''

  const viewerContent = compareMode && comparisonSlots && comparisonSlots.length > 0 ? (
    <div className="relative h-full">
      <ComparisonView
        slots={comparisonSlots as never}
        onRemoveSlot={onRemoveComparisonSlot!}
        onAddCurrent={onAddComparisonSlot!}
        colors={colors}
        wireframe={wireframe}
        mode={mode}
      />
    </div>
  ) : (
    <div className="relative h-full" aria-busy={loading}>
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
        headDiffMode={headDiffMode}
        headParts={headParts}
        hoveredParam={hoveredParam}
        cachedVariants={cachedVariants}
        orthoCamera={orthoCamera}
        setOrthoCamera={setOrthoCamera}
        clippingEnabled={clippingEnabled}
        clippingAxis={clippingAxis}
        clippingPosition={clippingPosition}
        measureMode={measureMode}
        onMeasure={(m: unknown) => setMeasurements((prev: unknown[]) => [...prev, m])}
        measurements={measurements}
        explodeFactor={explodeFactor}
        lightIntensity={lightIntensity}
        environmentPreset={environmentPreset}
        thicknessData={thicknessData}
        overhangData={overhangData}
        stressData={stressData}
        physicsFrames={physicsFrames}
        formatDimension={formatDim}
        unit={unit}
      />
      <RenderStatusChip loading={loading} progress={progress} progressPhase={progressPhase} parts={parts} t={t} />
      {/* FEA Overlay Trigger */}
      {mode && parts.length > 0 && !loading && (
        <div className="absolute bottom-4 left-4 z-20 flex flex-col gap-2">
          {physicsJobId ? (
            <div className="px-3 py-1.5 text-xs font-semibold rounded shadow bg-card border border-border">
              Simulating Physics... {Math.round(physicsProgress)}%
            </div>
          ) : (
            <button 
              onClick={handleRunPhysics}
              disabled={physicsFrames !== null}
              className={`px-3 py-1.5 text-xs font-semibold rounded shadow transition-colors ${physicsFrames !== null ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground hover:bg-muted border border-border'}`}
            >
              {physicsFrames !== null ? 'Physics Baked' : 'Run Full Physics'}
            </button>
          )}

          <button 
            onClick={handleRunFEA}
            disabled={stressSimulationActive}
            className={`px-3 py-1.5 text-xs font-semibold rounded shadow transition-colors ${stressSimulationActive ? 'bg-primary text-primary-foreground' : 'bg-card text-foreground hover:bg-muted border border-border'}`}
          >
            {stressSimulationActive ? 'FEA Stress Active' : 'Show Stress Map (Fast)'}
          </button>
          
          {/* Topo Optimization UI */}
          {optimizationJobId ? (
            <div className="px-3 py-1.5 text-xs font-semibold rounded shadow bg-purple-900 border border-purple-500 text-white flex flex-col gap-1 max-w-[200px]">
              <div>AI Optimizer... {Math.round(optimizationProgress)}%</div>
              {optimizationLogs.length > 0 && (
                <div className="text-[10px] opacity-80 truncate">
                  {optimizationLogs[optimizationLogs.length - 1]}
                </div>
              )}
            </div>
          ) : (
            <button 
              onClick={handleOptimizeTopology}
              className="px-3 py-1.5 text-xs font-semibold rounded shadow bg-purple-600 text-white hover:bg-purple-500 border border-purple-400 transition-colors"
            >
              AI Topo Optimization
            </button>
          )}

        </div>
      )}
      {!loading && parts.length > 0 && (
        <ModelInfoPanel printEstimate={printEstimate as never} partCount={parts.length} totalPieceCount={totalPieceCount} />
      )}
      {/* Accessible live region for render status and model summary */}
      <div aria-live="polite" className="sr-only" role="status">
        {loading ? 'Rendering in progress' : parts.length > 0 ? (
          <>
            Render complete.
            {printEstimate && (() => {
              const pe = printEstimate as Record<string, unknown>
              const total = pe.total as Record<string, unknown> | undefined
              const bbox = (total?.boundingBox ?? pe.boundingBox) as Record<string, number> | undefined
              const vol = (total?.volumeMm3 ?? pe.volumeMm3 ?? 0) as number
              return bbox ? ` ${t('a11y.model_summary', {
                parts: parts.length,
                width: formatDim(bbox.width ?? 0),
                height: formatDim(bbox.height ?? 0),
                depth: formatDim(bbox.depth ?? 0),
                volume: formatVolume(vol),
              } as never)}` : ''
            })()}
          </>
        ) : ''}
      </div>
    </div>
  )

  const consoleContent = (
    <div className="flex h-full border-t border-border">
      {/* Console logs — φ dominant within row (≈61.8% of row width) */}
      <div
        ref={consoleRef as React.RefObject<HTMLDivElement>}
        className="bg-muted p-4 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap min-w-0"
        style={{ flex: 1.618 }}
        role="log"
        aria-live="polite"
        aria-label="Render console"
      >
        {logs as React.ReactNode}
      </div>

      {/* Collapse/expand toggle tab */}
      {hasEstimate && (
        <div className="flex items-stretch">
          <button
            onClick={() => setEstimateOpen(o => !o)}
            className="w-8 min-w-[44px] bg-muted hover:bg-accent border-l border-border flex flex-col items-center justify-center gap-1 text-muted-foreground hover:text-foreground transition-colors py-2"
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
        <div className="shrink-0 bg-card border-l border-border overflow-y-auto" style={{ flex: 1, minWidth: '200px', maxWidth: '240px' }}>
          <PrintEstimateOverlay
            volumeMm3={((printEstimate as Record<string, unknown>)?.total as Record<string, unknown> | undefined)?.volumeMm3 as number ?? (printEstimate as Record<string, unknown>)?.volumeMm3 as number}
            boundingBox={((printEstimate as Record<string, unknown>)?.total as Record<string, unknown> | undefined)?.boundingBox as never ?? (printEstimate as Record<string, unknown>)?.boundingBox as never}
            perPartData={(printEstimate as Record<string, unknown>)?.parts as never}
            inline
          />
        </div>
      )}
    </div>
  )

  return (
    <div className="flex-1 relative flex flex-col min-h-0">
      {showWelcome && (
        <WelcomeOverlay slug={projectSlug} welcome={welcomeData as never} />
      )}
      {/* Desktop: resizable vertical layout */}
      <div className="hidden lg:flex flex-col flex-1 min-h-0">
        <ResizablePanelGroup
          orientation="vertical"
          onLayoutChanged={(panelLayout: Record<string, number>) => {
            if (!consoleCollapsed && panelLayout["console"] != null) {
              onConsoleResize?.(panelLayout["console"])
            }
          }}
        >
          {/* Viewer panel */}
          <ResizablePanel id="viewer" defaultSize={consoleCollapsed ? 100 : (100 - (consoleSize || 30))} minSize={40}>
            {viewerContent}
          </ResizablePanel>

          {/* Console panel */}
          {!consoleCollapsed && (
            <>
              <ResizableHandle withHandle orientation="vertical" />
              <ResizablePanel id="console" defaultSize={consoleSize || 30} minSize={10} maxSize={50}>
                {consoleContent}
              </ResizablePanel>
            </>
          )}
        </ResizablePanelGroup>

        {/* Collapsed console bar (desktop) */}
        {consoleCollapsed && (
          <button
            onClick={onToggleConsole}
            className="w-full flex items-center justify-center gap-2 px-3 py-1.5 bg-muted text-xs font-mono text-muted-foreground hover:bg-accent border-t border-border transition-colors"
            aria-label="Expand console"
          >
            <ChevronUp className="h-3 w-3 shrink-0" />
            <span className="font-medium text-foreground">Console</span>
            <span className="truncate max-w-xs text-left">{lastLogLine}</span>
          </button>
        )}
      </div>

      {/* Mobile: original layout */}
      <div className="lg:hidden flex flex-col flex-1 min-h-0">
        {/* 3D Viewport — φ dominant (≈61.8% of vertical space) */}
        <div className="relative min-h-0" style={{ flex: 1.618 }}>
          {viewerContent}
        </div>

        {/* Mobile: collapsed console bar (tap to expand) */}
        <div className="border-t border-border">
          <button
            onClick={() => setConsoleExpanded(e => !e)}
            className="w-full flex items-center gap-2 px-3 py-2 bg-muted text-xs font-mono text-muted-foreground hover:bg-accent transition-colors min-h-[44px]"
            aria-expanded={consoleExpanded}
            aria-label="Toggle console panel"
          >
            {consoleExpanded ? <ChevronDown className="h-3 w-3 shrink-0" /> : <ChevronUp className="h-3 w-3 shrink-0" />}
            <span className="font-medium text-foreground">Console</span>
            <span className="truncate flex-1 text-left">{lastLogLine}</span>
          </button>
          {consoleExpanded && (
            <div className="flex flex-col max-h-[40vh] landscape:max-h-[25vh]">
              <div
                ref={consoleRef as React.RefObject<HTMLDivElement>}
                className="bg-muted px-3 py-2 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap max-h-[30vh] landscape:max-h-[20vh]"
                role="log"
                aria-live="polite"
                aria-label="Render console"
              >
                {logs as React.ReactNode}
              </div>
              {hasEstimate && (
                <div className="bg-card border-t border-border overflow-y-auto" style={{ maxHeight: '15vh' }}>
                  <PrintEstimateOverlay
                    volumeMm3={((printEstimate as Record<string, unknown>)?.total as Record<string, unknown> | undefined)?.volumeMm3 as number ?? (printEstimate as Record<string, unknown>)?.volumeMm3 as number}
                    boundingBox={((printEstimate as Record<string, unknown>)?.total as Record<string, unknown> | undefined)?.boundingBox as never ?? (printEstimate as Record<string, unknown>)?.boundingBox as never}
                    perPartData={(printEstimate as Record<string, unknown>)?.parts as never}
                    inline
                  />
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <ShortcutHelpDialog open={shortcutHelpOpen} onClose={() => setShortcutHelpOpen(false)} />
    </div>
  )
}
