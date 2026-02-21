import { useRef } from 'react'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { useThemeAndLanguage } from './useThemeAndLanguage'
import { useProjectParams } from '../project/useProjectParams'
import { useProjectActions } from '../project/useProjectActions'
import { useAssemblyGuide } from '../editor/useAssemblyGuide'

/**
 * Thin composition layer that wires all sub-hooks together.
 * Returns the same API shape as before so callers don't change.
 */
export function useAppState() {
  const viewerRef = useRef(null)

  // Core parametric state, render, presets, constraints, etc.
  // This hook also owns useHashNavigation and provides currentView.
  const projectParams = useProjectParams({ viewerRef })

  // Get manifest for project name (for title sync)
  const { manifest } = useManifest()

  // Theme, language, OAuth, title sync
  const {
    theme, cycleTheme,
    language, setLanguage, toggleLanguage, t,
  } = useThemeAndLanguage({
    currentView: projectParams.currentView,
    projectName: manifest.project.name,
  })

  // Assembly guide state
  const assembly = useAssemblyGuide(viewerRef)

  // User-facing actions (verify, download, reset, share, export)
  const actions = useProjectActions({
    parts: projectParams.parts,
    mode: projectParams.mode,
    projectSlug: projectParams.projectSlug,
    t,
    setLogs: projectParams.setLogs,
    getDefaultParams: projectParams.getDefaultParams,
    getDefaultColors: projectParams.getDefaultColors,
    setParams: projectParams.setParams,
    setColors: projectParams.setColors,
    setWireframe: projectParams.setWireframe,
    setBoundingBox: projectParams.setBoundingBox,
    copyShareUrl: projectParams.copyShareUrl,
    handleExportImage: projectParams.handleExportImage,
    handleExportAllViews: projectParams.handleExportAllViews,
  })

  return {
    // View state
    currentView: projectParams.currentView,
    isDemo: projectParams.isDemo,
    // Theme/lang
    theme, cycleTheme,
    language, setLanguage, toggleLanguage, t,
    // Manifest data
    manifest: projectParams.manifest,
    getLabel: projectParams.getLabel,
    projectSlug: projectParams.projectSlug,
    presets: projectParams.presets,
    cameraViews: projectParams.cameraViews,
    // Mode & params
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
    // Undo/redo
    undoParams: projectParams.undoParams,
    redoParams: projectParams.redoParams,
    canUndo: projectParams.canUndo,
    canRedo: projectParams.canRedo,
    // Share
    handleShare: actions.handleShare,
    shareToast: actions.shareToast,
    // Render
    parts: projectParams.parts,
    logs: projectParams.logs,
    loading: projectParams.loading,
    progress: projectParams.progress,
    progressPhase: projectParams.progressPhase,
    showConfirmDialog: projectParams.showConfirmDialog,
    pendingEstimate: projectParams.pendingEstimate,
    handleGenerate: projectParams.handleGenerate,
    handleCancelGenerate: projectParams.handleCancelGenerate,
    handleConfirmRender: projectParams.handleConfirmRender,
    handleCancelRender: projectParams.handleCancelRender,
    // Actions
    handleVerify: actions.handleVerify,
    handleDownloadStl: actions.handleDownloadStl,
    handleReset: actions.handleReset,
    handleApplyPreset: projectParams.handleApplyPreset,
    handleGridPresetToggle: projectParams.handleGridPresetToggle,
    handleExportImage: actions.handleExportImage,
    handleExportAllViews: actions.handleExportAllViews,
    // Export
    exportFormat: projectParams.exportFormat,
    setExportFormat: projectParams.setExportFormat,
    // Constraints
    constraintViolations: projectParams.constraintViolations,
    constraintsByParam: projectParams.constraintsByParam,
    constraintErrors: projectParams.constraintErrors,
    // Print estimate
    printEstimate: projectParams.printEstimate,
    setPrintEstimate: projectParams.setPrintEstimate,
    // Assembly guide
    assemblyActive: assembly.assemblyActive,
    highlightedParts: assembly.highlightedParts,
    visibleParts: assembly.visibleParts,
    handleHighlightParts: assembly.handleHighlightParts,
    handleSetAssemblyCamera: assembly.handleSetAssemblyCamera,
    handleAssemblyStepChange: assembly.handleAssemblyStepChange,
    assemblyEditorOpen: assembly.assemblyEditorOpen,
    setAssemblyEditorOpen: assembly.setAssemblyEditorOpen,
    // Refs
    viewerRef,
    consoleRef: projectParams.consoleRef,
  }
}
