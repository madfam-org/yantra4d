import { createContext, useContext, useRef } from 'react'
import { useProjectParams } from '../hooks/useProjectParams'
import { useProjectActions } from '../hooks/useProjectActions'
import { useAssemblyGuide } from '../hooks/useAssemblyGuide'
import { useManifest } from './ManifestProvider'
import { useLanguage } from './LanguageProvider'

const ProjectContext = createContext(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useProject() {
  const context = useContext(ProjectContext)
  if (!context) {
    throw new Error('useProject must be used within a ProjectProvider')
  }
  return context
}

export function ProjectProvider({ children }) {
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
    handleExportImage: projectParams.handleExportImage,
    handleExportAllViews: projectParams.handleExportAllViews,
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
    animating: projectParams.animating,
    setAnimating: projectParams.setAnimating,

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

    // Constraints
    constraintViolations: projectParams.constraintViolations,
    constraintsByParam: projectParams.constraintsByParam,
    constraintErrors: projectParams.constraintErrors,

    // Export
    exportFormat: projectParams.exportFormat,
    setExportFormat: projectParams.setExportFormat,

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
