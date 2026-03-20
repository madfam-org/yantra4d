import { useState, useEffect, useCallback, useRef, useMemo, RefObject, Dispatch, SetStateAction } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { useManifest } from '../../contexts/project/ManifestProvider'
import { useLanguage } from '../../contexts/system/LanguageProvider'
import { useUndoRedo } from '../editor/useUndoRedo'
import { useLocalStoragePersistence } from '../system/useLocalStoragePersistence'
import { useShareableUrl, getSharedParams } from './useShareableUrl'
import { useConstraints } from '../editor/useConstraints'
import { useHashNavigation, parseHash, buildHash } from '../system/useHashNavigation'
import { apiFetch } from '../../services/core/apiClient'
import { useImageExport } from '../render/useImageExport'
import { useRender } from '../render/useRender'
import { useKeyboardShortcuts } from '../editor/useKeyboardShortcuts'
import { inferPreviewHint } from '../../lib/previewHintInference'
import { useParameterPreviewCache } from '../render/useParameterPreviewCache'

const RENDER_DEBOUNCE_MS = 500

interface ModeConfig {
  id: string
  parts: string[]
  estimate?: {
    formula?: string
    formula_vars?: string[]
    base_units?: number
  }
  [key: string]: unknown
}

interface ParamDef {
  id: string
  type: string
  default?: unknown
  group?: string
  visible_in_modes?: string[]
  label?: Record<string, string>
  min?: number
  max?: number
  preview_hint?: { type: string; axis?: string; affected_parts?: string[] }
  [key: string]: unknown
}

interface Preset {
  id: string
  values: Record<string, unknown>
  mode?: string
  visible_in_modes?: string[]
  [key: string]: unknown
}

interface Manifest {
  modes: ModeConfig[]
  parts: Array<{ id: string; render_mode: number; [key: string]: unknown }>
  parameters: ParamDef[]
  constraints?: Array<{ rule: string; message: string; severity: string; applies_to?: string[] }>
  grid_presets?: Record<string, { values?: Record<string, unknown>; default?: string; [key: string]: unknown }>
  estimate_constants?: {
    base_time: number
    per_unit: number
    per_part: number
    wasm_multiplier?: number
    warning_threshold_seconds?: number
  }
  project?: { force_backend?: boolean; hard_reload?: boolean; [key: string]: unknown }
  [key: string]: unknown
}

interface RenderPart {
  type: string
  url?: string
  download_url?: string
  blob?: Blob
  isGlb?: boolean
  [key: string]: unknown
}

interface CameraView {
  id: string
  [key: string]: unknown
}

interface ViewerRef {
  setCameraView: (view: string) => void
  captureSnapshot: () => string
}

interface HoveredParamInfo {
  paramId: string
  paramDef: ParamDef
  currentValue: unknown
  hint: { type: string; axis?: string; affected_parts?: string[] }
}

interface Violation {
  rule: string
  message: string | Record<string, string>
  severity: string
  appliesTo: string[]
}

interface CachedVariantParts {
  min?: RenderPart[]
  max?: RenderPart[]
}

interface UseProjectParamsOptions {
  viewerRef: RefObject<ViewerRef | null>
}

function safeParse<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

/**
 * Core parametric state: mode, params, colors, wireframe, animation,
 * presets, undo/redo, constraints, persistence, hash navigation,
 * render orchestration, keyboard shortcuts, and image export.
 */
