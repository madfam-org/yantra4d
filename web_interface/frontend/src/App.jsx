import { useState, useEffect, useRef, useCallback } from 'react'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { useManifest } from "./contexts/ManifestProvider"
import { Sun, Moon, Monitor, Globe, Download, Square, RotateCcw } from 'lucide-react'
import JSZip from 'jszip'
import { renderParts, cancelRender, estimateRenderTime } from './services/renderService'
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

  const [parts, setParts] = useState([])
  const [logs, setLogs] = useState(t("log.ready"))
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [progressPhase, setProgressPhase] = useState('')

  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingEstimate, setPendingEstimate] = useState(0)
  const [pendingPayload, setPendingPayload] = useState(null)

  const [partsCache, setPartsCache] = useState({})

  const viewerRef = useRef(null)
  const abortControllerRef = useRef(null)

  // --- Persistence (debounced) ---
  useEffect(() => {
    const id = setTimeout(() => localStorage.setItem(`${projectSlug}-params`, JSON.stringify(params)), 300)
    return () => clearTimeout(id)
  }, [params, projectSlug])

  useEffect(() => {
    const id = setTimeout(() => localStorage.setItem(`${projectSlug}-colors`, JSON.stringify(colors)), 300)
    return () => clearTimeout(id)
  }, [colors, projectSlug])

  useEffect(() => {
    localStorage.setItem(`${projectSlug}-mode`, mode)
  }, [mode, projectSlug])

  // Cache key derived from manifest parameter IDs
  const getCacheKey = useCallback((m, p) => {
    const keyObj = { mode: m }
    for (const param of manifest.parameters) {
      if (p[param.id] !== undefined) keyObj[param.id] = p[param.id]
    }
    return JSON.stringify(keyObj)
  }, [manifest])

  const handleGenerate = async (forceRender = false, overridePayload = null) => {
    const payload = overridePayload || { ...params, mode }
    const cacheKey = getCacheKey(mode, params)

    if (!forceRender && partsCache[cacheKey]) {
      setParts(partsCache[cacheKey])
      setLogs(prev => prev + `\n⚡ ${t("log.cache_hit")}`)
      return
    }

    if (!forceRender) {
      const estimate = estimateRenderTime(mode, params, manifest)
      if (estimate > 60) {
        setPendingEstimate(estimate)
        setPendingPayload(payload)
        setShowConfirmDialog(true)
        return
      }
    }

    setLoading(true)
    setProgress(5)
    setProgressPhase(t("phase.compiling"))
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const result = await renderParts(mode, params, manifest, {
        onProgress: ({ percent, phase, log }) => {
          if (percent !== undefined) setProgress(percent)
          if (phase) {
            const phaseKey = `phase.${phase}`
            const translated = t(phaseKey)
            if (translated !== phaseKey) setProgressPhase(translated)
          }
          if (log) setLogs(prev => prev + `\n${log}`)
        },
        abortSignal: controller.signal
      })

      setParts(result)
      setPartsCache(prev => ({ ...prev, [cacheKey]: result }))
      setProgress(100)
      setLogs(prev => prev + `\n${t("log.gen_stl")}`)
    } catch (e) {
      if (e.name === 'AbortError') {
        setLogs(prev => prev + `\n${t("log.cancelled")}`)
      } else {
        setLogs(prev => prev + `\n${t("log.error")}` + e.message)
      }
    } finally {
      abortControllerRef.current = null
      setProgressPhase('')
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, 500)
    }
  }

  const handleCancelGenerate = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    await cancelRender()
  }

  const handleConfirmRender = () => {
    setShowConfirmDialog(false)
    handleGenerate(true, pendingPayload)
  }

  const handleCancelRender = () => {
    setShowConfirmDialog(false)
    setPendingEstimate(0)
    setPendingPayload(null)
  }

  const handleReset = () => {
    setParams(getDefaultParams())
    setColors(getDefaultColors())
  }

  const handleVerify = async () => {
    setLoading(true)
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await verify(parts, mode)
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.output)
      if (res.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
      else setLogs(prev => prev + `\n${t("log.fail")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadStl = async () => {
    if (parts.length === 0) return

    if (parts.length === 1) {
      const link = document.createElement('a')
      link.href = parts[0].url
      link.download = `${projectSlug}_${mode}_${parts[0].type}.stl`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      return
    }

    setLogs(prev => prev + `\n${t("log.zipping")}`)
    try {
      const zip = new JSZip()
      for (const part of parts) {
        const res = await fetch(part.url)
        const blob = await res.blob()
        zip.file(`${projectSlug}_${mode}_${part.type}.stl`, blob)
      }
      const content = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(content)
      try {
        const link = document.createElement('a')
        link.href = url
        link.download = `${projectSlug}_${mode}_all_parts.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } finally {
        URL.revokeObjectURL(url)
      }
      setLogs(prev => prev + `\n${t("log.zip_done")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    }
  }

  const handleExportImage = (view) => {
    if (!viewerRef.current) return
    viewerRef.current.setCameraView(view)
    setTimeout(() => {
      const dataUrl = viewerRef.current.captureSnapshot()
      const link = document.createElement('a')
      link.href = dataUrl
      link.download = `${projectSlug}_${mode}_${view}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }, 100)
  }

  const handleExportAllViews = async () => {
    if (!viewerRef.current || parts.length === 0) return
    try {
      const views = ['iso', 'top', 'front', 'right']
      const zip = new JSZip()
      for (const view of views) {
        viewerRef.current.setCameraView(view)
        await new Promise(r => setTimeout(r, 150))
        const dataUrl = viewerRef.current.captureSnapshot()
        const data = atob(dataUrl.split(',')[1])
        const arr = new Uint8Array(data.length)
        for (let i = 0; i < data.length; i++) arr[i] = data.charCodeAt(i)
        zip.file(`${projectSlug}_${mode}_${view}.png`, arr)
      }
      const blob = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(blob)
      try {
        const link = document.createElement('a')
        link.href = url
        link.download = `${projectSlug}_${mode}_all_views.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
      } finally {
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      console.error('Export all views failed:', e)
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

          {/* Export Buttons */}
          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button
              variant="outline"
              onClick={handleDownloadStl}
              disabled={parts.length === 0}
              className="w-full gap-2"
              title={t("tooltip.download")}
            >
              <Download className="h-4 w-4" />
              {t("act.download_stl")} {parts.length > 1 ? '(ZIP)' : ''}
            </Button>

            <div className="text-xs text-muted-foreground mb-1">{t("act.export_img")}</div>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExportImage('iso')} disabled={parts.length === 0}>
                {t("view.iso")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('top')} disabled={parts.length === 0}>
                {t("view.top")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('front')} disabled={parts.length === 0}>
                {t("view.front")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('right')} disabled={parts.length === 0}>
                {t("view.right")}
              </Button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleExportAllViews}
              disabled={parts.length === 0}
              className="w-full"
            >
              {t("act.export_all")}
            </Button>
          </div>
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
