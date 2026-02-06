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
import { downloadFile, downloadZip } from '../lib/downloadUtils'
import { verify } from '../services/verifyService'
import { setTokenGetter } from '../services/apiClient'

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

function isDemoView(hash) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  return parts.length === 1 && parts[0] === 'demo'
}

function isProjectsView(hash) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  return parts.length === 1 && (parts[0] === 'projects' || parts[0] === 'demo')
}

function parseHash(hash, presets, modes) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  let presetId, modeId
  if (parts.length >= 3) {
    presetId = parts[1]
    modeId = parts[2]
  } else {
    presetId = parts[0]
    modeId = parts[1]
  }
  const preset = presets.find(p => p.id === presetId)
  const mode = modes.find(m => m.id === modeId)
  return {
    preset: preset || presets[0] || null,
    mode: mode || modes[0],
  }
}

function buildHash(projectSlug, presetId, modeId) {
  return `#/${projectSlug}/${presetId}/${modeId}`
}

export function useAppState() {
  const [isDemo, setIsDemo] = useState(() => isDemoView(window.location.hash))
  const [currentView, setCurrentView] = useState(() =>
    isProjectsView(window.location.hash) ? 'projects' : 'studio'
  )
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

  const initialHash = parseHash(window.location.hash, presets, manifest.modes)
  const initialPresetValues = initialHash.preset?.values || {}

  const [mode, setModeState] = useState(() => initialHash.mode.id)

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
      setTimeout(() => setShareToast(false), 2000)
      toast.success(t('act.share_copied'))
    } else {
      toast.error(t('toast.share_failed'))
    }
  }, [copyShareUrl, t])

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

  // Set initial hash if missing or invalid
  useEffect(() => {
    const parsed = parseHash(window.location.hash, presets, manifest.modes)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode.id
    if (presetId) {
      window.location.hash = buildHash(projectSlug, presetId, modeId)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for browser back/forward
  useEffect(() => {
    const onHashChange = () => {
      if (isDemoView(window.location.hash)) {
        setIsDemo(true)
        setCurrentView('projects')
        return
      }
      if (isProjectsView(window.location.hash)) {
        setCurrentView('projects')
        return
      }
      setCurrentView('studio')
      const parsed = parseHash(window.location.hash, presets, manifest.modes)
      setModeState(parsed.mode.id)
      if (parsed.preset) {
        setActivePresetId(parsed.preset.id)
        setParams(prev => ({ ...prev, ...parsed.preset.values }))
      }
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [presets, manifest.modes]) // eslint-disable-line react-hooks/exhaustive-deps

  const isGridMode = (modeId) => {
    const m = manifest.modes.find(md => md.id === modeId)
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

  const viewerRef = useRef(null)
  const consoleRef = useRef(null)

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
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (mod && e.key === 'z' && !e.shiftKey) {
        e.preventDefault()
        undoParams()
        return
      } else if (mod && e.key === 'z' && e.shiftKey) {
        e.preventDefault()
        redoParams()
        return
      } else if (mod && e.key === 'Enter') {
        e.preventDefault()
        handleGenerate()
      } else if (e.key === 'Escape' && loading) {
        handleCancelGenerate()
      } else if (mod) {
        const num = parseInt(e.key, 10)
        if (num >= 1 && num <= manifest.modes.length) {
          e.preventDefault()
          setMode(manifest.modes[num - 1].id)
        }
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [loading, params, mode, manifest]) // eslint-disable-line react-hooks/exhaustive-deps

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
