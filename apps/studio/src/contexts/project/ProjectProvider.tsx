import { createContext, useContext, useRef, useState, useEffect } from 'react'
import { useProjectParams } from '../../hooks/project/useProjectParams'
import { useProjectActions } from '../../hooks/project/useProjectActions'
import { useAssemblyGuide } from '../../hooks/editor/useAssemblyGuide'
import { useManifest } from './ManifestProvider'
import { useLanguage } from '../system/LanguageProvider'
import SplashScreen from '../../components/feedback/SplashScreen'

type ProjectParamsReturn = ReturnType<typeof useProjectParams>
type ProjectActionsReturn = ReturnType<typeof useProjectActions>
type AssemblyGuideReturn = ReturnType<typeof useAssemblyGuide>

interface ViewerRefHandle {
  setCameraView?: (view: string) => void
  captureSnapshot?: () => string
  animateTo?: (position: number[], target: number[]) => void
  [key: string]: unknown
}

export interface ProjectContextValue {
  viewerRef: React.RefObject<ViewerRefHandle | null>
  consoleRef: ProjectParamsReturn['consoleRef']

  currentView: ProjectParamsReturn['currentView']
  isDemo: ProjectParamsReturn['isDemo']
  manifest: ProjectParamsReturn['manifest']
  projectSlug: ProjectParamsReturn['projectSlug']
  presets: ProjectParamsReturn['presets']
  cameraViews: ProjectParamsReturn['cameraViews']
  getLabel: ProjectParamsReturn['getLabel']

  mode: ProjectParamsReturn['mode']
  setMode: ProjectParamsReturn['setMode']
  params: ProjectParamsReturn['params']
  setParams: ProjectParamsReturn['setParams']
  colors: ProjectParamsReturn['colors']
  setColors: ProjectParamsReturn['setColors']
  wireframe: ProjectParamsReturn['wireframe']
  setWireframe: ProjectParamsReturn['setWireframe']
  boundingBox: ProjectParamsReturn['boundingBox']
  setBoundingBox: ProjectParamsReturn['setBoundingBox']
  animating: ProjectParamsReturn['animating']
  setAnimating: ProjectParamsReturn['setAnimating']
  orthoCamera: ProjectParamsReturn['orthoCamera']
  setOrthoCamera: ProjectParamsReturn['setOrthoCamera']
  clippingEnabled: ProjectParamsReturn['clippingEnabled']
  setClippingEnabled: ProjectParamsReturn['setClippingEnabled']
  clippingAxis: ProjectParamsReturn['clippingAxis']
  setClippingAxis: ProjectParamsReturn['setClippingAxis']
  clippingPosition: ProjectParamsReturn['clippingPosition']
  setClippingPosition: ProjectParamsReturn['setClippingPosition']
  measureMode: ProjectParamsReturn['measureMode']
  setMeasureMode: ProjectParamsReturn['setMeasureMode']
  measurements: ProjectParamsReturn['measurements']
  setMeasurements: ProjectParamsReturn['setMeasurements']
  explodeFactor: ProjectParamsReturn['explodeFactor']
  setExplodeFactor: ProjectParamsReturn['setExplodeFactor']
  lightIntensity: ProjectParamsReturn['lightIntensity']
  setLightIntensity: ProjectParamsReturn['setLightIntensity']
  environmentPreset: ProjectParamsReturn['environmentPreset']
  setEnvironmentPreset: ProjectParamsReturn['setEnvironmentPreset']
  thicknessData: ProjectParamsReturn['thicknessData']
  setThicknessData: ProjectParamsReturn['setThicknessData']
  overhangData: ProjectParamsReturn['overhangData']
  setOverhangData: ProjectParamsReturn['setOverhangData']
  overhangEnabled: ProjectParamsReturn['overhangEnabled']
  setOverhangEnabled: ProjectParamsReturn['setOverhangEnabled']
  overhangThreshold: ProjectParamsReturn['overhangThreshold']
  setOverhangThreshold: ProjectParamsReturn['setOverhangThreshold']

  undoParams: ProjectParamsReturn['undoParams']
  redoParams: ProjectParamsReturn['redoParams']
  canUndo: ProjectParamsReturn['canUndo']
  canRedo: ProjectParamsReturn['canRedo']

