import { lazy, Suspense, useState, useCallback, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe, PanelLeft } from 'lucide-react'
import { Toaster } from "@/components/ui/sonner"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { ResizablePanelGroup, ResizablePanel, ResizableHandle } from "@/components/ui/resizable"
import { useProject } from './contexts/project/ProjectProvider'
import { useManifest } from './contexts/project/ManifestProvider'
import { useThemeAndLanguage } from './hooks/system/useThemeAndLanguage'
import { usePlatform } from './contexts/system/PlatformProvider'
import { useIsMobile } from './hooks/system/useMediaQuery'
import { usePanelLayout } from './hooks/system/usePanelLayout'
import StudioHeader from './components/studio/StudioHeader'
import StudioSidebar from './components/studio/StudioSidebar'
import StudioMainView from './components/studio/StudioMainView'
import ConfirmRenderDialog from './components/feedback/ConfirmRenderDialog'
import AuthButton from './components/auth/AuthButton'
import DemoBanner from './components/feedback/DemoBanner'
import RateLimitBanner from './components/feedback/RateLimitBanner'
import SynthesisModal from './components/studio/SynthesisModal'
import { ErrorBoundary } from './components/feedback/ErrorBoundary'
import './index.css'

const ProjectsView = lazy(() => import('./components/project/ProjectsView'))
const OnboardingWizard = lazy(() => import('./components/onboarding/OnboardingWizard'))
const ScadEditor = lazy(() => import('./components/editor/ScadEditor'))
const GitPanel = lazy(() => import('./components/editor/GitPanel'))
const AiChatPanel = lazy(() => import('./components/ai/AiChatPanel'))
const ForkDialog = lazy(() => import('./components/project/ForkDialog'))
const StorefrontView = lazy(() => import('./components/storefront/StorefrontView'))

interface ComparisonSlot {
  id: string
  label: string
  parts: unknown[]
  params: Record<string, unknown>
}

