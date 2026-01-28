import { useState, useEffect, useRef, useCallback } from 'react'
import axios from 'axios'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import ConfirmRenderDialog from './components/ConfirmRenderDialog'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { Sun, Moon, Monitor, Globe, Download } from 'lucide-react'
import './index.css'

function App() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()

  const [mode, setMode] = useState('unit') // 'unit', 'assembly', or 'grid'

  const [params, setParams] = useState({
    // Unit Params
    size: 20.0,
    thick: 2.5,
    rod_D: 3.0,
    show_base: true,
    show_walls: true,
    show_mech: true,
    // Grid Params
    rows: 8,
    cols: 8,
    rod_extension: 10
  })

  // Colors state
  const [colors, setColors] = useState({
    bottom: '#ffffff',
    top: '#000000',
    rods: '#808080',
    stoppers: '#ffd700',
    // Fallback/Default
    main: '#e5e7eb'
  })

  // Replaced stlUrl with parts list
  const [parts, setParts] = useState([])
  const [logs, setLogs] = useState(t("log.ready"))
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  // Confirmation dialog state
  const [showConfirmDialog, setShowConfirmDialog] = useState(false)
  const [pendingEstimate, setPendingEstimate] = useState(0)
  const [pendingPayload, setPendingPayload] = useState(null)

  // Geometry cache: { cacheKey: parts[] }
  const [partsCache, setPartsCache] = useState({})

  const viewerRef = useRef(null)

  // Generate cache key from mode and params
  const getCacheKey = useCallback((m, p) => {
    return JSON.stringify({ mode: m, size: p.size, thick: p.thick, rod_D: p.rod_D, rows: p.rows, cols: p.cols })
  }, [])

  const handleGenerate = async (forceRender = false, overridePayload = null) => {
    // Select SCAD file based on mode
    let scad_file = 'half_cube.scad'
    if (mode === 'grid') scad_file = 'tablaco.scad'
    else if (mode === 'assembly') scad_file = 'assembly.scad'

    const payload = overridePayload || { ...params, scad_file }
    const cacheKey = getCacheKey(mode, params)

    // Check cache first (unless forced)
    if (!forceRender && partsCache[cacheKey]) {
      setParts(partsCache[cacheKey])
      setLogs(prev => prev + `\n[Cache hit] Loaded from cache.`)
      return
    }

    // Step 1: Get estimate (unless we're forcing after confirmation)
    if (!forceRender) {
      try {
        const estRes = await axios.post('http://localhost:5000/api/estimate', payload)
        const estimate = estRes.data.estimated_seconds

        // If estimate > 60s, show confirmation dialog
        if (estimate > 60) {
          setPendingEstimate(estimate)
          setPendingPayload(payload)
          setShowConfirmDialog(true)
          return
        }
      } catch (e) {
        // If estimate fails, proceed anyway
        console.warn('Estimate failed, proceeding:', e)
      }
    }

    // Step 2: Actually render with streaming progress
    setLoading(true)
    setProgress(5)
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    try {
      // Use fetch with streaming to read SSE
      const response = await fetch('http://localhost:5000/api/render-stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let finalParts = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        // SSE format: "data: {...}\n\n"
        const lines = chunk.split('\n').filter(line => line.startsWith('data: '))

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6)) // Remove "data: " prefix

            // Update progress from any event that has it
            if (data.progress !== undefined) {
              setProgress(data.progress)
            }

            if (data.event === 'part_start') {
              setLogs(prev => prev + `\n[${data.part}] Starting... (${data.index + 1}/${data.total})`)
            } else if (data.event === 'output') {
              // Log phase transitions and significant lines
              const line = data.line
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
            // Ignore malformed JSON lines
          }
        }
      }

      // Add timestamp to cache bust and update state
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
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    } finally {
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, 500)
    }
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

  const handleVerify = async () => {
    setLoading(true)
    setLogs(prev => prev + `\n${t("log.verify")}`)
    try {
      const res = await axios.post('http://localhost:5000/api/verify')
      setLogs(prev => prev + "\n\n--- VERIFICATION REPORT ---\n" + res.data.output)
      if (res.data.passed) setLogs(prev => prev + `\n${t("log.pass")}`)
      else setLogs(prev => prev + `\n${t("log.fail")}`)
    } catch (e) {
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    } finally {
      setLoading(false)
    }
  }

  const handleDownloadStl = () => {
    // Basic implementation: download the first part found
    // A more robust solution would zip them or download all
    if (parts.length === 0) return
    const link = document.createElement('a')
    link.href = parts[0].url
    link.download = `tablaco_${mode}_${parts[0].type}.stl`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
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

  // Debounced auto-generate with cache check
  useEffect(() => {
    const cacheKey = getCacheKey(mode, params)
    // Check cache immediately on tab switch
    if (partsCache[cacheKey]) {
      setParts(partsCache[cacheKey])
      return
    }
    const timer = setTimeout(() => {
      handleGenerate()
    }, 500)
    return () => clearTimeout(timer)
  }, [params, mode])

  const cycleTheme = () => {
    const themes = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    setTheme(themes[(currentIndex + 1) % themes.length])
  }

  const toggleLanguage = () => {
    setLanguage(language === 'es' ? 'en' : 'es')
  }

  const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor

  console.log("App Render. Colors:", colors)

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
              <TabsTrigger value="assembly">Assembly</TabsTrigger>
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
            <Button type="button" onClick={handleGenerate} disabled={loading} className="w-full">
              {loading ? t("btn.proc") : t("btn.gen")}
            </Button>

            <Button variant="secondary" onClick={handleVerify} disabled={loading} className="w-full">
              {t("btn.verify")}
            </Button>
          </div>

          {/* Export Buttons */}
          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button variant="outline" onClick={handleDownloadStl} disabled={parts.length === 0} className="w-full gap-2">
              <Download className="h-4 w-4" />
              {t("act.download_stl")} (First Part)
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
          </div>
        </div>

        {/* Main View */}
        <div className="flex-1 relative flex flex-col">
          <div className="flex-1 bg-black relative">
            <Viewer ref={viewerRef} parts={parts} colors={colors} loading={loading} progress={progress} />
          </div>

          {/* Console */}
          <div className="h-48 bg-zinc-950 border-t border-border p-4 font-mono text-xs text-green-400 overflow-y-auto whitespace-pre-wrap">
            {logs}
          </div>
        </div>
      </div>

      {/* Confirmation Dialog for Long Renders */}
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

