import { useState, useEffect, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import { useTheme } from '../contexts/ThemeProvider'
import { useLanguage } from '../contexts/LanguageProvider'
import { useManifest } from '../contexts/ManifestProvider'
import { useAuth } from '../contexts/AuthProvider'
import { useRender } from './useRender'
import { useImageExport } from './useImageExport'
import { useLocalStoragePersistence } from './useLocalStoragePersistence'
import { useShareableUrl, getSharedParams } from './useShareableUrl'
import { useUndoRedo } from './useUndoRedo'
import { useConstraints } from './useConstraints'
import { useHashNavigation, parseHash, buildHash } from './useHashNavigation'
import { useKeyboardShortcuts } from './useKeyboardShortcuts'
import { downloadFile, downloadZip } from '../lib/downloadUtils'
import { verify } from '../services/verifyService'
import { setTokenGetter } from '../services/apiClient'

const RENDER_DEBOUNCE_MS = 500
const TOAST_DURATION_MS = 2000

function safeParse(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function useAppState() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { handleOAuthCallback: handleOAuth, getAccessToken } = useAuth()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, getCameraViews, projectSlug, presets } = useManifest()

  // Wire auth token into shared API client
  useEffect(() => {
    setTokenGetter(getAccessToken)
  }, [getAccessToken])

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
  const [animating, setAnimating] = useState(false)
  const [shareToast, setShareToast] = useState(false)
  const [printEstimate, setPrintEstimate] = useState(null)
  const [exportFormat, setExportFormat] = useState('stl')

  // Assembly guide state
  const [assemblyActive, setAssemblyActive] = useState(false)
  const [highlightedParts, setHighlightedParts] = useState([])
  const [visibleParts, setVisibleParts] = useState([])
  const [assemblyEditorOpen, setAssemblyEditorOpen] = useState(false)

  const viewerRef = useRef(null)
  const consoleRef = useRef(null)

  const handleHighlightParts = useCallback((parts) => {
    setHighlightedParts(parts || [])
  }, [])

  const handleSetAssemblyCamera = useCallback((position, target) => {
    viewerRef.current?.animateTo?.(position, target)
  }, [])

  const handleAssemblyStepChange = useCallback((step) => {
    if (!step) {
      setAssemblyActive(false)
      setHighlightedParts([])
      setVisibleParts([])
      return
    }
    setAssemblyActive(true)
    setVisibleParts(step.visible_parts || [])
    setHighlightedParts(step.highlight_parts || [])
    if (step.camera) {
      handleSetAssemblyCamera(step.camera, step.camera_target)
    }
  }, [handleSetAssemblyCamera])

  const { violations: constraintViolations, byParam: constraintsByParam, hasErrors: constraintErrors } = useConstraints(manifest.constraints, params)

  const { copyShareUrl } = useShareableUrl({ params, mode, projectSlug, defaultParams })

  const handleShare = useCallback(async () => {
    const ok = await copyShareUrl()
    if (ok) {
      setShareToast(true)
      setTimeout(() => setShareToast(false), TOAST_DURATION_MS)
      toast.success(t('act.share_copied'))
    } else {
      toast.error(t('toast.share_failed'))
    }
  }, [copyShareUrl, t])

  // Hash navigation (extracted hook)
  const handleHashChange = useCallback((parsed) => {
    if (parsed.mode) setModeState(parsed.mode.id)
    if (parsed.preset) {
      setActivePresetId(parsed.preset.id)
      setParams(prev => ({ ...prev, ...parsed.preset.values }))
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const { currentView, isDemo } = useHashNavigation({
    presets,
    modes,
    projectSlug,
    onHashChange: handleHashChange,
  })

  // Dynamic browser tab title
  useEffect(() => {
    document.title = currentView === 'projects'
      ? 'Yantra4D'
      : `${manifest.project.name} — Yantra4D`
  }, [currentView, manifest.project.name])

  // Handle OAuth callback
  useEffect(() => {
    const url = new URL(window.location.href)
    const code = url.searchParams.get('code')
    const state = url.searchParams.get('state')
    if (code && state) {
      handleOAuth(code, state).catch((err) => console.error('OAuth callback failed:', err))
      url.searchParams.delete('code')
      url.searchParams.delete('state')
      window.history.replaceState({}, '', url.pathname + url.hash)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const isGridMode = (modeId) => {
    if (!modes || modes.length === 0) return false
    const m = modes.find(md => md.id === modeId)
    return m?.estimate?.formula === 'grid'
  }

  const setMode = useCallback((newMode) => {
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
  }, [activePresetId, presets, manifest, projectSlug]) // eslint-disable-line react-hooks/exhaustive-deps

  // Persistence
  useLocalStoragePersistence(`${projectSlug}-params`, params)
  useLocalStoragePersistence(`${projectSlug}-colors`, colors)
  useLocalStoragePersistence(`${projectSlug}-mode`, mode, { debounce: 0, serialize: false })

  const getCacheKey = useCallback((m, p) => {
    const keyObj = { mode: m }
    for (const param of manifest.parameters) {
      if (p[param.id] !== undefined) keyObj[param.id] = p[param.id]
    }
    return JSON.stringify(keyObj)
  }, [manifest])

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

  const cameraViews = getCameraViews()
  const { handleExportImage, handleExportAllViews } = useImageExport({
    viewerRef, projectSlug, mode, parts, setLogs, t, cameraViews
  })

  const handleGridPresetToggle = useCallback(() => {
    const presetKeys = Object.keys(manifest.grid_presets || {}).filter(k => k !== 'default')
    const currentIndex = presetKeys.indexOf(gridPresetId)
    const nextId = presetKeys[(currentIndex + 1) % presetKeys.length]
    setGridPresetId(nextId)
    const gp = manifest.grid_presets?.[nextId]
    if (gp) {
      setParams(prev => ({ ...prev, ...gp.values }))
    }
  }, [gridPresetId, manifest]) // eslint-disable-line react-hooks/exhaustive-deps

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

  const handleReset = () => {
    setParams(getDefaultParams())
    setColors(getDefaultColors())
    setWireframe(false)
  }

  const handleVerify = async () => {
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await verify(parts, mode, projectSlug)
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.output)
      if (res.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
      else setLogs(prev => prev + `\n${t("log.fail")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
  }

  const handleDownloadStl = async () => {
    if (parts.length === 0) return
    if (parts.length === 1) {
      downloadFile(parts[0].url, `${projectSlug}_${mode}_${parts[0].type}.stl`)
      return
    }
    setLogs(prev => prev + `\n${t("log.zipping")}`)
    try {
      const items = parts.map(part => ({
        url: part.url,
        filename: `${projectSlug}_${mode}_${part.type}.stl`
      }))
      await downloadZip(items, `${projectSlug}_${mode}_all_parts.zip`)
      setLogs(prev => prev + `\n${t("log.zip_done")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
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

  // Keyboard shortcuts (extracted hook)
  useKeyboardShortcuts({
    onUndo: undoParams,
    onRedo: redoParams,
    onRender: handleGenerate,
    onCancelRender: handleCancelGenerate,
    onSwitchMode: setMode,
    loading,
    modes,
  })

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }

  const toggleLanguage = () => {
    setLanguage(language === 'es' ? 'en' : 'es')
  }

  return {
    // View state
    currentView, isDemo,
    // Theme/lang
    theme, cycleTheme,
    language, setLanguage, toggleLanguage, t,
    // Manifest data
    manifest, getLabel, projectSlug, presets, cameraViews,
    // Mode & params
    mode, setMode, params, setParams,
    colors, setColors,
    wireframe, setWireframe,
    animating, setAnimating,
    // Undo/redo
    undoParams, redoParams, canUndo, canRedo,
    // Share
    handleShare, shareToast,
    // Render
    parts, logs, loading, progress, progressPhase,
    showConfirmDialog, pendingEstimate,
    handleGenerate, handleCancelGenerate, handleConfirmRender, handleCancelRender,
    // Actions
    handleVerify, handleDownloadStl, handleReset,
    handleApplyPreset, handleGridPresetToggle,
    handleExportImage, handleExportAllViews,
    // Export
    exportFormat, setExportFormat,
    // Constraints
    constraintViolations, constraintsByParam, constraintErrors,
    // Print estimate
    printEstimate, setPrintEstimate,
    // Assembly guide
    assemblyActive, highlightedParts, visibleParts,
    handleHighlightParts, handleSetAssemblyCamera, handleAssemblyStepChange,
    assemblyEditorOpen, setAssemblyEditorOpen,
    // Refs
    viewerRef, consoleRef,
  }
}
