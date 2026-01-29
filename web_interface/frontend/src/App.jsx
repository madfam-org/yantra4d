import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { Sun, Moon, Monitor, Globe, Download, Square, RotateCcw } from 'lucide-react'
import JSZip from 'jszip'
import { DEFAULTS, MODE_SCAD_MAP } from './config/defaults'
import './index.css'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:5000'

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

  const [mode, setMode] = useState(() => localStorage.getItem('tablaco-mode') || 'unit')
  const [params, setParams] = useState(() => safeParse('tablaco-params', DEFAULTS.params))
  const [colors, setColors] = useState(() => safeParse('tablaco-colors', DEFAULTS.colors))

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
    const id = setTimeout(() => localStorage.setItem('tablaco-params', JSON.stringify(params)), 300)
    return () => clearTimeout(id)
  }, [params])

  useEffect(() => {
    const id = setTimeout(() => localStorage.setItem('tablaco-colors', JSON.stringify(colors)), 300)
    return () => clearTimeout(id)
  }, [colors])

  useEffect(() => {
    localStorage.setItem('tablaco-mode', mode)
  }, [mode])

  // --- Health check on mount ---
  useEffect(() => {
    axios.get(`${API_BASE}/api/health`).catch(() => {
      setLogs(prev => prev + `\n⚠️ ${t("log.backend_warn")}`)
    })
  }, [])

  // Cache key includes rod_extension
  const getCacheKey = useCallback((m, p) => {
    return JSON.stringify({ mode: m, size: p.size, thick: p.thick, rod_D: p.rod_D, rows: p.rows, cols: p.cols, rod_extension: p.rod_extension })
  }, [])

  const handleGenerate = async (forceRender = false, overridePayload = null) => {
    const scad_file = MODE_SCAD_MAP[mode] || 'half_cube.scad'
    const payload = overridePayload || { ...params, scad_file }
    const cacheKey = getCacheKey(mode, params)

    if (!forceRender && partsCache[cacheKey]) {
      setParts(partsCache[cacheKey])
      setLogs(prev => prev + `\n⚡ ${t("log.cache_hit")}`)
      return
    }

    if (!forceRender) {
      try {
        const estRes = await axios.post(`${API_BASE}/api/estimate`, payload)
        const estimate = estRes.data.estimated_seconds
        if (estimate > 60) {
          setPendingEstimate(estimate)
          setPendingPayload(payload)
          setShowConfirmDialog(true)
          return
        }
      } catch (e) {
        console.warn('Estimate failed, proceeding:', e)
      }
    }

    setLoading(true)
    setProgress(5)
    setProgressPhase(t("phase.compiling"))
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      const response = await fetch(`${API_BASE}/api/render-stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let finalParts = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n').filter(line => line.startsWith('data: '))

        for (const rawLine of lines) {
          try {
            const data = JSON.parse(rawLine.slice(6))

            if (data.progress !== undefined) {
              setProgress(data.progress)
            }

            if (data.event === 'part_start') {
              setLogs(prev => prev + `\n[${data.part}] Starting... (${data.index + 1}/${data.total})`)
            } else if (data.event === 'output') {
              const line = data.line
              if (line.includes('Compiling')) setProgressPhase(t("phase.compiling"))
              else if (line.includes('CGAL')) setProgressPhase(t("phase.cgal"))
              else if (line.includes('Rendering') || line.includes('Geometries')) setProgressPhase(t("phase.rendering"))
              else if (line.includes('Parsing')) setProgressPhase(t("phase.geometry"))

              if (line.includes('Compiling') || line.includes('Parsing') ||
                line.includes('CGAL') || line.includes('Geometries') ||
                line.includes('Rendering') || line.includes('Total') ||
                line.includes('Simple:')) {
                setLogs(prev => prev + `\n  ${line}`)
              }
            } else if (data.event === 'part_done') {
              setLogs(prev => prev + `\n[${data.part}] Done (${data.progress}%)`)
            } else if (data.event === 'complete') {
              finalParts = data.parts
            } else if (data.event === 'error') {
              setLogs(prev => prev + `\n[ERROR] ${data.part}: ${data.message}`)
            }
          } catch (parseErr) {
            // Ignore malformed JSON
          }
        }
      }

      const timestamp = Date.now()
      const partsWithCache = finalParts.map(p => ({
        ...p,
        url: p.url + "?t=" + timestamp
      }))

      setParts(partsWithCache)
      setPartsCache(prev => ({ ...prev, [cacheKey]: partsWithCache }))
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
    try {
      await axios.post(`${API_BASE}/api/render-cancel`)
    } catch (_) {}
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
    setParams(DEFAULTS.params)
    setColors(DEFAULTS.colors)
  }

  const handleVerify = async () => {
    setLoading(true)
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await axios.post(`${API_BASE}/api/verify`, { mode })
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.data.output)
      if (res.data.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
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
      link.download = `tablaco_${mode}_${parts[0].type}.stl`
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
        zip.file(`tablaco_${mode}_${part.type}.stl`, blob)
      }
      const content = await zip.generateAsync({ type: 'blob' })
      const url = URL.createObjectURL(content)
      const link = document.createElement('a')
      link.href = url
      link.download = `tablaco_${mode}_all_parts.zip`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      URL.revokeObjectURL(url)
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
      link.download = `tablaco_${mode}_${view}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
    }, 100)
  }

  const handleExportAllViews = async () => {
    if (!viewerRef.current || parts.length === 0) return
    const views = ['iso', 'top', 'front', 'right']
    const zip = new JSZip()
    for (const view of views) {
      viewerRef.current.setCameraView(view)
      await new Promise(r => setTimeout(r, 150))
      const dataUrl = viewerRef.current.captureSnapshot()
      const data = atob(dataUrl.split(',')[1])
      const arr = new Uint8Array(data.length)
      for (let i = 0; i < data.length; i++) arr[i] = data.charCodeAt(i)
      zip.file(`tablaco_${mode}_${view}.png`, arr)
    }
    const blob = await zip.generateAsync({ type: 'blob' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `tablaco_${mode}_all_views.zip`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
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
  }, [params, mode])

  // --- Keyboard shortcuts ---
  useEffect(() => {
    const handler = (e) => {
      const mod = e.metaKey || e.ctrlKey
      if (mod && e.key === 'Enter') {
        e.preventDefault()
        handleGenerate()
      } else if (e.key === 'Escape' && loading) {
        handleCancelGenerate()
      } else if (mod && e.key === '1') {
        e.preventDefault(); setMode('unit')
      } else if (mod && e.key === '2') {
        e.preventDefault(); setMode('assembly')
      } else if (mod && e.key === '3') {
        e.preventDefault(); setMode('grid')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [loading, params, mode])

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
        <h1 className="text-lg font-bold tracking-tight">{t("app.title")}</h1>
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
          <Tabs value={mode} onValueChange={setMode} className="w-full">
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="unit">{t("tab.unit")}</TabsTrigger>
              <TabsTrigger value="assembly">{t("tab.assembly")}</TabsTrigger>
              <TabsTrigger value="grid">{t("tab.grid")}</TabsTrigger>
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