function App() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()

  const isEmbed = searchParams.get('embed') === 'true'
  const isStorefront = searchParams.get('mode') === 'storefront'
  const [editorOpen, setEditorOpen] = useState(() => sessionStorage.getItem('yantra4d-editor-open') === 'true')
  const toggleEditor = () => setEditorOpen(prev => {
    const next = !prev
    sessionStorage.setItem('yantra4d-editor-open', String(next))
    return next
  })

  const [aiPanelOpen, setAiPanelOpen] = useState(() => sessionStorage.getItem('yantra4d-ai-panel') === 'true')
  const toggleAiPanel = () => setAiPanelOpen(prev => {
    const next = !prev
    sessionStorage.setItem('yantra4d-ai-panel', String(next))
    return next
  })

  const [synthesisModalOpen, setSynthesisModalOpen] = useState(false)
  const handleSynthesisComplete = useCallback((newSlug: string) => {
    navigate(`/project/${newSlug}`)
  }, [navigate])

  const isMobile = useIsMobile()
  const { layout, setSidebarSize, toggleSidebar, setConsoleSize, toggleConsole } = usePanelLayout()
  const { manifestError: _manifestError } = useManifest() as { manifestError: string | null }

  // Get state from ProjectContext
  const {
    currentView, isDemo, manifest, projectSlug,
    handleGenerate, handleConfirmRender, handleCancelRender,
    showConfirmDialog, pendingEstimate,
    params, setParams,
    parts,
  } = useProject()

  // Comparison mode state
  const [compareMode, setCompareMode] = useState(false)
  const [comparisonSlots, setComparisonSlots] = useState<ComparisonSlot[]>([])

  const handleAddComparisonSlot = useCallback(() => {
    if (comparisonSlots.length >= 4) return
    setComparisonSlots(prev => [...prev, {
      id: crypto.randomUUID(),
      label: `Variation ${prev.length + 1}`,
      parts: [...parts],
      params: { ...params },
    }])
  }, [parts, params, comparisonSlots.length])

  const handleRemoveComparisonSlot = useCallback((slotId: string) => {
    setComparisonSlots(prev => prev.filter(s => s.id !== slotId))
  }, [])

  // Panel toggle keyboard shortcuts ([ and ])
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement).tagName
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(tag) || (e.target as HTMLElement).isContentEditable) return
      if (e.metaKey || e.ctrlKey) return
      if (e.key === '[') toggleSidebar()
      else if (e.key === ']') toggleConsole()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [toggleSidebar, toggleConsole])

  // Initialize theme/lang/auth side effects
  const { t, language, toggleLanguage, theme, cycleTheme } = useThemeAndLanguage({
    currentView,
    projectName: manifest?.project?.name as string,
  })

  const { platformName, platformLogo, loading: platformLoading } = usePlatform()

  const [forkDialogSlug, setForkDialogSlug] = useState<string | null>(null)
  const handleForkRequest = useCallback(() => setForkDialogSlug(projectSlug), [projectSlug])
  const handleForked = useCallback((newSlug: string) => {
    setForkDialogSlug(null)
    navigate(`/project/${newSlug}`)
    setEditorOpen(true)
    sessionStorage.setItem('yantra4d-editor-open', 'true')
  }, [navigate])

  if (isStorefront) {
    return (
      <ErrorBoundary t={t}>
        <Suspense fallback={<div className="flex items-center justify-center h-dvh text-muted-foreground">Loading storefront...</div>}>
          <StorefrontView
            onExitStorefront={() => {
              searchParams.delete('mode')
              setSearchParams(searchParams)
            }}
          />
        </Suspense>
      </ErrorBoundary>
    )
  }

  if (!isEmbed && currentView === 'projects') {
    const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor
    return (
      <div className="flex flex-col h-dvh w-full bg-background text-foreground">
        <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-2">
            {!platformLoading && (
              <>
                <img src={platformLogo} alt="Logo" className="h-6 w-auto" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none' }} />
                <h1 className="text-lg font-bold tracking-tight">{platformName}</h1>
              </>
            )}
          </div>
          <div className="flex items-center gap-2">
            <AuthButton />
            <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={toggleLanguage} title={language === 'es' ? t('lang.switch_to_en') : t('lang.switch_to_es')}>
              <Globe className="h-5 w-5" />
            </Button>
            <Button variant="ghost" size="icon" className="min-h-[44px] min-w-[44px]" onClick={cycleTheme} title={t(`theme.${theme}`)}>
              <ThemeIcon className="h-5 w-5" />
            </Button>
          </div>
        </header>
        {isDemo && <DemoBanner />}
        <RateLimitBanner />
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

  if (currentView === 'onboard') {
    return (
      <ErrorBoundary t={t}>
        <Suspense fallback={<div className="flex items-center justify-center h-dvh text-muted-foreground">Loading...</div>}>
          <OnboardingWizard />
        </Suspense>
      </ErrorBoundary>
    )
  }

  // Project not found or manifest error — show friendly error page
  if (_manifestError) {
    return (
      <div className="flex flex-col items-center justify-center h-dvh bg-background text-foreground gap-4 px-4 text-center">
        <div className="text-6xl">🔍</div>
        <h1 className="text-2xl font-bold">{t('error.project_not_found_title')}</h1>
        <p className="text-muted-foreground max-w-md">
          {t('error.project_not_found_body', { slug: projectSlug })}
        </p>
        <Button onClick={() => navigate('/projects')} variant="default" className="min-h-[44px]">
          {t('error.browse_projects')}
        </Button>
      </div>
    )
  }

  // Whether editor should be shown as bottom sheet on mobile
  const editorSheet = editorOpen && isMobile

  return (
    <div className="flex flex-col h-dvh w-full bg-background text-foreground">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:absolute focus:z-[100] focus:top-2 focus:left-2 focus:px-4 focus:py-2 focus:bg-primary focus:text-primary-foreground focus:rounded-md focus:text-sm focus:font-medium">
        {t('a11y.skip_to_content')}
      </a>
      {!isEmbed && (
        <StudioHeader
          editorOpen={editorOpen}
          toggleEditor={toggleEditor}
          aiPanelOpen={aiPanelOpen}
          toggleAiPanel={toggleAiPanel}
          onForkRequest={handleForkRequest}
          setSynthesisModalOpen={setSynthesisModalOpen}
        />
      )}

      {!isEmbed && <RateLimitBanner />}

      {/*
        Single #main-content spanning both layout trees.

        The id used to live on StudioMainView, which is rendered once here for
        desktop and once below for mobile — so it was in the DOM twice. That is
        invalid HTML, and it broke the skip link above: href="#main-content"
        resolves to the first match, the desktop tree, which is display:none
        under lg. Skipping to content on a phone landed on a hidden element.

        Exactly one child is ever displayed (hidden lg:flex vs lg:hidden), so
        one wrapper is unambiguous at every width and needs no JS breakpoint.
        tabIndex={-1} lets the skip link move focus here without adding a tab
        stop of its own.
      */}
      <div id="main-content" tabIndex={-1} className="flex flex-1 overflow-hidden min-h-0 outline-none">

      {/* Desktop: resizable horizontal layout */}
      <div className="hidden lg:flex flex-1 overflow-hidden relative">
        <ResizablePanelGroup
          orientation="horizontal"
          onLayoutChanged={(panelLayout: Record<string, number>) => {
            if (!editorOpen && !layout.sidebarCollapsed && panelLayout["sidebar"] != null) {
              setSidebarSize(panelLayout["sidebar"])
            }
          }}
        >
          {/* Sidebar panel (conditional) */}
          {!editorOpen && !layout.sidebarCollapsed && (
            <>
              <ResizablePanel id="sidebar" defaultSize={layout.sidebarSize} minSize={15} maxSize={40}>
                <StudioSidebar
                  variant="desktop"
                  compareMode={compareMode}
                  onToggleCompare={() => setCompareMode(prev => !prev)}
                  onCollapse={toggleSidebar}
                />
              </ResizablePanel>
              <ResizableHandle withHandle orientation="horizontal" />
            </>
          )}

          {/* Editor panel (conditional, replaces sidebar) */}
          {editorOpen && (
            <>
              <ResizablePanel id="editor" defaultSize={40} minSize={25} maxSize={60}>
                <div className="flex flex-col h-full min-h-0 border-r border-border">
                  <ErrorBoundary t={t}>
                    <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground text-sm">Loading editor...</div>}>
                      <ScadEditor slug={projectSlug} handleGenerate={handleGenerate} manifest={manifest} />
                      <GitPanel slug={projectSlug} />
                    </Suspense>
                  </ErrorBoundary>
                </div>
              </ResizablePanel>
              <ResizableHandle withHandle orientation="horizontal" />
            </>
          )}

          {/* Main view panel */}
          <ResizablePanel id="main" defaultSize={editorOpen ? 60 : (layout.sidebarCollapsed ? 100 : (100 - layout.sidebarSize))} minSize={40}>
            <ErrorBoundary t={t}>
              <StudioMainView
                compareMode={compareMode}
                comparisonSlots={comparisonSlots}
                onAddComparisonSlot={handleAddComparisonSlot}
                onRemoveComparisonSlot={handleRemoveComparisonSlot}
                consoleSize={layout.consoleSize}
                consoleCollapsed={layout.consoleCollapsed}
                onConsoleResize={setConsoleSize}
                onToggleConsole={toggleConsole}
              />
            </ErrorBoundary>
          </ResizablePanel>
        </ResizablePanelGroup>

        {/* Sidebar collapsed: floating expand button */}
        {layout.sidebarCollapsed && !editorOpen && (
          <button
            onClick={toggleSidebar}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-20 p-2 bg-card border border-border border-l-0 rounded-r-md shadow-sm hover:bg-muted transition-colors text-muted-foreground hover:text-foreground"
            title="Show sidebar"
            aria-label="Show sidebar"
            aria-expanded={false}
          >
            <PanelLeft className="h-4 w-4" />
          </button>
        )}
      </div>

      {/* Mobile: original layout */}
      <div className="flex flex-1 overflow-hidden flex-col lg:hidden">
        {/* Mobile: editor as bottom sheet */}
        {editorSheet && (
          <Sheet open={editorSheet} onOpenChange={(open: boolean) => { if (!open) toggleEditor() }}>
            <SheetContent side="bottom" className="max-h-[60vh] overflow-y-auto p-0 flex flex-col pb-safe">
              <SheetTitle className="sr-only">Code Editor</SheetTitle>
              <ErrorBoundary t={t}>
                <Suspense fallback={<div className="flex items-center justify-center h-32 text-muted-foreground text-sm">Loading editor...</div>}>
                  <ScadEditor slug={projectSlug} handleGenerate={handleGenerate} manifest={manifest} />
                  <GitPanel slug={projectSlug} />
                </Suspense>
              </ErrorBoundary>
            </SheetContent>
          </Sheet>
        )}

        {/* Sidebar: mobile bar */}
        {!editorOpen && (
          <StudioSidebar
            variant="mobile"
            compareMode={compareMode}
            onToggleCompare={() => setCompareMode(prev => !prev)}
          />
        )}

        <ErrorBoundary t={t}>
          <div style={{ flex: 1.618, minWidth: 0 }} className="flex flex-col min-h-0">
            <StudioMainView
              compareMode={compareMode}
              comparisonSlots={comparisonSlots}
              onAddComparisonSlot={handleAddComparisonSlot}
              onRemoveComparisonSlot={handleRemoveComparisonSlot}
            />
          </div>
        </ErrorBoundary>
      </div>

      </div>{/* /#main-content */}

      {/* AI Configurator overlay */}
      {aiPanelOpen && !editorOpen && (
        <>
          {/* Mobile dismiss backdrop */}
          {isMobile && (
            <div
              className="fixed inset-0 z-30 bg-black/20"
              onClick={toggleAiPanel}
              aria-hidden="true"
            />
          )}
          <div className="fixed right-0 top-12 landscape:top-10 bottom-0 w-full sm:w-80 z-40 border-l border-border shadow-lg bg-background max-h-[calc(100dvh-3rem)] landscape:max-h-[calc(100dvh-2.5rem)] pb-safe pr-safe">
            <ErrorBoundary t={t}>
              <Suspense fallback={<div className="flex items-center justify-center h-full text-sm text-muted-foreground">Loading AI...</div>}>
                <AiChatPanel
                  mode="configurator"
                  projectSlug={projectSlug}
                  manifest={manifest}
                  params={params}
                  setParams={setParams}
                />
              </Suspense>
            </ErrorBoundary>
          </div>
        </>
      )}

      {/* Fork dialog */}
      {forkDialogSlug && (
        <Suspense fallback={null}>
          <ForkDialog
            slug={forkDialogSlug}
            projectName={(manifest?.project?.name as string) || forkDialogSlug}
            onClose={() => setForkDialogSlug(null)}
            onForked={handleForked}
          />
        </Suspense>
      )}

      <ConfirmRenderDialog
        open={showConfirmDialog}
        onConfirm={handleConfirmRender}
        onCancel={handleCancelRender}
        estimatedTime={pendingEstimate}
      />

      <SynthesisModal
        open={synthesisModalOpen}
        onOpenChange={setSynthesisModalOpen}
        onSynthesisComplete={handleSynthesisComplete}
      />

      <Toaster richColors position={isMobile ? "top-center" : "bottom-right"} />
    </div>
  )
}

export default App
