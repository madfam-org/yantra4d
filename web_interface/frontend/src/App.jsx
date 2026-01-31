import { useState, useEffect, useRef, useCallback, lazy, Suspense } from 'react'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import ExportPanel from './components/ExportPanel'
import PrintEstimateOverlay from './components/PrintEstimateOverlay'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { useManifest } from "./contexts/ManifestProvider"
import { Sun, Moon, Monitor, Globe, Square, RotateCcw, Share2, Undo2, Redo2 } from 'lucide-react'
import { useRender } from './hooks/useRender'
import { useImageExport } from './hooks/useImageExport'
import { useLocalStoragePersistence } from './hooks/useLocalStoragePersistence'
import { useShareableUrl, getSharedParams } from './hooks/useShareableUrl'
import { useUndoRedo } from './hooks/useUndoRedo'
import { downloadFile, downloadZip } from './lib/downloadUtils'
import { verify } from './services/verifyService'
import AuthButton from './components/AuthButton'
import ProjectSelector from './components/ProjectSelector'
import { ErrorBoundary } from './components/ErrorBoundary'
import { useAuth } from './contexts/AuthProvider'
import './index.css'

const ProjectsView = lazy(() => import('./components/ProjectsView'))
const OnboardingWizard = lazy(() => import('./components/OnboardingWizard'))

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

function isProjectsView(hash) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  return parts.length === 1 && parts[0] === 'projects'
}

