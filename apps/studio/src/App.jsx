import { lazy, Suspense, useState, useCallback } from 'react'
import { Button } from "@/components/ui/button"
import { Sun, Moon, Monitor, Globe } from 'lucide-react'
import { Toaster } from "@/components/ui/sonner"
import { useProject } from './contexts/ProjectProvider'
import { useThemeAndLanguage } from './hooks/useThemeAndLanguage'
import StudioHeader from './components/studio/StudioHeader'
import StudioSidebar from './components/studio/StudioSidebar'
import StudioMainView from './components/studio/StudioMainView'
import ConfirmRenderDialog from './components/feedback/ConfirmRenderDialog'
import AuthButton from './components/auth/AuthButton'
import DemoBanner from './components/feedback/DemoBanner'
import RateLimitBanner from './components/feedback/RateLimitBanner'
import { ErrorBoundary } from './components/feedback/ErrorBoundary'
import './index.css'

const ProjectsView = lazy(() => import('./components/project/ProjectsView'))
const ScadEditor = lazy(() => import('./components/editor/ScadEditor'))
const GitPanel = lazy(() => import('./components/editor/GitPanel'))
const AiChatPanel = lazy(() => import('./components/ai/AiChatPanel'))
const ForkDialog = lazy(() => import('./components/project/ForkDialog'))

const isEmbed = new URLSearchParams(window.location.search).get('embed') === 'true'

function App() {
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

  const [forkDialogSlug, setForkDialogSlug] = useState(null)
  const handleForkRequest = useCallback(() => setForkDialogSlug(projectSlug), [projectSlug])
  const handleForked = useCallback((newSlug) => {
    setForkDialogSlug(null)
    window.location.hash = `#/${newSlug}`
    setEditorOpen(true)
    sessionStorage.setItem('yantra4d-editor-open', 'true')
  }, [])

  if (!isEmbed && currentView === 'projects') {
    const ThemeIcon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor
    return (
      <div className="flex flex-col h-screen w-full bg-background text-foreground">
        <header className="h-12 border-b border-border bg-card flex items-center justify-between px-4 shrink-0">
          <h1 className="text-lg font-bold tracking-tight">Yantra4D</h1>
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

  return (
    <div className="flex flex-col h-screen w-full bg-background text-foreground">
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
        />
      )}

      {!isEmbed && <RateLimitBanner />}
      <div className={`flex flex-1 overflow-hidden flex-col lg:flex-row ${editorOpen ? 'editor-layout' : ''}`}>
        {editorOpen && (
          <div className="w-full lg:w-[40%] flex flex-col min-h-0 border-r border-border">
            <ErrorBoundary t={t}>
              <Suspense fallback={<div className="flex items-center justify-center h-full text-muted-foreground text-sm">Loading editor...</div>}>
                <ScadEditor slug={projectSlug} handleGenerate={handleGenerate} manifest={manifest} />
                <GitPanel slug={projectSlug} />
              </Suspense>
            </ErrorBoundary>
          </div>
        )}
        {!editorOpen && <StudioSidebar />}

        <ErrorBoundary t={t}>
          <StudioMainView />
        </ErrorBoundary>
      </div>

      {/* AI Configurator overlay */}
      {aiPanelOpen && !editorOpen && (
        <div className="fixed right-0 top-12 bottom-0 w-80 z-40 border-l border-border shadow-lg">
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
      <Toaster richColors position="bottom-right" />
    </div>
  )
}

export default App
