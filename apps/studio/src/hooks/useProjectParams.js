import { useState, useEffect, useCallback, useRef } from 'react'
import { toast } from 'sonner'
import { useManifest } from '../contexts/ManifestProvider'
import { useLanguage } from '../contexts/LanguageProvider'
import { useUndoRedo } from './useUndoRedo'
import { useLocalStoragePersistence } from './useLocalStoragePersistence'
import { useShareableUrl, getSharedParams } from './useShareableUrl'
import { useConstraints } from './useConstraints'
import { useHashNavigation, parseHash, buildHash } from './useHashNavigation'
import { useImageExport } from './useImageExport'
import { useRender } from './useRender'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'

const RENDER_DEBOUNCE_MS = 500

function safeParse(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

/**
 * Core parametric state: mode, params, colors, wireframe, animation,
 * presets, undo/redo, constraints, persistence, hash navigation,
 * render orchestration, keyboard shortcuts, and image export.
 */
export function useProjectParams({ viewerRef }) {
  const { t } = useLanguage()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, getCameraViews, projectSlug, presets } = useManifest()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()
  const modes = manifest.modes

  const initialHash = parseHash(window.location.hash, presets, modes)
  const initialPresetValues = initialHash.preset?.values || {}

  const [mode, setModeState] = useState(() => initialHash.mode?.id || (modes.length > 0 ? modes[0].id : null))

  const sharedParams = getSharedParams()

  const [params, setParams, { undo: undoParams, redo: redoParams, canUndo, canRedo }] = useUndoRedo(() => {
    const stored = safeParse(`${projectSlug}-params`, defaultParams)
    return { ...defaultParams, ...stored, ...initialPresetValues, ...sharedParams }
  })
  const [colors, setColors] = useState(() => ({
    ...defaultColors,
    ...safeParse(`${projectSlug}-colors`, {})
  }))
  const [activePresetId, setActivePresetId] = useState(() => initialHash.preset?.id || presets[0]?.id || null)
  const [gridPresetId, setGridPresetId] = useState(manifest.grid_presets?.default || Object.keys(manifest.grid_presets || {}).find(k => k !== 'default'))
  const [wireframe, setWireframe] = useState(false)
  const [boundingBox, setBoundingBox] = useState(false)
  const [animating, setAnimating] = useState(false)
  const [printEstimate, setPrintEstimate] = useState(null)
  const [exportFormat, setExportFormat] = useState('stl')

  const consoleRef = useRef(null)

  // Constraints
  const { violations: constraintViolations, byParam: constraintsByParam, hasErrors: constraintErrors } = useConstraints(manifest.constraints, params)

  // Shareable URL
  const { copyShareUrl } = useShareableUrl({ params, mode, projectSlug, defaultParams })

  // Hash navigation
  const handleHashChange = (parsed) => {
    if (parsed.mode) setModeState(parsed.mode.id)
    if (parsed.preset) {
      setActivePresetId(parsed.preset.id)
      setParams(prev => ({ ...prev, ...parsed.preset.values }))
    }
  }

  const { currentView, isDemo } = useHashNavigation({
    presets,
    modes,
    projectSlug,
    onHashChange: handleHashChange,
  })

  const isGridMode = (modeId) => {
    if (!modes || modes.length === 0) return false
    const m = modes.find(md => md.id === modeId)
    return m?.estimate?.formula === 'grid'
  }

  const setMode = (newMode) => {
    setModeState(newMode)
    setAnimating(false)
    if (isGridMode(newMode)) {
      const defaultGridPreset = manifest.grid_presets?.default || 'rendering'
      const presetValues = manifest.grid_presets?.[defaultGridPreset]?.values
      if (presetValues) {
        setParams(prev => ({ ...prev, ...presetValues }))
        setGridPresetId(defaultGridPreset)
      }
    }
    const presetId = activePresetId || presets[0]?.id
    if (presetId) {
      window.location.hash = buildHash(projectSlug, presetId, newMode)
    }
  }

  // Persistence
  useLocalStoragePersistence(`${projectSlug}-params`, params)
  useLocalStoragePersistence(`${projectSlug}-colors`, colors)
  useLocalStoragePersistence(`${projectSlug}-mode`, mode, { debounce: 0, serialize: false })

  // Render cache key
  const getCacheKey = useCallback((m, p) => {
    const keyObj = { mode: m }
    for (const param of manifest.parameters) {
      if (p[param.id] !== undefined) keyObj[param.id] = p[param.id]
    }
    return JSON.stringify(keyObj)
  }, [manifest])

  // Render hook
  const {
    parts,
    setParts,
    logs,
    setLogs,
    loading,
    progress,
    progressPhase,
    checkCache,
    showConfirmDialog,
    pendingEstimate,
    handleGenerate,
    handleCancelGenerate,
    handleConfirmRender,
    handleCancelRender,
  } = useRender({ mode, params, manifest, t, getCacheKey, project: projectSlug })

  // Auto-scroll console
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  // Revoke old blob URLs
  useEffect(() => {
    return () => {
      parts.forEach(p => { if (p.url?.startsWith('blob:')) URL.revokeObjectURL(p.url) })
    }
  }, [parts])

  // Image export
  const cameraViews = getCameraViews()
  const { handleExportImage, handleExportAllViews } = useImageExport({
    viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews
  })

  // Grid preset toggle
  const handleGridPresetToggle = () => {
    const presetKeys = Object.keys(manifest.grid_presets || {}).filter(k => k !== 'default')
    const currentIndex = presetKeys.indexOf(gridPresetId)
    const nextId = presetKeys[(currentIndex + 1) % presetKeys.length]
    setGridPresetId(nextId)
    const gp = manifest.grid_presets?.[nextId]
    if (gp) {
      setParams(prev => ({ ...prev, ...gp.values }))
    }
  }

  // Apply preset
  const handleApplyPreset = (preset) => {
    const defaultGridPreset = manifest.grid_presets?.default || 'rendering'
    setParams(prev => {
      const gridValues = manifest.grid_presets?.[defaultGridPreset]?.values || {}
      return { ...prev, ...preset.values, ...gridValues }
    })
    setActivePresetId(preset.id)
    setGridPresetId(defaultGridPreset)
    window.location.hash = buildHash(projectSlug, preset.id, mode)
  }

  // Debounced auto-generate with cache check
  useEffect(() => {
    if (!modes || modes.length === 0) return
    const visibilityParams = manifest.parameters.filter(
      p => p.group === 'visibility' && (p.visible_in_modes || []).includes(mode)
    )
    if (visibilityParams.length > 0 && visibilityParams.every(p => !params[p.id])) {
      return
    }
    if (constraintErrors) return
    const cacheKey = getCacheKey(mode, params)
    const cached = checkCache(cacheKey)
    if (cached) {
      setParts(cached)
      toast.info(t('toast.cache_hit'), { duration: 1500 })
      return
    }
    const timer = setTimeout(() => {
      handleGenerate()
    }, RENDER_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [params, mode, getCacheKey, manifest]) // eslint-disable-line react-hooks/exhaustive-deps

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onUndo: undoParams,
    onRedo: redoParams,
    onRender: handleGenerate,
    onCancelRender: handleCancelGenerate,
    onSwitchMode: setMode,
    loading,
    modes,
  })

  return {
    // Navigation
    currentView, isDemo,
    // Manifest
    manifest, getLabel, projectSlug, presets, cameraViews,
    getDefaultParams, getDefaultColors,
    // Mode & params
    mode, setMode, params, setParams,
    colors, setColors,
    wireframe, setWireframe,
    boundingBox, setBoundingBox,
    animating, setAnimating,
    // Undo/redo
    undoParams, redoParams, canUndo, canRedo,
    // Render
    parts, logs, setLogs, loading, progress, progressPhase,
    showConfirmDialog, pendingEstimate,
    handleGenerate, handleCancelGenerate, handleConfirmRender, handleCancelRender,
    // Presets
    handleApplyPreset, handleGridPresetToggle,
    // Constraints
    constraintViolations, constraintsByParam, constraintErrors,
    // Export
    exportFormat, setExportFormat,
    handleExportImage, handleExportAllViews,
    // Print estimate
    printEstimate, setPrintEstimate,
    // Share
    copyShareUrl,
    // Refs
    consoleRef,
  }
}
