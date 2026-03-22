import { createContext, useContext, useRef, useState, useEffect } from 'react'
import { useProjectParams } from '../../hooks/project/useProjectParams'
import { useProjectActions } from '../../hooks/project/useProjectActions'
import { useAssemblyGuide } from '../../hooks/editor/useAssemblyGuide'
import { useManifest } from './ManifestProvider'
import { useLanguage } from '../system/LanguageProvider'
import SplashScreen from '../../components/feedback/SplashScreen'

const ProjectContext = createContext(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useProject() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider')
  }
  return context
}

// Inner component to handle strict state reset on project change
function ProjectProviderContent({ children }) {
  const viewerRef = useRef(null)
  const { projectSlug } = useManifest()
  const { t } = useLanguage()

  // 1. Core parametric state (mode, params, render loop, etc.)
  const projectParams = useProjectParams({ viewerRef })

  // 2. Assembly guide state
  const assembly = useAssemblyGuide(viewerRef)

  // 3. User actions (verify, download, export, etc.)
  const actions = useProjectActions({
    parts: projectParams.parts,
    mode: projectParams.mode,
    projectSlug: projectSlug,
    t,
    setLogs: projectParams.setLogs,
    getDefaultParams: projectParams.getDefaultParams,
    getDefaultColors: projectParams.getDefaultColors,
    setParams: projectParams.setParams,
    setColors: projectParams.setColors,
    setWireframe: projectParams.setWireframe,
    copyShareUrl: projectParams.copyShareUrl,
    exportFormat: projectParams.exportFormat,
    handleExportImage: projectParams.handleExportImage,
    handleExportAllViews: projectParams.handleExportAllViews,
    params: projectParams.params,
    manifest: projectParams.manifest,
  })

  const value = {
    // Refs
    viewerRef,
    consoleRef: projectParams.consoleRef,

    // Core State
    currentView: projectParams.currentView,
    isDemo: projectParams.isDemo,
    manifest: projectParams.manifest,
    projectSlug: projectParams.projectSlug,
    presets: projectParams.presets,
    cameraViews: projectParams.cameraViews,
    getLabel: projectParams.getLabel,

    // Params & Mode
    mode: projectParams.mode,
    setMode: projectParams.setMode,
    params: projectParams.params,
    setParams: projectParams.setParams,
    colors: projectParams.colors,
    setColors: projectParams.setColors,
    wireframe: projectParams.wireframe,
    setWireframe: projectParams.setWireframe,
    boundingBox: projectParams.boundingBox,
    setBoundingBox: projectParams.setBoundingBox,
    animating: projectParams.animating,
    setAnimating: projectParams.setAnimating,
    orthoCamera: projectParams.orthoCamera,
    setOrthoCamera: projectParams.setOrthoCamera,
    clippingEnabled: projectParams.clippingEnabled,
    setClippingEnabled: projectParams.setClippingEnabled,
    clippingAxis: projectParams.clippingAxis,
    setClippingAxis: projectParams.setClippingAxis,
    clippingPosition: projectParams.clippingPosition,
    setClippingPosition: projectParams.setClippingPosition,
    measureMode: projectParams.measureMode,
    setMeasureMode: projectParams.setMeasureMode,
    measurements: projectParams.measurements,
    setMeasurements: projectParams.setMeasurements,
    explodeFactor: projectParams.explodeFactor,
    setExplodeFactor: projectParams.setExplodeFactor,
    lightIntensity: projectParams.lightIntensity,
    setLightIntensity: projectParams.setLightIntensity,
    environmentPreset: projectParams.environmentPreset,
    setEnvironmentPreset: projectParams.setEnvironmentPreset,
    thicknessData: projectParams.thicknessData,
    setThicknessData: projectParams.setThicknessData,
    overhangData: projectParams.overhangData,
    setOverhangData: projectParams.setOverhangData,
    overhangEnabled: projectParams.overhangEnabled,
    setOverhangEnabled: projectParams.setOverhangEnabled,
    overhangThreshold: projectParams.overhangThreshold,
    setOverhangThreshold: projectParams.setOverhangThreshold,

    // Undo/Redo
    undoParams: projectParams.undoParams,
    redoParams: projectParams.redoParams,
    canUndo: projectParams.canUndo,
    canRedo: projectParams.canRedo,

    // Render State
    parts: projectParams.parts,
    logs: projectParams.logs,
    loading: projectParams.loading,
    progress: projectParams.progress,
    progressPhase: projectParams.progressPhase,
    showConfirmDialog: projectParams.showConfirmDialog,
    pendingEstimate: projectParams.pendingEstimate,
    printEstimate: projectParams.printEstimate,
    setPrintEstimate: projectParams.setPrintEstimate,
    headDiffMode: projectParams.headDiffMode,
    setHeadDiffMode: projectParams.setHeadDiffMode,
    headParts: projectParams.headParts,
    setHeadParts: projectParams.setHeadParts,
    loadingHeadDiff: projectParams.loadingHeadDiff,
    setLoadingHeadDiff: projectParams.setLoadingHeadDiff,

    // Constraints
    constraintViolations: projectParams.constraintViolations,
    constraintsByParam: projectParams.constraintsByParam,
    constraintErrors: projectParams.constraintErrors,

    // Export
    exportFormat: projectParams.exportFormat,
    setExportFormat: projectParams.setExportFormat,

    // Shortcut help
    shortcutHelpOpen: projectParams.shortcutHelpOpen,
    setShortcutHelpOpen: projectParams.setShortcutHelpOpen,

    // Parameter preview
    hoveredParam: projectParams.hoveredParam,
    setHoveredParamId: projectParams.setHoveredParamId,
    cachedVariants: projectParams.cachedVariants,
    preRenderStatus: projectParams.preRenderStatus,

    // Assembly
    assemblyActive: assembly.assemblyActive,
    highlightedParts: assembly.highlightedParts,
    visibleParts: assembly.visibleParts,
    handleHighlightParts: assembly.handleHighlightParts,
    handleSetAssemblyCamera: assembly.handleSetAssemblyCamera,
    handleAssemblyStepChange: assembly.handleAssemblyStepChange,
    assemblyEditorOpen: assembly.assemblyEditorOpen,
    setAssemblyEditorOpen: assembly.setAssemblyEditorOpen,

    // Actions
    handleGenerate: projectParams.handleGenerate,
    handleCancelGenerate: projectParams.handleCancelGenerate,
    handleConfirmRender: projectParams.handleConfirmRender,
    handleCancelRender: projectParams.handleCancelRender,
    handleVerify: actions.handleVerify,
    handleDownloadStl: actions.handleDownloadStl,
    handleReset: actions.handleReset,
    handleShare: actions.handleShare,
    shareToast: actions.shareToast,
    handleApplyPreset: projectParams.handleApplyPreset,
    handleGridPresetToggle: projectParams.handleGridPresetToggle,
    handleExportImage: actions.handleExportImage,
    handleExportAllViews: actions.handleExportAllViews,
  }

  return (
    <ProjectContext.Provider value={value}>
      {children}
    </ProjectContext.Provider>
  )
}

