import { useState, useEffect, useRef } from 'react'
import axios from 'axios'
import Controls from './components/Controls'
import Viewer from './components/Viewer'
import { Button } from "@/components/ui/button"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useTheme } from "./contexts/ThemeProvider"
import { useLanguage } from "./contexts/LanguageProvider"
import { Sun, Moon, Monitor, Globe, Download, Image } from 'lucide-react'
import './index.css'

function App() {
  const { theme, setTheme } = useTheme()
  const { language, setLanguage, t } = useLanguage()

  const [mode, setMode] = useState('unit') // 'unit' or 'grid'

  const [params, setParams] = useState({
    // Unit Params
    size: 20.0,
    thick: 2.5,
    rod_D: 6.0,
    show_base: true,
    show_walls: true,
    show_mech: true,
    // Grid Params
    rows: 4,
    cols: 4,
    rod_extension: 10
  })

  const [stlUrl, setStlUrl] = useState(null)
  const [logs, setLogs] = useState(t("log.ready"))
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)

  const viewerRef = useRef(null)

  const handleGenerate = async () => {
    setLoading(true)
    setProgress(10)
    setLogs(prev => prev + `\n${t("log.generating")} (${mode})...`)

    // Select SCAD file based on mode
    const payload = {
      ...params,
      scad_file: mode === 'unit' ? 'half_cube.scad' : 'tablaco.scad'
    }

    // Simulate progress
    const progressInterval = setInterval(() => {
      setProgress(p => Math.min(p + 15, 90))
    }, 300)

    try {
      const res = await axios.post('http://localhost:5000/api/render', payload)
      clearInterval(progressInterval)
      setProgress(100)
      setStlUrl(res.data.stl_url + "?t=" + Date.now()) // Cache bust
      setLogs(prev => prev + `\n${t("log.gen_stl")}`)
    } catch (e) {
      clearInterval(progressInterval)
      setLogs(prev => prev + `\n${t("log.error")}` + e.message)
    } finally {
      setTimeout(() => {
        setLoading(false)
        setProgress(0)
      }, 500) // Brief pause to show 100%
    }
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
    if (!stlUrl) return
    const link = document.createElement('a')
    link.href = stlUrl
    link.download = `tablaco_${mode}.stl`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const handleExportImage = (view) => {
    if (!viewerRef.current) return
    viewerRef.current.setCameraView(view)
    // Small delay to let camera update
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

  // Debounced auto-generate
  useEffect(() => {
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
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="unit">{t("tab.unit")}</TabsTrigger>
              <TabsTrigger value="grid">{t("tab.grid")}</TabsTrigger>
            </TabsList>
          </Tabs>

          <Controls params={params} setParams={setParams} mode={mode} />

          <div className="flex-1"></div>

          {/* Action Buttons */}
          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button onClick={handleGenerate} disabled={loading} className="w-full">
              {loading ? t("btn.proc") : t("btn.gen")}
            </Button>

            <Button variant="secondary" onClick={handleVerify} disabled={loading} className="w-full">
              {t("btn.verify")}
            </Button>
          </div>

          {/* Export Buttons */}
          <div className="flex flex-col gap-2 border-t border-border pt-4">
            <Button variant="outline" onClick={handleDownloadStl} disabled={!stlUrl} className="w-full gap-2">
              <Download className="h-4 w-4" />
              {t("act.download_stl")}
            </Button>

            <div className="text-xs text-muted-foreground mb-1">{t("act.export_img")}</div>
            <div className="grid grid-cols-2 gap-2">
              <Button variant="outline" size="sm" onClick={() => handleExportImage('iso')} disabled={!stlUrl}>
                {t("view.iso")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('top')} disabled={!stlUrl}>
                {t("view.top")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('front')} disabled={!stlUrl}>
                {t("view.front")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => handleExportImage('right')} disabled={!stlUrl}>
                {t("view.right")}
              </Button>
            </div>
          </div>
        </div>

        {/* Main View */}
        <div className="flex-1 relative flex flex-col">
          <div className="flex-1 bg-black relative">
            <Viewer ref={viewerRef} stlUrl={stlUrl} loading={loading} progress={progress} />
          </div>

          {/* Console */}
          <div className="h-48 bg-zinc-950 border-t border-border p-4 font-mono text-xs text-green-400 overflow-y-auto whitespace-pre-wrap">
            {logs}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

