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

function App() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()
  const { manifest, getDefaultParams, getDefaultColors, getLabel, projectSlug } = useManifest()

  const defaultParams = getDefaultParams()
  const defaultColors = getDefaultColors()

  const [mode, setMode] = useState(() => localStorage.getItem(`${projectSlug}-mode`) || manifest.modes[0].id)
  const [params, setParams] = useState(() => safeParse(`${projectSlug}-params`, defaultParams))
  const [colors, setColors] = useState(() => safeParse(`${projectSlug}-colors`, defaultColors))

  const viewerRef = useRef(null)

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
    partsCache,
    showConfirmDialog,
    pendingEstimate,
    handleGenerate,
    handleCancelGenerate,
    handleConfirmRender,
    handleCancelRender,
  } = useRender({ mode, params, manifest, t, getCacheKey })

  const { handleExportImage, handleExportAllViews } = useImageExport({
    viewerRef, projectSlug, mode, parts, setLogs, t
  })

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
    const cacheKey = getCacheKey(mode, params)
    if (partsCache[cacheKey]) {
      setParts(partsCache[cacheKey])
      return
    }
    const timer = setTimeout(() => {
      handleGenerate()
    }, 500)
    return () => clearTimeout(timer)
  }, [params, mode, getCacheKey, partsCache])

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
      <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4">
        <h1 className="text-lg font-bold tracking-tight">{manifest.project.name}</h1>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="icon" onClick={toggleLanguage} title={language === 'es' ? 'English' : 'Español'}>
            <Globe className="h-5 w-5" />
            <span className="sr-only">Toggle Language</span>
          </Button>
          <Button variant="ghost" size="icon" onClick={cycleTheme} title={theme}>
            <ThemeIcon className="h-5 w-5" />
            <span className="sr-only">Toggle Theme</span>
          </Button>
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 border-r border-border bg-card p-4 flex flex-col gap-4 overflow-y-auto">
          <Tabs value={mode} onValueChange={setMode} className="w-full relative z-10">
            <TabsList className={`grid w-full grid-cols-${manifest.modes.length}`}>
              {manifest.modes.map(m => (
                <TabsTrigger key={m.id} value={m.id}>
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
            onDownloadStl={handleDownloadStl}
            onExportImage={handleExportImage}
            onExportAllViews={handleExportAllViews}
          />
        </div>

        {/* Main View */}
        <div className="flex-1 relative flex flex-col">
          <div className="flex-1 relative">
            <Viewer ref={viewerRef} parts={parts} colors={colors} loading={loading} progress={progress} progressPhase={progressPhase} />
          </div>

          {/* Console */}
          <div
            className="h-48 bg-muted border-t border-border p-4 font-mono text-xs text-foreground overflow-y-auto whitespace-pre-wrap"
            role="log"
            aria-live="polite"
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
