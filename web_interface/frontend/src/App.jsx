import { useState, useEffect, useRef, useCallback } from 'react'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import ExportPanel from './components/ExportPanel'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { useManifest } from "./contexts/ManifestProvider"
import { Sun, Moon, Monitor, Globe, Square, RotateCcw } from 'lucide-react'
import { useRender } from './hooks/useRender'
import { useImageExport } from './hooks/useImageExport'
import { useLocalStoragePersistence } from './hooks/useLocalStoragePersistence'
import { downloadFile, downloadZip } from './lib/downloadUtils'
import { verify } from './services/verifyService'
import './index.css'

function safeParse(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

function parseHash(hash, presets, modes) {
  const parts = hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  const presetId = parts[0]
  const modeId = parts[1]
  const preset = presets.find(p => p.id === presetId)
  const mode = modes.find(m => m.id === modeId)
  return {
    preset: preset || presets[0] || null,
    mode: mode || modes[0],
  }
}

function buildHash(presetId, modeId) {
  return `#/${presetId}/${modeId}`
}

function App() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, getCameraViews, projectSlug, presets } = useManifest()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()

  // Parse initial state from URL hash
  const initialHash = parseHash(window.location.hash, presets, manifest.modes)
  const initialPresetValues = initialHash.preset?.values || {}

  const [mode, setModeState] = useState(() => initialHash.mode.id)
  const [params, setParams] = useState(() => {
    const stored = safeParse(`${projectSlug}-params`, defaultParams)
    // Merge: defaults < localStorage < preset from URL
    return { ...defaultParams, ...stored, ...initialPresetValues }
  })
  const [colors, setColors] = useState(() => safeParse(`${projectSlug}-colors`, defaultColors))
  const [activePresetId, setActivePresetId] = useState(() => initialHash.preset?.id || presets[0]?.id || null)
  const [gridPresetId, setGridPresetId] = useState('rendering')

  // Set initial hash if missing or invalid
  useEffect(() => {
    const parsed = parseHash(window.location.hash, presets, manifest.modes)
    const presetId = parsed.preset?.id || presets[0]?.id
    const modeId = parsed.mode.id
    if (presetId) {
      window.location.hash = buildHash(presetId, modeId)
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  // Listen for browser back/forward
  useEffect(() => {
    const onHashChange = () => {
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

  // Wrap setMode to also update hash
  const setMode = useCallback((newMode) => {
    setModeState(newMode)
    const presetId = activePresetId || presets[0]?.id
    if (presetId) {
      window.location.hash = buildHash(presetId, newMode)
    }
  }, [activePresetId, presets])

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
  } = useRender({ mode, params, manifest, t, getCacheKey })

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
    const nextId = gridPresetId === 'rendering' ? 'manufacturing' : 'rendering'
    setGridPresetId(nextId)
    const gp = manifest.grid_presets?.[nextId]
    if (gp) {
      setParams(prev => ({ ...prev, ...gp.values }))
    }
  }, [gridPresetId, manifest])

  const handleApplyPreset = (preset) => {
    setParams(prev => {
      const renderingValues = manifest.grid_presets?.rendering?.values || {}
      return { ...prev, ...preset.values, ...renderingValues }
    })
    setActivePresetId(preset.id)
    setGridPresetId('rendering')
    window.location.hash = buildHash(preset.id, mode)
  }

  const handleReset = () => {
    setParams(getDefaultParams())
    setColors(getDefaultColors())
  }

  const handleVerify = async () => {
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await verify(parts, mode)
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
    }, 500)
    return () => clearTimeout(timer)
  }, [params, mode, getCacheKey, manifest])

  // --- Keyboard shortcuts (dynamic Cmd+1..N for modes) ---
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (mod && e.key === 'Enter') {
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

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
      {/* Header */}
      <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
        <h1 className="text-lg font-bold tracking-tight">{manifest.project.name}</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? 'English' : 'Español'}>
            <Globe className="h-5 w-5" />
            <span className="sr-only">Toggle Language</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={cycleTheme} title={t(`theme.${theme}`)}>
            <ThemeIcon className="h-5 w-5" />
            <span className="sr-only">Toggle Theme</span>
          </Button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden flex-col lg:flex-row">
        {/* Sidebar */}
        <div className="w-full lg:w-80 lg:min-w-[20rem] border-b lg:border-b-0 lg:border-r border-border bg-card p-4 flex flex-col gap-4 overflow-y-auto shrink-0 max-h-[50vh] lg:max-h-none">
          <Tabs value={mode} onValueChange={setMode} className="w-full relative z-10">
            <TabsList className="grid w-full grid-cols-3">
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
            manifest={manifest}
            onDownloadStl={handleDownloadStl}
            onExportImage={handleExportImage}
            onExportAllViews={handleExportAllViews}
          />
        </div>

        {/* Main View */}
        <div className="flex-1 relative flex flex-col min-h-0">
          <div className="flex-1 relative min-h-0">
            <Viewer ref={viewerRef} parts={parts} colors={colors} loading={loading} progress={progress} progressPhase={progressPhase} />
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
