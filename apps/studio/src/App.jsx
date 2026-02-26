import { lazy, Suspense, useState, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe } from 'lucide-react'
import { Toaster } from "@/components/ui/sonner"
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet"
import { useProject } from './contexts/project/ProjectProvider'
import { useThemeAndLanguage } from './hooks/system/useThemeAndLanguage'
import { usePlatform } from './contexts/system/PlatformProvider'
import { useIsMobile } from './hooks/system/useMediaQuery'
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
const ScadEditor = lazy(() => import('./components/editor/ScadEditor'))
const GitPanel = lazy(() => import('./components/editor/GitPanel'))
const AiChatPanel = lazy(() => import('./components/ai/AiChatPanel'))
const ForkDialog = lazy(() => import('./components/project/ForkDialog'))
const StorefrontView = lazy(() => import('./components/storefront/StorefrontView'))


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
  const handleSynthesisComplete = useCallback((newSlug) => {
    navigate(`/project/${newSlug}`)
  }, [navigate])

  const isMobile = useIsMobile()

  // Get state from ProjectContext
  const {
    currentView, isDemo, manifest, projectSlug,
    handleGenerate, handleConfirmRender, handleCancelRender,
    showConfirmDialog, pendingEstimate,
    params, setParams,
  } = useProject()

  // Initialize theme/lang/auth side effects
  const { t, language, toggleLanguage, theme, cycleTheme } = useThemeAndLanguage({
    currentView,
    projectName: manifest?.project?.name,
  })

  const { platformName, platformLogo, loading: platformLoading } = usePlatform()

  const [forkDialogSlug, setForkDialogSlug] = useState(null)
  const handleForkRequest = useCallback(() => setForkDialogSlug(projectSlug), [projectSlug])
  const handleForked = useCallback((newSlug) => {
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
                <img src={platformLogo} alt="Logo" className="h-6 w-auto" onError={(e) => e.target.style.display = 'none'} />
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
      <div className={`flex flex-1 overflow-hidden flex-col lg:flex-row ${editorOpen && !isMobile ? 'editor-layout' : ''}`}>
        {/* Desktop: editor side panel */}
        {editorOpen && !isMobile && (
          <div className="w-full lg:w-[40%] flex flex-col min-h-0 border-r border-border">
            <ErrorBoundary t={t}>
              <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground text-sm">Loading editor...</div>}>
                <ScadEditor slug={projectSlug} handleGenerate={handleGenerate} manifest={manifest} />
                <GitPanel slug={projectSlug} />
              </Suspense>
            </ErrorBoundary>
          </div>
        )}

        {/* Mobile: editor as bottom sheet */}
        {editorSheet && (
          <Sheet open={editorSheet} onOpenChange={(open) => { if (!open) toggleEditor() }}>
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

        {/* φ split: Sidebar ≈ 38.2% | Main ≈ 61.8% */}
        {!editorOpen && (
          <div className="flex flex-col min-h-0 border-r border-border overflow-y-auto" style={{ flex: 1, minWidth: '280px' }}>
            <StudioSidebar />
          </div>
        )}

        <ErrorBoundary t={t}>
          <div style={{ flex: 1.618, minWidth: 0 }} className="flex flex-col min-h-0">
            <StudioMainView />
          </div>
        </ErrorBoundary>
      </div>

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
            projectName={manifest?.project?.name || forkDialogSlug}
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