  parts: ProjectParamsReturn['parts']
  logs: ProjectParamsReturn['logs']
  loading: ProjectParamsReturn['loading']
  progress: ProjectParamsReturn['progress']
  progressPhase: ProjectParamsReturn['progressPhase']
  showConfirmDialog: ProjectParamsReturn['showConfirmDialog']
  pendingEstimate: ProjectParamsReturn['pendingEstimate']
  printEstimate: ProjectParamsReturn['printEstimate']
  setPrintEstimate: ProjectParamsReturn['setPrintEstimate']
  headDiffMode: ProjectParamsReturn['headDiffMode']
  setHeadDiffMode: ProjectParamsReturn['setHeadDiffMode']
  headParts: ProjectParamsReturn['headParts']
  setHeadParts: ProjectParamsReturn['setHeadParts']
  loadingHeadDiff: ProjectParamsReturn['loadingHeadDiff']
  setLoadingHeadDiff: ProjectParamsReturn['setLoadingHeadDiff']

  constraintViolations: ProjectParamsReturn['constraintViolations']
  constraintsByParam: ProjectParamsReturn['constraintsByParam']
  constraintErrors: ProjectParamsReturn['constraintErrors']

  exportFormat: ProjectParamsReturn['exportFormat']
  setExportFormat: ProjectParamsReturn['setExportFormat']

  shortcutHelpOpen: ProjectParamsReturn['shortcutHelpOpen']
  setShortcutHelpOpen: ProjectParamsReturn['setShortcutHelpOpen']

  hoveredParam: ProjectParamsReturn['hoveredParam']
  setHoveredParamId: ProjectParamsReturn['setHoveredParamId']
  cachedVariants: ProjectParamsReturn['cachedVariants']
  preRenderStatus: ProjectParamsReturn['preRenderStatus']

  assemblyActive: AssemblyGuideReturn['assemblyActive']
  highlightedParts: AssemblyGuideReturn['highlightedParts']
  visibleParts: AssemblyGuideReturn['visibleParts']
  handleHighlightParts: AssemblyGuideReturn['handleHighlightParts']
  handleSetAssemblyCamera: AssemblyGuideReturn['handleSetAssemblyCamera']
  handleAssemblyStepChange: AssemblyGuideReturn['handleAssemblyStepChange']
  assemblyEditorOpen: AssemblyGuideReturn['assemblyEditorOpen']
  setAssemblyEditorOpen: AssemblyGuideReturn['setAssemblyEditorOpen']

  handleGenerate: ProjectParamsReturn['handleGenerate']
  handleCancelGenerate: ProjectParamsReturn['handleCancelGenerate']
  handleConfirmRender: ProjectParamsReturn['handleConfirmRender']
  handleCancelRender: ProjectParamsReturn['handleCancelRender']
  handleVerify: ProjectActionsReturn['handleVerify']
  handleDownloadStl: ProjectActionsReturn['handleDownloadStl']
  handleReset: ProjectActionsReturn['handleReset']
  handleShare: ProjectActionsReturn['handleShare']
  shareToast: ProjectActionsReturn['shareToast']
  handleApplyPreset: ProjectParamsReturn['handleApplyPreset']
  handleGridPresetToggle: ProjectParamsReturn['handleGridPresetToggle']
  handleExportImage: ProjectActionsReturn['handleExportImage']
  handleExportAllViews: ProjectActionsReturn['handleExportAllViews']
}

interface ProjectProviderProps {
  children: React.ReactNode
}

const ProjectContext = createContext<ProjectContextValue | null>(null)

export function useProject(): ProjectContextValue {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider')
  }
  return context
}

// Inner component to handle strict state reset on project change
function ProjectProviderContent({ children }: ProjectProviderProps) {
  const viewerRef = useRef<ViewerRefHandle | null>(null)
  const { projectSlug } = useManifest()
  const { t } = useLanguage()

  // 1. Core parametric state (mode, params, render loop, etc.)
  const projectParams = useProjectParams({ viewerRef: viewerRef as React.RefObject<never> })

  // 2. Assembly guide state
  const assembly = useAssemblyGuide(viewerRef as React.RefObject<never>)

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

  const value: ProjectContextValue = {
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

export function ProjectProvider({ children }: ProjectProviderProps) {
  const { projectSlug, manifest, manifestError } = useManifest() as ReturnType<typeof useManifest> & { manifestError: string | null }

  // Gate: only block when the manifest belongs to a DIFFERENT project than
  // the one requested via URL.  This prevents the auto-render from firing with
  // the wrong (fallback) manifest while the correct one is being fetched.
  // We deliberately do NOT gate on generic `loading` so that views which don't
  // depend on the manifest (e.g. ProjectsView) can render immediately.
  const manifestSlug = manifest.project?.slug || ''
  const manifestStale = !manifestError && manifestSlug && projectSlug && manifestSlug !== projectSlug

  // Smooth exit: hold splash visible for 300ms fade-out after manifest loads.
  // setState in effect is intentional here — it synchronizes with the timer
  // (an external system) and only fires on the stale→ready edge transition.
  const [showSplash, setShowSplash] = useState(!!manifestStale)
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