function parseHash(hash, presets, modes) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  // Support both 2-segment (preset/mode) and 3-segment (project/preset/mode) formats
  let presetId, modeId
  if (parts.length >= 3) {
    // 3-segment: project/preset/mode — project handled by ManifestProvider
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

function App() {
  const [currentView, setCurrentView] = useState(() =>
    isProjectsView(window.location.hash) ? 'projects' : 'studio'
  )
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { handleOAuthCallback: handleOAuth } = useAuth()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, getCameraViews, projectSlug, presets } = useManifest()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()

  // Parse initial state from URL hash
  const initialHash = parseHash(window.location.hash, presets, manifest.modes)
  const initialPresetValues = initialHash.preset?.values || {}

  const [mode, setModeState] = useState(() => initialHash.mode.id)

  // Shared params from ?p= query string take highest priority
  const sharedParams = getSharedParams()

  const [params, setParams, { undo: undoParams, redo: redoParams, canUndo, canRedo }] = useUndoRedo(() => {
    const stored = safeParse(`${projectSlug}-params`, defaultParams)
    // Merge: defaults < localStorage < preset from URL < shared params
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

  // Shareable URL hook
  const { copyShareUrl } = useShareableUrl({ params, mode, projectSlug, defaultParams })

  const handleShare = useCallback(async () => {
    const ok = await copyShareUrl()
    if (ok) {
      setShareToast(true)
      setTimeout(() => setShareToast(false), 2000)
    }
  }, [copyShareUrl])

  // Dynamic browser tab title
  useEffect(() => {
    document.title = currentView === 'projects'
      ? 'Qubic'
      : `${manifest.project.name} — Qubic`
  }, [currentView, manifest.project.name])

  // Handle OAuth callback (?code=&state= query params)
  useEffect(() => {
    const url = new URL(window.location.href)
    const code = url.searchParams.get('code')
    const state = url.searchParams.get('state')
    if (code && state) {
      handleOAuth(code, state).catch(() => {})
      // Clean query params without reload
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
  }, [presets, manifest.modes])

  const isGridMode = (modeId) => {
    const m = manifest.modes.find(md => md.id === modeId)
    return m?.estimate?.formula === 'grid'
  }

  // Wrap setMode to also update hash
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
  }, [activePresetId, presets, manifest, projectSlug])

  const viewerRef = useRef(null)
  const consoleRef = useRef(null)

  // --- Persistence ---
  useLocalStoragePersistence(`${projectSlug}-params`, params)
  useLocalStoragePersistence(`${projectSlug}-colors`, colors)
  useLocalStoragePersistence(`${projectSlug}-mode`, mode, { debounce: 0, serialize: false })

  // Cache key derived from manifest parameter IDs
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

  // Auto-scroll console to bottom on new logs
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight
    }
  }, [logs])

  // Revoke old blob URLs when parts change to prevent memory leaks
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
  }, [gridPresetId, manifest])

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
    // Skip render if all visibility params for current mode are unchecked
    const visibilityParams = manifest.parameters.filter(
      p => p.group === 'visibility' && (p.visible_in_modes || []).includes(mode)
    )
    if (visibilityParams.length > 0 && visibilityParams.every(p => !params[p.id])) {
      return
    }

    const cacheKey = getCacheKey(mode, params)
    const cached = checkCache(cacheKey)
    if (cached) {
      setParts(cached)
      return
    }
    const timer = setTimeout(() => {
      handleGenerate()
    }, RENDER_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [params, mode, getCacheKey, manifest])

  // --- Keyboard shortcuts (dynamic Cmd+1..N for modes) ---
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
  }, [loading, params, mode, manifest])

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }

  const toggleLanguage = () => {
    setLanguage(language === 'es' ? 'en' : 'es')
  }

  const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor

  if (currentView === 'projects') {
    return (
      <div className="flex flex-col h-screen w-full bg-background text-foreground">
        <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
          <h1 className="text-lg font-bold tracking-tight">Qubic</h1>
          <div className="flex items-center gap-2">
            <AuthButton />
            <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? t('lang.switch_to_en') : t('lang.switch_to_es')}>
              <Globe className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
              <ThemeIcon className="h-5 w-5" />
            </Button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto">
          <ErrorBoundary t={t}>
            <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground">Loading...</div>}>
              <ProjectsView />
            </Suspense>
          </ErrorBoundary>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
      {/* Header */}
      <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex flex-col">
            <h1 className="text-lg font-bold tracking-tight">{manifest.project.name}</h1>
            <span className="text-[10px] text-muted-foreground leading-tight">{t('platform.powered_by')}</span>
          </div>
          <ProjectSelector />
          <a href="#/projects" className="text-sm text-muted-foreground hover:text-foreground">{t('nav.projects')}</a>
        </div>
        <div className="flex items-center gap-1">
          <AuthButton />
          <Button variant="ghost" size="icon" onClick={undoParams} disabled={!canUndo} title={t('act.undo')}>
            <Undo2 className="h-4 w-4" />
            <span className="sr-only">{t('act.undo')}</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={redoParams} disabled={!canRedo} title={t('act.redo')}>
            <Redo2 className="h-4 w-4" />
            <span className="sr-only">{t('act.redo')}</span>
          </Button>
          <div className="relative">
            <Button variant="ghost" size="icon" onClick={handleShare} title={t('act.share')}>
              <Share2 className="h-4 w-4" />
              <span className="sr-only">{t('act.share')}</span>
            </Button>
            {shareToast && (
              <div className="absolute top-full right-0 mt-1 px-2 py-1 bg-primary text-primary-foreground text-xs rounded whitespace-nowrap z-50">
                {t('act.share_copied')}
              </div>
            )}
          </div>
          <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? t('lang.switch_to_en') : t('lang.switch_to_es')}>
            <Globe className="h-5 w-5" />
            <span className="sr-only">{t('sr.toggle_lang')}</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
            <ThemeIcon className="h-5 w-5" />
            <span className="sr-only">{t('sr.toggle_theme')}</span>
          </Button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* Sidebar */}
        <div className="w-full lg:w-80 lg:min-w-[20rem] border-b lg:border-b-0 lg:border-r border-border bg-card p-4 flex flex-col gap-4 overflow-y-auto shrink-0 max-h-[50vh] lg:max-h-none">
          <Tabs value={mode} onValueChange={setMode} className="w-full relative z-10">
            <TabsList className="grid w-full" style={{ gridTemplateColumns: `repeat(${manifest.modes.length}, minmax(0, 1fr))` }}>
              {manifest.modes.map(m => (
                <TabsTrigger key={m.id} value={m.id} className="min-h-[44px]">
                  {getLabel(m, 'label', language)}
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>

          <Controls
            params={params}
            setParams={setParams}
            mode={mode}
            colors={colors}
            setColors={setColors}
            wireframe={wireframe}
            setWireframe={setWireframe}
            presets={presets}
            onApplyPreset={handleApplyPreset}
            onToggleGridPreset={handleGridPresetToggle}
          />

          <div className="flex-1"></div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button
              type="button"
              onClick={() => handleGenerate()}
              disabled={loading}
              className="w-full"
              title={t("tooltip.gen")}
            >
              {loading ? t("btn.proc") : t("btn.gen")}
            </Button>

            {loading && (
              <Button variant="destructive" onClick={handleCancelGenerate} className="w-full gap-2">
                <Square className="h-4 w-4" />
                {t("btn.cancel")}
              </Button>
            )}

            <Button
              variant="secondary"
              onClick={handleVerify}
              disabled={loading || parts.length === 0}
              className="w-full"
              title={t("tooltip.verify")}
            >
              {t("btn.verify")}
            </Button>

            <Button variant="outline" onClick={handleReset} className="w-full gap-2">
              <RotateCcw className="h-4 w-4" />
              {t("btn.reset")}
            </Button>
          </div>

          <ExportPanel
            parts={parts}
            mode={mode}
            onDownloadStl={handleDownloadStl}
            onExportImage={handleExportImage}
            onExportAllViews={handleExportAllViews}
            exportFormat={exportFormat}
            onExportFormatChange={setExportFormat}
          />
        </div>

        {/* Main View */}
        <div className="flex-1 relative flex flex-col min-h-0">
          <div className="flex-1 relative min-h-0">
            <Viewer ref={viewerRef} parts={parts} colors={colors} wireframe={wireframe} loading={loading} progress={progress} progressPhase={progressPhase} animating={animating} setAnimating={setAnimating} mode={mode} params={params} onGeometryStats={setPrintEstimate} />
            <PrintEstimateOverlay volumeMm3={printEstimate?.volumeMm3} boundingBox={printEstimate?.boundingBox} />
          </div>

          {/* Console */}
          <div
            ref={consoleRef}
            className="h-32 lg:h-48 bg-muted border-t border-border p-4 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap shrink-0"
            role="log"
            aria-live="polite"
            aria-label="Render console"
          >
            {logs}
          </div>
        </div>
      </div>

      <ConfirmRenderDialog
        open={showConfirmDialog}
        onConfirm={handleConfirmRender}
        onCancel={handleCancelRender}
        estimatedTime={pendingEstimate}
      />
    </div>
  )
}

export default App