export function ProjectProvider({ children }) {
  const { projectSlug, manifest } = useManifest()

  // Gate: only block when the manifest belongs to a DIFFERENT project than
  // the one requested via URL.  This prevents the auto-render from firing with
  // the wrong (fallback) manifest while the correct one is being fetched.
  // We deliberately do NOT gate on generic `loading` so that views which don't
  // depend on the manifest (e.g. ProjectsView) can render immediately.
  const manifestSlug = manifest.project?.slug || ''
  const manifestStale = manifestSlug && projectSlug && manifestSlug !== projectSlug

  // Smooth exit: hold splash visible for 300ms fade-out after manifest loads.
  // setState in effect is intentional here — it synchronizes with the timer
  // (an external system) and only fires on the stale→ready edge transition.
  const [showSplash, setShowSplash] = useState(manifestStale)
  const [exiting, setExiting] = useState(false)

  // Synchronize splash visibility with manifestStale transitions.
  // setState in effect is intentional: this is an edge-triggered transition
  // that coordinates with a timer (external system) for the exit animation.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (manifestStale) {
      setShowSplash(true)
      setExiting(false)
    } else if (showSplash) {
      setExiting(true)
      const t = setTimeout(() => {
        setShowSplash(false)
        setExiting(false)
      }, 300)
      return () => clearTimeout(t)
    }
  }, [manifestStale]) // eslint-disable-line react-hooks/exhaustive-deps
  /* eslint-enable react-hooks/set-state-in-effect */

  if (showSplash) {
    return <SplashScreen exiting={exiting} />
  }

  // Force full remount when project changes OR when the real manifest loads
  // (replacing the fallback). This ensures hooks reinitialize with correct defaults.
  return (
    <ProjectProviderContent key={`${projectSlug}:${manifestSlug}`}>
      {children}
    </ProjectProviderContent>
  )
}