export function useProjectParams({ viewerRef }: UseProjectParamsOptions) {
  const { t } = useLanguage()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, getCameraViews, projectSlug, presets } = useManifest()

  const location = useLocation()
  const navigate = useNavigate()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()
  const modes = manifest.modes

  const isHardReload = manifest.project?.hard_reload === true

  const storedModeId = !isHardReload ? safeParse<string | null>(`${projectSlug}-mode`, null) : null
  const storedPresetId = !isHardReload ? safeParse<string | null>(`${projectSlug}-preset`, null) : null

  const initialHash = parseHash(location.pathname, presets, modes, storedModeId, storedPresetId)
  const initialPresetValues = (initialHash.preset as Preset)?.values || {}

  const [mode, setModeState] = useState<string>(() => initialHash.mode?.id || (modes.length > 0 ? modes[0].id : ''))

  const sharedParams = getSharedParams()

  const [params, setParams, { undo: undoParams, redo: redoParams, canUndo, canRedo }] = useUndoRedo(() => {
    let stored: Record<string, unknown> = {}
    if (!isHardReload && storedPresetId === (initialHash.preset as Preset)?.id) {
       // Only apply localStorage parameter tweaks if we're loading the exact same preset
       // that was active when we saved them. Otherwise start fresh.
       stored = safeParse<Record<string, unknown>>(`${projectSlug}-params`, {})
    }

    // Discard stale localStorage keys that don't exist in current manifest
    const validKeys = new Set(manifest.parameters.map((p: ParamDef) => p.id))
    const filtered: Record<string, unknown> = {}
    for (const key of Object.keys(stored)) {
      if (validKeys.has(key)) filtered[key] = stored[key]
    }
    return { ...defaultParams, ...initialPresetValues, ...filtered, ...sharedParams }
  })
  const [colors, setColors] = useState<Record<string, unknown>>(() => ({
    ...defaultColors,
    ...(isHardReload ? {} : safeParse<Record<string, unknown>>(`${projectSlug}-colors`, {}))
  }))
  const [activePresetId, setActivePresetId] = useState<string | null>(() => (initialHash.preset as Preset)?.id || presets[0]?.id || null)
  const [gridPresetId, setGridPresetId] = useState<string | undefined>(
    (manifest.grid_presets?.default as string | undefined) || Object.keys(manifest.grid_presets || {}).find(k => k !== 'default')
  )
  const [wireframe, setWireframe] = useState(false)
  const [boundingBox, setBoundingBox] = useState(false)
  const [animating, setAnimating] = useState(false)
  const [orthoCamera, setOrthoCamera] = useState(false)
  const [clippingEnabled, setClippingEnabled] = useState(false)
  const [clippingAxis, setClippingAxis] = useState('z')
  const [clippingPosition, setClippingPosition] = useState(0.5)
  const [measureMode, setMeasureMode] = useState(false)
  const [measurements, setMeasurements] = useState<unknown[]>([])
  const [explodeFactor, setExplodeFactor] = useState(0)
  const [lightIntensity, setLightIntensity] = useState(1.0)
  const [environmentPreset, setEnvironmentPreset] = useState('city')
  const [thicknessData, setThicknessData] = useState<unknown>(null)
  const [overhangData, setOverhangData] = useState<unknown>(null)
  const [overhangEnabled, setOverhangEnabled] = useState(false)
  const [overhangThreshold, setOverhangThreshold] = useState(45)
  const [printEstimate, setPrintEstimate] = useState<unknown>(null)
  const [exportFormat, setExportFormat] = useState('stl')
  const [shortcutHelpOpen, setShortcutHelpOpen] = useState(false)

  // 3D Git Diff Mode state
  const [headDiffMode, setHeadDiffMode] = useState(false)
  const [headParts, setHeadParts] = useState<RenderPart[]>([])
  const [loadingHeadDiff, setLoadingHeadDiff] = useState(false)

  // Parameter preview hover state
  const [hoveredParamId, setHoveredParamId] = useState<string | null>(null)
  const hoveredParam = useMemo((): HoveredParamInfo | null => {
    if (!hoveredParamId) return null
    const paramDef = manifest.parameters?.find((p: ParamDef) => p.id === hoveredParamId)
    if (!paramDef) return null
    return {
      paramId: hoveredParamId,
      paramDef,
      currentValue: params[hoveredParamId],
      hint: inferPreviewHint(paramDef, manifest as Parameters<typeof inferPreviewHint>[1], mode),
    }
  }, [hoveredParamId, manifest, params, mode])

  const consoleRef = useRef<HTMLElement | null>(null)

  // Constraints
  const { violations: constraintViolations, byParam: constraintsByParam, hasErrors: constraintErrors } = useConstraints(manifest.constraints, params)

  // Shareable URL
  const { copyShareUrl } = useShareableUrl({ params, mode, projectSlug, defaultParams })

  // Hash navigation — only re-apply preset values when the preset actually
  // changes.  During auto-redirect (e.g. /project/test -> /project/test/small/cup),
  // the preset stays the same as the one already applied during initialisation,
  // so we skip the redundant (and destructive, for ?p= shared params) setParams.
  const handleHashChange = (parsed: { mode: { id: string } | null; preset: Preset | null }) => {
    const newMode = parsed.mode ? parsed.mode.id : mode
    const modeChanged = parsed.mode ? parsed.mode.id !== mode : false

    if (modeChanged) setModeState(newMode)

    const newPresetId = parsed.preset ? parsed.preset.id : activePresetId
    const presetChanged = parsed.preset ? parsed.preset.id !== activePresetId : false

    if (presetChanged) setActivePresetId(newPresetId)

    if (modeChanged || presetChanged) {
      setParams((prev: Record<string, unknown>) => {
        const next = { ...prev }

        // 1. Clean up parameters that shouldn't leak into the new mode
        if (manifest?.parameters) {
          manifest.parameters.forEach((p: ParamDef) => {
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
    defaultModeId: storedModeId,
    defaultPresetId: storedPresetId
  })

  const isGridMode = (modeId: string): boolean => {
    if (!modes || modes.length === 0) return false
    const m = modes.find((md: ModeConfig) => md.id === modeId)
    return m?.estimate?.formula === 'grid'
  }

  const setMode = (newMode: string) => {
    setModeState(newMode)
    setAnimating(false)
    setPrintEstimate(null)
    setParts([])
    if (isGridMode(newMode)) {
      const defaultGridPreset = (manifest.grid_presets?.default as string | undefined) || 'rendering'
      const presetValues = (manifest.grid_presets?.[defaultGridPreset] as { values?: Record<string, unknown> } | undefined)?.values
      if (presetValues) {
        setParams((prev: Record<string, unknown>) => ({ ...prev, ...presetValues }))
        setGridPresetId(defaultGridPreset)
      }
    }

    // Ensure active preset is valid for the new mode
    let validPresetId = activePresetId
    const currentPreset = presets.find((p: Preset) => p.id === activePresetId)

    if (currentPreset && currentPreset.visible_in_modes && !currentPreset.visible_in_modes.includes(newMode)) {
      // Preset is not valid for this mode, find the first one that is
      const fallbackPreset = presets.find((p: Preset) => !p.visible_in_modes || p.visible_in_modes.includes(newMode))
      if (fallbackPreset) {
        validPresetId = fallbackPreset.id
        setActivePresetId(validPresetId)

        // Build a set of system-group param ids
        const systemParamIds = new Set(
          (manifest.parameters || [])
            .filter((p: ParamDef) => p.group === 'system')
            .map((p: ParamDef) => p.id)
        )

        setParams((prev: Record<string, unknown>) => {
          const next = { ...prev }
          for (const [key, val] of Object.entries(fallbackPreset.values)) {
            const isSystem = systemParamIds.has(key)
            const isUserModified = key in defaultParams && prev[key] !== defaultParams[key]
            if (isSystem || !isUserModified) {
              next[key] = val
            }
          }
          return next
        })
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
  useLocalStoragePersistence(`${projectSlug}-mode`, mode, { debounce: 0 })
  useLocalStoragePersistence(`${projectSlug}-preset`, activePresetId, { debounce: 0 })

  // Render cache key
  const getCacheKey = useCallback((m: string, p: Record<string, unknown>): string => {
    const keyObj: Record<string, unknown> = { mode: m }
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
    evictCache,
    showConfirmDialog,
    pendingEstimate,
    handleGenerate,
    handleCancelGenerate,
    handleConfirmRender,
    handleCancelRender,
  } = useRender({ mode, params, manifest: manifest as Parameters<typeof useRender>[0]['manifest'], t, getCacheKey, project: projectSlug, exportFormat })

  // Auto-scroll console
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  // Revoke old blob URLs and evict those entries from the L1 render cache.
  useEffect(() => {
    return () => {
      parts.forEach((p: RenderPart) => {
        if (p.url?.startsWith('blob:')) {
          URL.revokeObjectURL(p.url)
          const key = getCacheKey(mode, params)
          evictCache(key)
        }
      })
    }
  }, [parts]) // eslint-disable-line react-hooks/exhaustive-deps

  // Image export
  const cameraViews = getCameraViews()
  const { handleExportImage, handleExportAllViews } = useImageExport({
    viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews
  })

  // Grid preset toggle
  const handleGridPresetToggle = () => {
    const presetKeys = Object.keys(manifest.grid_presets || {}).filter(k => k !== 'default')
    const currentIndex = presetKeys.indexOf(gridPresetId || '')
    const nextId = presetKeys[(currentIndex + 1) % presetKeys.length]
    setGridPresetId(nextId)
    const gp = manifest.grid_presets?.[nextId] as { values?: Record<string, unknown> } | undefined
    if (gp) {
      setParams((prev: Record<string, unknown>) => ({ ...prev, ...gp.values }))
    }
  }

  // Apply preset (auto-switch mode if preset specifies one)
  const handleApplyPreset = (preset: Preset) => {
    const targetMode = preset.mode || mode
    const defaultGridPreset = (manifest.grid_presets?.default as string | undefined) || 'rendering'
    setParams((prev: Record<string, unknown>) => {
      const gridValues = (manifest.grid_presets?.[defaultGridPreset] as { values?: Record<string, unknown> } | undefined)?.values || {}
      return { ...prev, ...preset.values, ...gridValues }
    })
    setActivePresetId(preset.id)
    setGridPresetId(defaultGridPreset)
    if (targetMode !== mode) {
      setModeState(targetMode)
      setPrintEstimate(null)
    }
    navigate(buildHash(projectSlug, targetMode, preset.id))
  }

  // Debounced auto-generate with cache check
  useEffect(() => {
    if (!modes || modes.length === 0) return
    const visibilityParams = manifest.parameters.filter(
      (p: ParamDef) => p.group === 'visibility' && (p.visible_in_modes || []).includes(mode)
    )
    if (visibilityParams.length > 0 && visibilityParams.every((p: ParamDef) => !params[p.id])) {
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
  const handleSetOverhangEnabled = useCallback((val: boolean) => {
    setOverhangEnabled(val)
    if (!val) setOverhangData(null)
  }, [])

  // Overhang analysis — fetch when enabled
  useEffect(() => {
    if (!overhangEnabled || !projectSlug || parts.length === 0) return
    let cancelled = false
    const apiBase = import.meta.env.VITE_API_BASE || ''
    apiFetch(`${apiBase}/api/projects/${projectSlug}/analyze/overhang`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ threshold_deg: overhangThreshold }),
    })
      .then(r => r.ok ? r.json() : Promise.reject(new Error('Overhang analysis failed')))
      .then((data: { analysis: unknown }) => {
        if (!cancelled) setOverhangData(data.analysis)
      })
      .catch((err: Error) => {
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

  // Cached geometry variants for parameter preview ghost overlay
  const { cachedVariants, preRenderStatus } = useParameterPreviewCache({
    manifest: manifest as Parameters<typeof useParameterPreviewCache>[0]['manifest'],
    mode, params, parts, loading, project: projectSlug,
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
    // Parameter preview
    hoveredParam, setHoveredParamId,
    cachedVariants, preRenderStatus,
    // Share
    copyShareUrl,
    // Shortcut help
    shortcutHelpOpen, setShortcutHelpOpen,
    // Refs
    consoleRef,
  }
}
