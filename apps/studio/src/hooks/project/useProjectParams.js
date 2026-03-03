import { useState, useEffect, useCallback, useRef } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useUndoRedo } from '../editor/useUndoRedo'
import { useLocalStoragePersistence } from '../system/useLocalStoragePersistence'
import { useShareableUrl, getSharedParams } from './useShareableUrl'
import { useConstraints } from '../editor/useConstraints'
import { useHashNavigation, parseHash, buildHash } from '../system/useHashNavigation'
import { useImageExport } from '../render/useImageExport'
import { useRender } from '../render/useRender'
import { useKeyboardShortcuts } from '../editor/useKeyboardShortcuts'

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

  const location = useLocation()
  const navigate = useNavigate()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()
  const modes = manifest.modes

  const initialHash = parseHash(location.pathname, presets, modes)
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
  const [orthoCamera, setOrthoCamera] = useState(false)
  const [clippingEnabled, setClippingEnabled] = useState(false)
  const [clippingAxis, setClippingAxis] = useState('z')
  const [clippingPosition, setClippingPosition] = useState(0.5)
  const [measureMode, setMeasureMode] = useState(false)
  const [measurements, setMeasurements] = useState([])
  const [explodeFactor, setExplodeFactor] = useState(0)
  const [lightIntensity, setLightIntensity] = useState(1.0)
  const [environmentPreset, setEnvironmentPreset] = useState('city')
  const [thicknessData, setThicknessData] = useState(null)
  const [overhangData, setOverhangData] = useState(null)
  const [overhangEnabled, setOverhangEnabled] = useState(false)
  const [overhangThreshold, setOverhangThreshold] = useState(45)
  const [printEstimate, setPrintEstimate] = useState(null)
  const [exportFormat, setExportFormat] = useState('stl')
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false)

  // 3D Git Diff Mode state
  const [headDiffMode, setHeadDiffMode] = useState(false)
  const [headParts, setHeadParts] = useState([])
  const [loadingHeadDiff, setLoadingHeadDiff] = useState(false)

  const consoleRef = useRef(null)

  // Constraints
  const { violations: constraintViolations, byParam: constraintsByParam, hasErrors: constraintErrors } = useConstraints(manifest.constraints, params)

  // Shareable URL
  const { copyShareUrl } = useShareableUrl({ params, mode, projectSlug, defaultParams })

  // Hash navigation — only re-apply preset values when the preset actually
  // changes.  During auto-redirect (e.g. /project/test → /project/test/small/cup),
  // the preset stays the same as the one already applied during initialisation,
  // so we skip the redundant (and destructive, for ?p= shared params) setParams.
  const handleHashChange = (parsed) => {
    const newMode = parsed.mode ? parsed.mode.id : mode
    const modeChanged = parsed.mode && parsed.mode.id !== mode

    if (modeChanged) setModeState(newMode)

    const newPresetId = parsed.preset ? parsed.preset.id : activePresetId
    const presetChanged = parsed.preset && parsed.preset.id !== activePresetId

    if (presetChanged) setActivePresetId(newPresetId)

    if (modeChanged || presetChanged) {
      setParams(prev => {
        const next = { ...prev }

        // 1. Clean up parameters that shouldn't leak into the new mode
        if (manifest?.parameters) {
          manifest.parameters.forEach(p => {
            if (p.visible_in_modes && !p.visible_in_modes.includes(newMode)) {
              next[p.id] = p.default !== undefined ? p.default : 0
            }
          })
        }

        // 2. Apply new preset values
        if (presetChanged && parsed.preset) {
          Object.assign(next, parsed.preset.values)
        }

        return next
      })
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

    // Ensure active preset is valid for the new mode
    let validPresetId = activePresetId
    const currentPreset = presets.find(p => p.id === activePresetId)

    if (currentPreset && currentPreset.visible_in_modes && !currentPreset.visible_in_modes.includes(newMode)) {
      // Preset is not valid for this mode, find the first one that is
      const fallbackPreset = presets.find(p => !p.visible_in_modes || p.visible_in_modes.includes(newMode))
      if (fallbackPreset) {
        validPresetId = fallbackPreset.id
        setActivePresetId(validPresetId)
        setParams(prev => ({ ...prev, ...fallbackPreset.values }))
      }
    }

    const presetIdToHash = validPresetId || presets[0]?.id
    if (presetIdToHash) {
      navigate(buildHash(projectSlug, newMode, presetIdToHash))
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
    navigate(buildHash(projectSlug, mode, preset.id))
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

  // Wrapper that clears data when disabling overhang
  const handleSetOverhangEnabled = useCallback((val) => {
    setOverhangEnabled(val)
    if (!val) setOverhangData(null)
  }, [])

  // Overhang analysis — fetch when enabled
  useEffect(() => {
    if (!overhangEnabled || !projectSlug || parts.length === 0) return
    let cancelled = false
    const apiBase = import.meta.env.VITE_API_BASE || ''
    fetch(`${apiBase}/api/projects/${projectSlug}/analyze/overhang`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threshold_deg: overhangThreshold }),
    })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Overhang analysis failed')))
      .then(data => {
        if (!cancelled) setOverhangData(data.analysis)
      })
      .catch(err => {
        if (!cancelled) {
          console.warn('[Overhang]', err.message)
          setOverhangData(null)
        }
      })
    return () => { cancelled = true }
  }, [overhangEnabled, overhangThreshold, projectSlug, parts.length])

  // Keyboard shortcuts
  useKeyboardShortcuts({
    onUndo: undoParams,
    onRedo: redoParams,
    onRender: handleGenerate,
    onCancelRender: handleCancelGenerate,
    onSwitchMode: setMode,
    onToggleOrtho: () => setOrthoCamera(v => !v),
    onToggleClipping: () => setClippingEnabled(v => !v),
    onToggleMeasure: () => setMeasureMode(v => !v),
    onToggleShortcutHelp: () => setShortcutHelpOpen(v => !v),
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
    orthoCamera, setOrthoCamera,
    clippingEnabled, setClippingEnabled,
    clippingAxis, setClippingAxis,
    clippingPosition, setClippingPosition,
    measureMode, setMeasureMode,
    measurements, setMeasurements,
    explodeFactor, setExplodeFactor,
    lightIntensity, setLightIntensity,
    environmentPreset, setEnvironmentPreset,
    thicknessData, setThicknessData,
    overhangData, setOverhangData,
    overhangEnabled, setOverhangEnabled: handleSetOverhangEnabled,
    overhangThreshold, setOverhangThreshold,
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
    // 3D Diff state
    headDiffMode, setHeadDiffMode,
    headParts, setHeadParts,
    loadingHeadDiff, setLoadingHeadDiff,
    // Share
    copyShareUrl,
    // Shortcut help
    shortcutHelpOpen, setShortcutHelpOpen,
    // Refs
    consoleRef,
  }
}
